# 运行时配置获取分析

> 来源：黑曼巴6.16逆向分析（IP非硬编码，运行时从服务器获取）
> 适用：网络验证、动态配置、服务器地址运行时获取的场景

## 一、问题分析

### 1.1 黑曼巴的配置获取方式

```
传统程序：IP地址硬编码在二进制中
  → 搜索字符串即可找到
  → 修改字符串即可Patch

黑曼巴：IP地址运行时从服务器获取
  → 字符串搜索找不到IP
  → 需要分析配置获取协议
  → 需要拦截配置获取过程
```

**具体行为：**
1. 程序启动时连接配置服务器
2. 获取服务器列表（IP+端口）
3. 使用获取的IP进行后续通信
4. 配置可能包含：服务器地址、验证方式、功能开关

### 1.2 带来的挑战

| 挑战 | 说明 | 影响 |
|------|------|------|
| 无法静态Patch | IP不在二进制中 | 字符串搜索无效 |
| 需要动态分析 | 必须运行时拦截 | 增加复杂度 |
| 协议分析 | 需要理解配置协议 | 可能需要逆向协议 |
| 多层验证 | 配置可能包含验证逻辑 | 绕过更困难 |

## 二、分析策略

### 2.1 策略1：拦截配置获取请求

**目标：** 在程序获取配置时，拦截并修改响应

**步骤：**
```python
# 1. 分析配置获取请求
# 使用抓包工具（Wireshark/mitmproxy）
# 观察程序启动时的网络请求

# 2. 确定配置服务器地址
# 可能通过DNS查询、硬编码域名、或之前获取的配置

# 3. 设置拦截
# 使用Hosts劫持或DNS劫持
# 将配置服务器指向本地

# 4. 伪造配置响应
# 返回修改后的配置（包含本地IP）
```

**工具：**
```bash
# mitmproxy拦截
mitmproxy --mode reverse:http://config-server.com

# 修改响应脚本
# mitm_script.py
def response(flow):
    if "config" in flow.request.url:
        # 修改响应中的IP地址
        flow.response.text = flow.response.text.replace(
            "original_ip", "127.0.0.1"
        )
```

### 2.2 策略2：Hook配置解析函数

**目标：** 在程序解析配置时，修改解析结果

**步骤：**
```javascript
// 1. 定位配置解析函数
// 搜索字符串："server", "ip", "port", "config"
// 找到解析配置的函数

// 2. Hook配置解析函数
Interceptor.attach(config_parse_function, {
    onLeave: function(retval) {
        // 修改解析后的配置结构
        var config = this.config_ptr;
        
        // 修改服务器地址
        config.server_ip = "127.0.0.1";
        config.server_port = 8080;
        
        console.log("[+] 配置已修改指向本地");
    }
});
```

### 2.3 策略3：Hook网络请求函数

**目标：** 在程序发送请求时，修改目标地址

**步骤：**
```javascript
// 1. Hook connect函数
Interceptor.attach(Module.findExportByName(null, "connect"), {
    onEnter: function(args) {
        var sockaddr = ptr(args[1]);
        var port = sockaddr.add(2).readU16().swap16();
        var ip = sockaddr.add(4).readByteArray(4);
        
        var ip_str = Array.from(ip).join(".");
        console.log("[*] 连接目标: " + ip_str + ":" + port);
        
        // 修改为目标IP
        if (ip_str === "original_ip") {
            var new_ip = [127, 0, 0, 1];
            sockaddr.add(4).writeByteArray(new_ip);
            console.log("[+] 已重定向到 127.0.0.1");
        }
    }
});
```

### 2.4 策略4：本地DNS劫持

**目标：** 通过DNS劫持，将配置服务器域名指向本地

**步骤：**
```bash
# 1. 确定配置服务器域名
# 抓包分析或字符串搜索

# 2. 修改Hosts文件（Windows）
# C:\Windows\System32\drivers\etc\hosts
127.0.0.1 config-server.com
127.0.0.1 api.target.com

# 3. 刷新DNS缓存
ipconfig /flushdns

# 4. 启动本地假服务器
# 返回修改后的配置
```

### 2.5 策略5：内存搜索运行时配置

**目标：** 在程序运行后，从内存中搜索配置结构

**步骤：**
```python
# 1. 使用Cheat Engine或类似工具
# 2. 在程序获取配置后，搜索已知配置值
# 3. 找到配置结构在内存中的位置
# 4. 修改内存中的配置值

# 示例：搜索IP地址字符串
# 在Cheat Engine中搜索字符串 "115.159.3.176"
# 找到后修改内存值为 "127.0.0.1"
```

## 三、黑曼巴特定方案

### 3.1 配置获取流程分析

```
黑曼巴启动流程：
1. 程序启动
2. 连接配置服务器（域名/IP）
3. 发送设备信息（获取配置）
4. 接收配置（JSON/Protobuf/自定义格式）
5. 解析配置，提取服务器地址
6. 连接游戏服务器

关键点：步骤2-4是配置获取阶段
```

### 3.2 拦截方案

```python
# 方案A：拦截配置请求
# 使用pydivert（Windows）或iptables（Linux）

import pydivert

# 拦截所有出站请求
with pydivert.WinDivert("outbound") as w:
    for packet in w:
        if packet.dst_port == 80 or packet.dst_port == 443:
            # 检查是否是配置请求
            # 如果是，修改目标IP为本地
            packet.dst_addr = "127.0.0.1"
        
        w.send(packet)

# 本地启动假服务器
# 返回修改后的配置
```

### 3.3 假服务器实现

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/config', methods=['POST'])
def fake_config():
    """返回修改后的配置"""
    return jsonify({
        "servers": [
            {"ip": "127.0.0.1", "port": 8080, "type": "auth"},
            {"ip": "127.0.0.1", "port": 8081, "type": "game"}
        ],
        "features": {
            "vip": True,
            "all_functions": True
        },
        "verify": {
            "enabled": False,  # 禁用验证
            "server": "127.0.0.1"
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
```

## 四、通用分析流程

### 4.1 分析步骤

```
1. 静态分析
   ├─ 搜索配置相关字符串（"config", "server", "ip", "port"）
   ├─ 搜索网络请求函数（connect, HttpOpenRequest, curl）
   └─ 识别配置解析函数

2. 动态分析
   ├─ 抓包观察启动时的网络请求
   ├─ 确定配置服务器地址和协议
   └─ 分析配置响应格式

3. 选择策略
   ├─ 如果配置服务器是域名 → DNS劫持
   ├─ 如果配置通过HTTP获取 → mitmproxy拦截
   ├─ 如果配置解析函数可定位 → Hook解析函数
   └─ 如果以上都失败 → 内存搜索运行时配置

4. 执行绕过
   ├─ 设置拦截（Hosts/DNS/Hook）
   ├─ 启动假服务器
   └─ 验证配置是否被修改
```

### 4.2 工具链

| 工具 | 用途 | 场景 |
|------|------|------|
| Wireshark | 抓包分析 | 观察网络请求 |
| mitmproxy | HTTP拦截 | 修改HTTP响应 |
| Fiddler | HTTP调试 | Windows平台 |
| pydivert | 包过滤 | Windows底层拦截 |
| iptables | 包过滤 | Linux底层拦截 |
| Frida | 函数Hook | 修改配置解析 |
| Cheat Engine | 内存编辑 | 运行时修改 |

## 五、多层防护突破

### 5.1 黑曼巴的多层防护

```
黑曼巴防护层次：
1. 第一层：Frida检测
   → 检测到Frida后禁用网络
   → 绕过：Gadget模式/非Frida工具

2. 第二层：IP白名单
   → 服务器验证客户端IP
   → 绕过：配置获取拦截/本地服务器

3. 第三层：TLS加密
   → 使用rustls进行TLS 1.3加密
   → 绕过：证书固定绕过/内存提取密钥

4. 第四层：协议验证
   → 自定义协议，验证请求合法性
   → 绕过：协议分析/请求伪造
```

### 5.2 突破顺序

```
推荐突破顺序：
1. 先绕过Frida检测（否则无法动态分析）
2. 再拦截配置获取（获取服务器地址）
3. 然后绕过TLS加密（解密通信）
4. 最后伪造协议请求（通过验证）

注意：每层突破都需要前一层成功
```

## 六、经验总结

### 6.1 关键教训

```
1. 不要假设IP是硬编码的
   → 现代程序普遍使用动态配置
   → 必须分析配置获取机制

2. 配置获取是突破口
   → 控制配置 = 控制程序行为
   → 拦截配置比Patch程序更容易

3. 假服务器是最有效的方案
   → 完全控制程序接收的配置
   → 可以禁用验证、启用功能

4. 多层防护需要分层突破
   → 不要试图一次性突破所有防护
   → 逐层分析，逐层突破
```

### 6.2 工具推荐

```
Windows平台：
- 首选：Fiddler + pydivert
- 备选：Wireshark + mitmproxy
- 最后：Cheat Engine + x64dbg

Linux平台：
- 首选：iptables + mitmproxy
- 备选：nftables + Wireshark
- 最后：GDB + Frida

macOS平台：
- 首选：mitmproxy + Frida
- 备选：Wireshark + LLDB
- 最后：Cheat Engine
```

### 6.3 自动化工具

```python
class ConfigInterceptor:
    """自动拦截和修改配置获取"""
    
    def __init__(self, target_config_server):
        self.target_server = target_config_server
        self.fake_server = None
    
    def start(self):
        """启动拦截"""
        # 1. 设置DNS劫持
        self.hijack_dns()
        
        # 2. 启动假服务器
        self.start_fake_server()
        
        # 3. 等待程序连接
        print("[*] 等待程序获取配置...")
    
    def hijack_dns(self):
        """劫持DNS解析"""
        # 修改Hosts文件或启动本地DNS服务器
        pass
    
    def start_fake_server(self):
        """启动假服务器"""
        # 根据目标协议启动对应服务
        # HTTP/HTTPS/TCP/UDP
        pass
    
    def modify_config(self, original_config):
        """修改配置内容"""
        # 根据需求修改配置
        # 禁用验证、启用功能、修改服务器地址
        modified = original_config.copy()
        modified['verify']['enabled'] = False
        modified['features']['vip'] = True
        return modified
```

---

> 结论：运行时配置获取是现代程序的标准做法，逆向分析时必须将配置获取作为关键突破口。控制配置获取 = 控制程序行为。
