# rustls TLS深入分析：BlackMamba案例

> 基于：逆向分析报告 + rustls-0.23.40源码分析
> 目标：理解为什么无法绕过TLS加密

## 一、rustls架构分析

### 1.1 rustls核心组件

```
rustls-0.23.40
├── client/
│   ├── ClientConfig      # 客户端配置
│   ├── ClientConnection  # 客户端连接
│   └── tls13/           # TLS 1.3实现
├── server/
│   └── ServerConfig      # 服务端配置
├── crypto/
│   └── ring/            # 加密后端（ring库）
└── verify/              # 证书验证
    └── ServerCertVerifier
```

### 1.2 BlackMamba中的TLS配置

**从二进制中提取的配置特征：**

```rust
// 典型的rustls ClientConfig配置
let config = ClientConfig::builder()
    .with_safe_defaults()
    .with_root_certificates(root_store)  // 系统CA
    .with_no_client_auth();               // 无客户端证书

// WebSocket连接
let ws_stream = connect_async_tls_with_config(
    "wss://115.190.254.27:16000",
    Some(config),
    ...
).await?;
```

**关键发现：**
- 使用系统CA证书（无证书固定）
- 无客户端认证
- TLS 1.3（从rustls版本推断）

## 二、为什么无法解密TLS流量

### 2.1 TLS 1.3握手流程

```
客户端                           服务端
  |                                |
  |--- ClientHello --------------->|
  |    + key_share                 |
  |                                |
  |<--- ServerHello ---------------|
  |    + encrypted_extensions      |
  |<--- {Certificate} --------------|
  |<--- {CertificateVerify} -------|
  |<--- {Finished} ----------------|
  |                                |
  |--- {Finished} ---------------->|
  |    [Application Data]          |
  |<--- [Application Data] --------|
```

**关键：{ } 表示加密数据，[ ] 表示受保护数据**

### 2.2 密钥派生

```
PSK (Pre-Shared Key) = 0 (无0-RTT)

ES (Early Secret) = HKDF-Extract(0, 0)
HS (Handshake Secret) = HKDF-Extract(DHE, ES)
MS (Master Secret) = HKDF-Extract(0, HS)

应用数据密钥 = HKDF-Expand-Label(MS, "key", "", 16)
应用数据IV   = HKDF-Expand-Label(MS, "iv", "", 12)
```

**BlackMamba无法解密的原因：**

| 原因 | 说明 | 影响 |
|------|------|------|
| **DHE密钥临时** | 每次握手生成新的临时密钥 | 无法预测 |
| **前向保密** | 即使长期私钥泄露，历史会话安全 | 无法回溯解密 |
| **密钥仅内存** | 会话密钥只存在于内存中 | 无法提取 |
| **ring库保护** | Rust内存安全，难以Hook | 难以拦截 |

### 2.3 尝试过的解密方法（全部失败）

```python
# 方法1：Hook密钥派生函数
# 失败原因：ring库使用底层汇编优化，函数符号混淆

# 方法2：内存扫描密钥
# 失败原因：密钥使用后立即清零，且Rust内存布局复杂

# 方法3：Hook加密/解密函数
# 失败原因：WebSocket帧加密，无法定位明文边界

# 方法4：中间人攻击
# 失败原因：证书验证通过，但无法伪造服务端响应
```

## 三、证书验证分析

### 3.1 证书链验证

```rust
// rustls默认验证流程
impl ServerCertVerifier for WebPkiVerifier {
    fn verify_server_cert(
        &self,
        end_entity: &Certificate,
        intermediates: &[Certificate],
        server_name: &ServerName,
        ocsp_response: &[u8],
        now: UnixTime,
    ) -> Result<ServerCertVerified, Error> {
        // 1. 构建证书链
        // 2. 验证签名
        // 3. 检查有效期
        // 4. 验证域名匹配
        // 5. 检查撤销状态
        Ok(ServerCertVerified::assertion())
    }
}
```

**BlackMababy验证结果：**
- 证书验证通过（使用系统CA）
- 无证书固定（未发现硬编码指纹）
- 域名验证：验证服务器证书域名

### 3.2 为什么证书验证不是弱点

```
即使绕过证书验证：
  1. TLS握手仍然需要服务端私钥
  2. 无法伪造服务端Finished消息
  3. 客户端会检测到握手失败
  
结论：证书验证不是突破点
```

## 四、WebSocket协议分析

### 4.1 WebSocket over TLS

```
TLS记录层
├── 类型: Application Data (23)
├── 版本: TLS 1.3
└── 加密数据
    └── WebSocket帧
        ├── FIN: 1
        ├── RSV: 000
        ├── OPCODE: 1 (text) / 2 (binary)
        ├── MASK: 1 (客户端) / 0 (服务端)
        ├── PAYLOAD LENGTH: 7位 / 16位 / 64位
        ├── MASKING KEY: 4字节（如果MASK=1）
        └── PAYLOAD DATA: 加密数据
```

### 4.2 抓包分析

```python
# 成功捕获的384字节数据
# 结构分析：

# TLS记录头 (5字节)
# 17 03 03 01 7F  -> Application Data, TLS 1.2, 长度 383

# 加密数据 (383字节)
# 无法解密，因为缺少会话密钥

# 即使解密TLS记录：
# 内部是WebSocket帧，可能还有应用层加密
```

## 五、突破点分析

### 5.1 理论上可能的突破点

| 层级 | 突破点 | 难度 | 可行性 |
|------|--------|------|--------|
| **TLS层** | 提取会话密钥 | ⭐⭐⭐⭐⭐ | 几乎不可能 |
| **WebSocket层** | 伪造握手响应 | ⭐⭐⭐⭐ | 需要解密 |
| **应用层** | 分析认证协议 | ⭐⭐⭐ | 需要大量样本 |
| **客户端层** | Patch验证逻辑 | ⭐⭐ | 可能可行 |

### 5.2 最可行的方向：客户端Patch

```
思路：不是解密通信，而是让客户端认为验证通过

方法：
1. 找到认证状态检查点
2. Patch检查逻辑，强制返回"已认证"
3. 绕过所有服务端验证

难点：
- Rust编译的代码难以定位逻辑点
- 反调试机制阻止动态分析
- 多线程并发增加Patch复杂度
```

### 5.3 黑曼巴尝试过的客户端Patch（全部失败）

```
方案17: 等长Patch地址
- 结果：程序正常启动
- 问题：主验证IP非硬编码，运行时获取
- 教训：现代程序使用配置/动态获取，非硬编码

方案18: DLL Patch
- 结果：DLL从未加载
- 问题：验证逻辑在主程序
- 教训：不要假设DLL是核心

方案21-26: 各种Patch尝试
- 结果：全部失败
- 原因：Rust代码结构复杂，难以定位关键点
```

## 六、rustls特定逆向技巧

### 6.1 识别rustls配置

```bash
# 检查是否使用自定义ServerCertVerifier
strings target.exe | grep -i "ServerCertVerifier\|verify_server_cert"

# 检查是否禁用验证（测试模式）
strings target.exe | grep -i "dangerous\|insecure\|skip_verify"

# 检查证书存储
strings target.exe | grep -i "root_store\|ca_cert\|trust_anchor"
```

### 6.2 定位TLS握手函数

```python
# Frida脚本：定位TLS握手
TLS_HANDSHAKE_SCRIPT = """
// Hook rustls ClientConnection::new
Interceptor.attach(Module.findExportByName(null, "_ZN4rustls6client16ClientConnection3new..."), {
    onEnter: function(args) {
        console.log("[+] ClientConnection::new 被调用");
        
        // 分析配置参数
        var config = args[0];
        console.log("[+] 配置地址: " + config);
        
        // 可以尝试修改配置
        // 例如：禁用证书验证
    }
});

// Hook TLS握手完成
Interceptor.attach(Module.findExportByName(null, "_ZN4rustls...complete_io..."), {
    onLeave: function(retval) {
        console.log("[+] TLS握手完成");
        
        // 握手完成后，可以分析连接状态
    }
});
"""
```

### 6.3 提取TLS配置信息

```python
# 从内存中提取TLS配置
def extract_tls_config(process_name):
    """
    提取rustls ClientConfig配置
    """
    import frida
    
    session = frida.attach(process_name)
    script = session.create_script("""
        // 扫描内存查找ClientConfig特征
        var pattern = "rustls_client_ClientConfig"; // 简化示例
        
        Memory.scan(Process.mainModule.base, Process.mainModule.size, pattern, {
            onMatch: function(addr, size) {
                console.log("[+] 发现ClientConfig相关数据 at: " + addr);
                
                // 读取配置结构
                var config_data = Memory.readByteArray(addr, 256);
                console.log(hexdump(config_data));
                
                return 'stop';
            },
            onComplete: function() {
                console.log("[+] 扫描完成");
            }
        });
    """)
    script.load()
    return session
```

## 七、总结与建议

### 7.1 为什么BlackMamba无法破解

```
1. 强加密：TLS 1.3 + 前向保密
2. 密钥保护：仅服务端持有，客户端无密钥
3. 反调试：检测到Frida后禁用网络
4. 验证分散：多层级验证，单点突破无效
5. 动态配置：关键参数运行时获取，非硬编码
6. Rust安全：内存安全，难以Hook和Patch
```

### 7.2 对其他Rust程序的启示

```
分析Rust程序TLS时：
1. 首先确认TLS库版本和配置
2. 检查是否有证书固定
3. 确认密钥存储位置
4. 评估反调试机制强度
5. 考虑客户端Patch而非解密

如果目标使用rustls+ring：
- 解密几乎不可能
- 重点放在客户端逻辑Patch
- 寻找认证状态检查点
- 考虑社会工程学攻击
```

### 7.3 工具建议

```python
# 针对rustls的专用工具链

# 1. 静态分析
# - IDA Pro + Rust插件
# - Ghidra + Rust脚本
# - 自定义rustls符号恢复

# 2. 动态分析
# - Frida（需要反调试绕过）
# - WinDbg（内核调试）
# - 自定义内核驱动

# 3. 网络分析
# - 内核级抓包（pktmon/netsh）
# - 透明代理（pydivert）
# - 路由器抓包

# 4. 辅助工具
# - Process Hacker（内存分析）
# - API Monitor（API调用跟踪）
# - DebugView（调试输出）
```

---

> 结论：对于使用rustls+TLS 1.3+前向保密的现代Rust程序，
> 网络层解密几乎不可能。重点应放在客户端逻辑分析
> 和Patch，而非尝试破解加密。
