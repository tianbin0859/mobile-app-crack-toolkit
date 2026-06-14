# 本地授权服务器部署指南

## 场景

为破解后的软件（如528游戏辅助）搭建替代授权服务器，实现：
- 卡密生成与管理
- 设备绑定（一机一码）
- 远程激活（公网访问）
- 心跳检测
- Web管理面板

## 部署方式

### 方式一：本地直接运行（推荐）

```bash
# 启动服务器（监听0.0.0.0:8080）
python w528_auth_server.py

# 后台运行
nohup python w528_auth_server.py > server.log 2>&1 &
```

**特点：**
- 绑定本地所有接口（0.0.0.0）
- 支持局域网内其他设备访问
- 适合测试和开发

### 方式二：内网穿透（公网访问）

#### ngrok（免费/临时）

```bash
# 安装
brew install ngrok

# 配置Token（免费注册获取）
ngrok config add-authtoken YOUR_TOKEN

# 启动隧道（后台）
ngrok http 8080 --region=ap > ngrok.log 2>&1 &

# 查看公网地址
curl -s http://localhost:4040/api/tunnels | grep -o 'https://[^"]*'
```

**缺点：** 免费版域名随机，每次重启变化

#### 花生壳（国内/稳定）

```bash
# 官网下载客户端（需注册账号）
# https://hsk.oray.com/download

# 安装后配置映射
# 内网IP: 127.0.0.1:8080
# 外网域名: yourname.vip
```

**注意：** 官网下载链接可能失效，备用方案：
1. 通过brew安装：`brew install --cask phddns`（可能不可用）
2. Docker运行：`docker run -d oray/phddns`
3. 直接回退到ngrok

#### frp（自建/免费）

```bash
# 需要一台公网服务器
# 服务端（公网VPS）
frps -c frps.ini

# 客户端（本地）
frpc -c frpc.ini
```

### 方式三：后台常驻服务

```bash
# 使用launchd（macOS）
cat > ~/Library/LaunchAgents/com.auth.server.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.auth.server</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/path/to/w528_auth_server.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

launchctl load ~/Library/LaunchAgents/com.auth.server.plist
```

## Web管理面板

### 访问方式

```
本地: http://127.0.0.1:8080/panel
公网: https://your-ngrok-url.ngrok-free.dev/panel
```

### 功能

- 卡密生成（批量/单条）
- 卡密列表（启用/禁用/删除）
- 设备绑定查看
- 使用统计
- 心跳状态

### 暗色主题

```css
/* 黑底+荧光绿高亮 */
body { background: #0a0a0a; color: #e0e0e0; }
.card { background: #1a1a1a; border: 1px solid #333; }
.btn-primary { background: #00ff88; color: #000; }
.status-active { color: #00ff88; }
.status-expired { color: #ff4444; }
```

## 卡密格式

```
前缀-随机段-随机段-随机段

CL-XXXXX-XXXXX-XXXXX  (基础功能)
ZL-XXXXX-XXXXX-XXXXX  (专业功能)
GL-XXXXX-XXXXX-XXXXX  (VIP功能)
```

## 验证流程

```
客户端启动
    ↓
请求 /api/verify (卡密+设备ID)
    ↓
服务器验证：
  - 卡密是否存在
  - 是否已过期
  - 设备是否绑定
  - 设备数是否超限
    ↓
返回验证结果 + 功能级别
    ↓
客户端根据功能级别启用对应功能
```

## 心跳检测

```
客户端每5分钟发送心跳
    ↓
请求 /api/heartbeat (卡密+设备ID)
    ↓
服务器更新最后活跃时间
    ↓
超过10分钟无心跳 = 离线状态
```

## 与破解软件联动

### 修改hosts（最简单）

```
# 将原始验证服务器指向本地
115.159.3.176  127.0.0.1
111.170.163.77 127.0.0.1
```

### Frida Hook（更灵活）

```javascript
// Hook网络请求，重定向到本地服务器
Interceptor.attach(Module.findExportByName(null, "connect"), {
    onEnter: function(args) {
        var addr = Memory.readUtf8String(args[1]);
        if (addr.indexOf("115.159.3.176") !== -1) {
            // 替换为本地地址
            Memory.writeUtf8String(args[1], "127.0.0.1:8080");
        }
    }
});
```

### 代理工具（mitmproxy）

```python
# 拦截验证请求并转发到本地
def request(flow):
    if "115.159.3.176:8080" in flow.request.url:
        flow.request.host = "127.0.0.1"
        flow.request.port = 8080
```

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 卡密不存在 | 服务器重启后数据库丢失 | 使用持久化存储（JSON文件/SQLite） |
| 公网地址变化 | ngrok免费版域名随机 | 使用付费版或花生壳/frp |
| 端口被占用 | 其他程序占用8080 | 更换端口或kill占用进程 |
| 防火墙拦截 | 系统防火墙 | 添加例外规则或关闭防火墙 |
| 中文乱码 | 终端编码问题 | 使用PowerShell而非cmd |

## 安全建议

1. **本地部署**：授权服务器仅监听127.0.0.1，不暴露公网
2. **内网穿透**：使用ngrok/花生壳时，注意Token安全
3. **HTTPS**：生产环境使用HTTPS（Let's Encrypt免费证书）
4. **访问控制**：管理面板添加密码保护
5. **日志清理**：定期清理验证日志，避免敏感信息泄露

## 用户交互信号

- `不用7` = 跳过步骤7（如跳过LAN共享，仅本地部署）
- `你来处理` = 直接执行最佳方案，不询问确认
- `同意` = 立即继续执行，不需要详细解释
- `继续` = 继续上一步操作，不重复确认
