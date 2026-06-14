# 阿里云远程授权控制服务器部署指南

## 概述

为破解后的软件搭建阿里云ECS远程授权控制服务器，实现全球访问、卡密管理、设备绑定、远程激活、心跳检测。

## 阿里云ECS配置

### 推荐配置

| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| 实例类型 | ECS 共享型 n4 | 性价比最高 |
| CPU | 1核 | 足够处理验证请求 |
| 内存 | 2GB | 运行Python服务 |
| 带宽 | 1Mbps | 足够验证流量 |
| 系统盘 | 40GB SSD | 存储日志和数据库 |
| 操作系统 | CentOS 7.9 / Ubuntu 20.04 | 稳定兼容 |
| 费用 | 约￥100/年 | 新用户优惠 |

### 购买步骤

1. 访问阿里云官网：https://www.aliyun.com
2. 注册/登录账号
3. 进入ECS控制台
4. 点击"创建实例"
5. 选择"共享型 n4"实例
6. 选择操作系统（CentOS 7.9）
7. 选择带宽（1Mbps）
8. 确认订单并支付

## 安全组配置

### 必须开放的端口

| 端口 | 协议 | 授权对象 | 用途 |
|------|------|----------|------|
| 22 | TCP | 你的本地IP | SSH远程登录 |
| 8080 | TCP | 0.0.0.0/0 | 授权服务API |
| 80 | TCP | 0.0.0.0/0 | Web管理面板（可选） |

### 配置步骤

1. 进入ECS控制台
2. 选择你的实例
3. 点击"安全组"
4. 点击"配置规则"
5. 添加安全组规则：
   - 方向：入方向
   - 授权策略：允许
   - 协议类型：自定义TCP
   - 端口范围：8080/8080
   - 授权对象：0.0.0.0/0
   - 描述：授权服务API

## 部署方式对比

| 方式 | 适用场景 | 稳定性 | 域名 | 费用 |
|------|----------|--------|------|------|
| 阿里云ECS | 国内稳定长期 | 高 | 固定IP | ￥100/年 |
| ngrok | 临时测试 | 低（域名变化） | 随机域名 | 免费 |
| 花生壳DDNS | 国内动态IP | 中 | 固定域名 | ￥98/年 |
| frp自建 | 长期稳定 | 高 | 自定义域名 | 需服务器 |

## 快速部署

### 1. 准备服务器文件

```bash
# 本地准备以下文件
w528_auth_server.py      # 授权服务器主程序
w528_auth_client.py      # 客户端验证工具
w528_panel.html          # Web管理面板
deploy_aliyun.sh         # 部署脚本
```

### 2. 上传文件到服务器

```bash
# 使用scp上传
scp w528_auth_server.py w528_auth_client.py w528_panel.html deploy_aliyun.sh root@你的阿里云IP:/root/

# 或使用sftp
sftp root@你的阿里云IP
put w528_auth_server.py
put w528_auth_client.py
put w528_panel.html
put deploy_aliyun.sh
```

### 3. 执行部署脚本

```bash
# SSH登录服务器
ssh root@你的阿里云IP

# 执行部署脚本
chmod +x deploy_aliyun.sh
./deploy_aliyun.sh
```

### 4. 验证部署

```bash
# 测试API接口
curl http://你的阿里云IP:8080/api/status

# 测试卡密生成
curl -X POST http://你的阿里云IP:8080/api/admin/generate \
  -H "Content-Type: application/json" \
  -d '{"prefix": "ZL", "days": 30}'

# 测试验证
curl -X POST http://你的阿里云IP:8080/api/verify \
  -H "Content-Type: application/json" \
  -d '{"license_key": "生成的卡密", "device_id": "test_device"}'
```

## 部署脚本详解

### deploy_aliyun.sh

```bash
#!/bin/bash
# 528授权服务器 - 阿里云ECS部署脚本

set -e

echo "[*] 528授权服务器部署脚本"
echo "[*] 适用于阿里云ECS CentOS/Ubuntu"

# 1. 安装依赖
echo "[1/7] 安装系统依赖..."
if command -v yum &> /dev/null; then
    yum install -y python3 python3-pip
elif command -v apt-get &> /dev/null; then
    apt-get update
    apt-get install -y python3 python3-pip
else
    echo "[!] 不支持的包管理器"
    exit 1
fi

# 2. 创建目录
echo "[2/7] 创建服务目录..."
mkdir -p /opt/w528-auth
mkdir -p /var/log/w528-auth

# 3. 复制文件
echo "[3/7] 复制授权服务器文件..."
cp w528_auth_server.py /opt/w528-auth/
cp w528_auth_client.py /opt/w528-auth/
cp w528_panel.html /opt/w528-auth/

# 4. 安装Python依赖
echo "[4/7] 安装Python依赖..."
pip3 install flask cryptography

# 5. 创建系统服务
echo "[5/7] 创建系统服务..."
cat > /etc/systemd/system/w528-auth.service << 'EOF'
[Unit]
Description=528 Authorization Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/w528-auth
ExecStart=/usr/bin/python3 /opt/w528-auth/w528_auth_server.py server --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5
StandardOutput=append:/var/log/w528-auth/server.log
StandardError=append:/var/log/w528-auth/error.log

[Install]
WantedBy=multi-user.target
EOF

# 6. 启动服务
echo "[6/7] 启动服务..."
systemctl daemon-reload
systemctl enable w528-auth
systemctl start w528-auth

# 7. 验证
echo "[7/7] 验证部署..."
sleep 2
if curl -s http://localhost:8080/api/status > /dev/null; then
    echo "[+] 部署成功！"
    echo "[*] 公网访问: http://你的阿里云IP:8080"
    echo "[*] 管理面板: http://你的阿里云IP:8080/panel"
else
    echo "[!] 部署可能失败，请检查日志"
    journalctl -u w528-auth -n 20
fi
```

## 管理命令

### 服务管理

```bash
# 查看服务状态
systemctl status w528-auth

# 查看运行日志
journalctl -u w528-auth -f

# 查看错误日志
tail -f /var/log/w528-auth/error.log

# 重启服务
systemctl restart w528-auth

# 停止服务
systemctl stop w528-auth

# 禁用开机启动
systemctl disable w528-auth
```

### 卡密管理

```bash
# 进入服务目录
cd /opt/w528-auth

# 生成卡密
python3 w528_auth_server.py generate --prefix ZL --days 30

# 生成多个卡密
python3 w528_auth_server.py generate --prefix GL --days 30 --count 10

# 查看卡密列表
python3 w528_auth_server.py list

# 查看统计信息
python3 w528_auth_server.py stats
```

## Web管理面板

### 访问地址

```
公网访问: http://你的阿里云IP:8080/panel
```

### 功能说明

| 功能 | 说明 |
|------|------|
| 统计概览 | 总卡密数、活跃设备、今日验证次数 |
| 卡密生成 | 批量生成、前缀选择、有效期设置 |
| 卡密管理 | 启用/禁用/解绑/删除 |
| 设备管理 | 查看绑定设备、强制解绑 |
| 日志查看 | 验证记录、激活记录 |

### 暗色主题

- 黑底背景
- 荧光绿高亮
- 红色警告
- 蓝色信息

## 与破解软件联动

### 1. 修改hosts（Windows虚拟机）

```bash
# 编辑hosts文件
notepad C:\Windows\System32\drivers\etc\hosts

# 添加以下行（替换为你的阿里云IP）
你的阿里云IP  115.159.3.176
你的阿里云IP  111.170.163.77

# 刷新DNS缓存
ipconfig /flushdns
```

### 2. Frida Hook拦截

```javascript
// 替换验证服务器地址为阿里云IP
Interceptor.attach(Module.findExportByName(null, "connect"), {
    onEnter: function(args) {
        var sockaddr = ptr(args[1]);
        var port = sockaddr.add(2).readU16().swap16();
        var ip = sockaddr.add(4).readByteArray(4);
        
        // 替换为阿里云IP
        var aliyunIP = [你的阿里云IP段];
        sockaddr.add(4).writeByteArray(aliyunIP);
        
        console.log("[*] 重定向验证服务器到阿里云");
    }
});
```

### 3. 代理工具转发

```bash
# mitmproxy拦截并转发
mitmproxy --mode reverse:http://你的阿里云IP:8080

# 或配置系统代理
export HTTP_PROXY=http://你的阿里云IP:8080
export HTTPS_PROXY=http://你的阿里云IP:8080
```

## 卡密分级系统

### 功能分级

| 前缀 | 功能 | 价格 | 适用场景 |
|------|------|------|----------|
| CL | 基础功能 | 低 | 普通用户 |
| ZL | 高级功能 | 中 | 进阶用户 |
| GL | 全部功能 | 高 | 专业用户 |

### 设备绑定机制

- 一机一码：卡密首次激活绑定设备指纹
- 最大设备数：可配置（默认1-3台）
- 心跳检测：每30分钟验证一次
- 离线缓冲：24小时离线可用

## 故障排查

### 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 无法访问8080端口 | 安全组未开放 | 配置安全组规则 |
| 服务启动失败 | 依赖缺失 | 安装python3和pip |
| 卡密验证失败 | 卡密未启用 | 启用卡密或重新生成 |
| 设备绑定失败 | 已达最大设备数 | 解绑旧设备或增加限制 |
| 心跳检测失败 | 网络不稳定 | 检查网络连接 |

### 日志查看

```bash
# 查看服务日志
journalctl -u w528-auth -n 100

# 查看错误日志
tail -f /var/log/w528-auth/error.log

# 查看访问日志
tail -f /var/log/w528-auth/server.log
```

## 安全建议

1. **修改默认端口**：将8080改为非标准端口
2. **配置防火墙**：仅开放必要端口
3. **定期备份**：备份卡密数据库
4. **监控日志**：定期检查异常访问
5. **更新系统**：定期更新操作系统和依赖

## 升级维护

### 更新授权服务器

```bash
# 1. 停止服务
systemctl stop w528-auth

# 2. 备份数据
cp /opt/w528-auth/w528_licenses.json /opt/w528-auth/w528_licenses.json.bak

# 3. 上传新版本
scp w528_auth_server.py root@你的阿里云IP:/opt/w528-auth/

# 4. 启动服务
systemctl start w528-auth

# 5. 验证
curl http://你的阿里云IP:8080/api/status
```

## 费用估算

| 项目 | 费用 | 说明 |
|------|------|------|
| ECS实例 | ￥100/年 | 新用户优惠 |
| 带宽 | 包含 | 1Mbps已包含 |
| 域名（可选） | ￥55/年 | 购买域名并解析 |
| SSL证书（可选） | 免费 | 使用Let's Encrypt |
| 总计 | ￥100-155/年 | 基础配置 |

## 总结

阿里云ECS部署方案优势：
- 固定公网IP，稳定可靠
- 国内访问速度快
- 完全自主控制
- 成本低廉（￥100/年）
- 支持长期运行

适合场景：
- 长期运营的破解软件授权
- 需要稳定公网访问
- 国内用户为主
- 预算有限

---

*阿里云远程授权控制服务器部署指南 v1.0*
*适用于528游戏辅助工具等破解软件的授权管理*
