# 授权系统设计指南

## 系统架构

```
┌─────────────────┐      HTTP/HTTPS      ┌──────────────────┐
│   客户端 (ELF)   │ ◄──────────────────► │   授权服务器      │
│                 │                      │  (Python/Flask)  │
├─────────────────┤                      ├──────────────────┤
│ 设备指纹采集     │                      │ 卡密管理         │
│ 请求签名生成     │                      │ 设备绑定         │
│ Token本地存储   │                      │ 期限控制         │
│ 心跳定时发送     │                      │ 功能分级         │
└─────────────────┘                      └──────────────────┘
```

## 服务端API (Python/Flask)

### 核心接口

```python
from flask import Flask, request, jsonify
import hashlib, time, sqlite3, secrets

app = Flask(__name__)
DB = "licenses.db"
SECRET_KEY = "your-secret-key"

def sign(data: dict, secret: str) -> str:
    """生成请求签名"""
    s = '&'.join(f"{k}={v}" for k, v in sorted(data.items()))
    return hashlib.sha256(f"{s}&{secret}".encode()).hexdigest()[:32]

def verify_sign(data: dict, signature: str) -> bool:
    """验证请求签名"""
    return sign(data, SECRET_KEY) == signature

@app.route('/api/init', methods=['POST'])
def api_init():
    """获取服务器配置"""
    return jsonify({
        "status": "ok",
        "heartbeat_interval": 60,
        "server_time": int(time.time()),
        "version": "1.0"
    })

@app.route('/api/login', methods=['POST'])
def api_login():
    """卡密登录"""
    data = request.get_json()
    key = data.get('key')
    device_id = data.get('device_id')
    signature = data.get('signature')
    
    # 验证签名
    if not verify_sign({"key": key, "device_id": device_id}, signature):
        return jsonify({"status": "error", "message": "Invalid signature"})
    
    # 验证卡密
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM licenses WHERE key=?", (key,))
    row = c.fetchone()
    
    if not row:
        return jsonify({"status": "error", "message": "Invalid key"})
    
    _, _, expires, devices, features, used = row
    
    if time.time() > expires:
        return jsonify({"status": "error", "message": "Key expired"})
    
    if used and used != device_id:
        return jsonify({"status": "error", "message": "Key bound to another device"})
    
    # 绑定设备
    if not used:
        c.execute("UPDATE licenses SET used=? WHERE key=?", (device_id, key))
        conn.commit()
    
    # 生成Token
    token = secrets.token_hex(16)
    c.execute("INSERT INTO tokens VALUES (?, ?, ?)", (token, key, int(time.time())))
    conn.commit()
    conn.close()
    
    return jsonify({
        "status": "ok",
        "token": token,
        "expires": expires,
        "features": features
    })

@app.route('/api/heartbeat', methods=['POST'])
def api_heartbeat():
    """心跳验证"""
    data = request.get_json()
    token = data.get('token')
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM tokens WHERE token=?", (token,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return jsonify({"status": "error", "message": "Invalid token"})
    
    return jsonify({"status": "ok"})
```

### 数据库结构

```sql
CREATE TABLE licenses (
    key TEXT PRIMARY KEY,
    created INTEGER,
    expires INTEGER,
    max_devices INTEGER,
    features TEXT,
    used TEXT
);

CREATE TABLE tokens (
    token TEXT PRIMARY KEY,
    license_key TEXT,
    created INTEGER
);

CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_key TEXT,
    device_id TEXT,
    action TEXT,
    timestamp INTEGER,
    ip TEXT
);
```

## 客户端实现 (C++)

### 核心类

```cpp
class AuthManager {
public:
    static AuthManager& getInstance() {
        static AuthManager instance;
        return instance;
    }
    
    bool initialize(const std::string& licenseKey);
    bool validate();
    bool hasFeature(Feature feature);
    void startHeartbeat();
    
private:
    std::string serverUrl = "http://your-server.com:8080";
    std::string secretKey = "your-secret-key";
    std::string token;
    std::vector<std::string> features;
    bool authenticated = false;
    
    std::string generateDeviceId();
    std::string generateSignature(const std::map<std::string, std::string>& data);
    bool verifyResponse(const std::string& response, const std::string& signature);
};
```

### 登录流程

```cpp
bool AuthManager::initialize(const std::string& licenseKey) {
    // 1. 获取设备指纹
    std::string deviceId = generateDeviceId();
    
    // 2. 生成请求签名
    auto data = std::map<std::string, std::string>{
        {"key", licenseKey},
        {"device_id", deviceId}
    };
    std::string signature = generateSignature(data);
    
    // 3. 发送登录请求
    auto response = httpPost(serverUrl + "/api/login", {
        {"key", licenseKey},
        {"device_id", deviceId},
        {"signature", signature}
    });
    
    // 4. 解析响应
    auto json = parseJson(response);
    if (json["status"] == "ok") {
        token = json["token"];
        features = json["features"];
        authenticated = true;
        startHeartbeat();
        return true;
    }
    
    return false;
}
```

### 心跳机制

```cpp
void AuthManager::startHeartbeat() {
    std::thread([this]() {
        while (authenticated) {
            std::this_thread::sleep_for(std::chrono::seconds(60));
            
            auto response = httpPost(serverUrl + "/api/heartbeat", {
                {"token", token}
            });
            
            auto json = parseJson(response);
            if (json["status"] != "ok") {
                authenticated = false;
                // 触发授权失效回调
            }
        }
    }).detach();
}
```

## 安全机制

### 1. 请求签名
```
签名算法: SHA256(sorted_params + secret_key)
示例: key=ABC&device_id=123 → SHA256("device_id=123&key=ABC&secret")
```

### 2. 响应签名
```
服务端返回: {data..., "signature": "xxx"}
客户端验证签名防止中间人篡改
```

### 3. 设备绑定
```
首次登录: 记录device_id
后续登录: 验证device_id是否匹配
防止一码多用
```

### 4. Token机制
```
登录成功: 服务端生成随机Token
后续请求: 携带Token验证
Token过期: 需重新登录
```

### 5. 时间戳校验
```
请求包含timestamp
服务端校验: |server_time - timestamp| < 300秒
防止重放攻击
```

## 卡密生成

```python
def generate_license(days: int, features: list, count: int = 1) -> list:
    """生成卡密"""
    import secrets, base64, json
    
    keys = []
    for _ in range(count):
        # 生成随机数据
        data = {
            "id": secrets.token_hex(8),
            "created": int(time.time()),
            "expires": int(time.time()) + days * 86400,
            "features": features
        }
        
        # Base64编码
        payload = base64.urlsafe_b64encode(
            json.dumps(data).encode()
        ).decode().rstrip('=')
        
        # 添加前缀
        key = f"M7-{payload}"
        keys.append(key)
    
    return keys
```

## 部署指南

### 1. 安装依赖
```bash
pip install flask pyopenssl gunicorn
```

### 2. 启动服务
```bash
# 开发模式
python server.py

# 生产模式
gunicorn -w 4 -b 0.0.0.0:8080 server:app
```

### 3. Nginx反向代理
```nginx
server {
    listen 443 ssl;
    server_name auth.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 客户端集成示例

```cpp
#include "auth_manager.h"

int main() {
    // 初始化授权
    auto& auth = AuthManager::getInstance();
    
    if (!auth.initialize("M7-XXXXXXXX")) {
        printf("授权失败，程序退出\n");
        return 1;
    }
    
    // 检查功能权限
    if (auth.hasFeature(FEATURE_ESP)) {
        enable_esp();
    }
    
    if (auth.hasFeature(FEATURE_AIM)) {
        enable_aim();
    }
    
    // 主循环
    while (true) {
        if (!auth.validate()) {
            printf("授权已失效\n");
            break;
        }
        
        // 游戏逻辑...
    }
    
    return 0;
}
```
