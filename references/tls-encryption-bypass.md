# TLS加密与证书固定绕过指南

## TLS库识别

### 常见TLS库特征

| 库 | 特征字符串 | 检测方法 |
|----|-----------|----------|
| **rustls** | `rustls::`, `ClientConfig`, `ServerCertVerifier` | `strings \| grep rustls` |
| **OpenSSL** | `OPENSSL`, `SSL_CTX`, `X509_verify_cert` | `strings \| grep -i openssl` |
| **WinHTTP** | `WinHttpOpen`, `WinHttpSetOption` | `strings \| grep WinHttp` |
| **SChannel** | `AcquireCredentialsHandle`, `InitializeSecurityContext` | `strings \| grep -i schannel` |
| **mbedTLS** | `mbedtls_ssl`, `mbedtls_x509` | `strings \| grep mbedtls` |
| **BoringSSL** | `boringssl`, `SSL_do_handshake` | `strings \| grep boringssl` |

### 快速识别

```bash
# 检查所有TLS库
strings target.exe | grep -E "rustls|openssl|WinHttp|SChannel|mbedtls|boringssl" | sort | uniq -c | sort -rn

# 检查TLS版本
strings target.exe | grep -E "TLSv1\.[0-3]|SSLv[23]" | head -10

# 检查证书相关
strings target.exe | grep -E "CERTIFICATE|PUBLIC KEY|PRIVATE KEY|X509" | head -20
```

## 证书固定检测

### 检测方法

```bash
# 1. 搜索固定相关字符串
strings target.exe | grep -i "pin\|pinning\|fixed\|hardcoded" | head -20

# 2. 搜索证书指纹
strings target.exe | grep -E "sha256/[a-zA-Z0-9+/=]{40,}" | head -10

# 3. 搜索硬编码域名
strings target.exe | grep -E "[a-zA-Z0-9.-]+\.(com|cn|net|org)" | sort | uniq | head -20

# 4. 搜索证书数据
strings target.exe | grep -E "BEGIN CERTIFICATE\|BEGIN PUBLIC KEY" | head -10

# 5. 分析二进制中的证书数据
python3 -c "
with open('target.exe', 'rb') as f:
    data = f.read()

# 查找X.509证书魔数 (0x30 0x82)
certs = []
pos = 0
while True:
    pos = data.find(b'\x30\x82', pos)
    if pos == -1:
        break
    # 检查是否是证书
    if data[pos:pos+4] == b'\x30\x82':
        certs.append(pos)
    pos += 1

print(f'发现 {len(certs)} 个可能的X.509证书')
for i, pos in enumerate(certs[:5]):
    print(f'  证书 {i+1}: 偏移 0x{pos:06X}')
"
```

### 证书固定类型

| 类型 | 说明 | 绕过难度 |
|------|------|----------|
| 公钥固定 | 固定服务器公钥指纹 | ⭐⭐⭐⭐ |
| 证书固定 | 固定整个证书 | ⭐⭐⭐ |
| 域名固定 | 只验证域名 | ⭐⭐ |
| 自签证书 | 使用自带CA | ⭐⭐⭐ |
| 混合固定 | 多种方式组合 | ⭐⭐⭐⭐⭐ |

## 证书固定绕过策略

### 策略1: Hook证书验证函数

```python
import frida

# 通用证书验证Hook脚本
CERT_HOOK_SCRIPT = """
// 针对rustls的ServerCertVerifier
Interceptor.attach(Module.findExportByName(null, "_ZN4rustls6client12ClientConfig..."), {
    onEnter: function(args) {
        console.log("[+] 拦截ClientConfig创建");
    }
});

// 通用验证器替换
function bypass_cert_verifier() {
    // 找到验证器vtable
    var verifier_vtable = Module.findExportByName(null, "_ZN4rustls...ServerCertVerifier...");
    
    if (verifier_vtable) {
        console.log("[+] 发现证书验证器: " + verifier_vtable);
        
        // Hook verify方法
        Interceptor.attach(verifier_vtable, {
            onEnter: function(args) {
                console.log("[+] 证书验证被调用 - 强制通过");
            },
            onLeave: function(retval) {
                // 强制返回验证成功
                retval.replace(0x1); // true
                console.log("[+] 证书验证结果已修改为通过");
            }
        });
    }
}

bypass_cert_verifier();
"""

def hook_cert_verification(target_process):
    session = frida.attach(target_process)
    script = session.create_script(CERT_HOOK_SCRIPT)
    script.load()
    return session
```

### 策略2: 内存Patch证书数据

```python
# 替换内存中的证书数据
def patch_certificate_data(process_name, old_cert_data, new_cert_data):
    """
    在目标进程内存中替换证书数据
    """
    import frida
    
    session = frida.attach(process_name)
    script = session.create_script(f"""
        // 扫描内存查找证书数据
        var pattern = "{old_cert_data.hex()}";
        Memory.scan(Process.mainModule.base, Process.mainModule.size, pattern, {{
            onMatch: function(addr, size) {{
                console.log("[+] 发现证书数据 at: " + addr);
                
                // 替换为新证书
                var newData = hexToBytes("{new_cert_data.hex()}");
                Memory.writeByteArray(addr, newData);
                console.log("[+] 证书数据已替换");
                
                return 'stop';
            }},
            onComplete: function() {{
                console.log("[+] 扫描完成");
            }}
        }});
    """)
    script.load()
    return session
```

### 策略3: 中间人+自签证书

```bash
# 1. 生成自签CA证书
openssl req -x509 -newkey rsa:2048 -keyout ca-key.pem -out ca-cert.pem -days 365 -nodes -subj "/CN=FakeCA"

# 2. 配置mitmproxy使用自签证书
mitmproxy --cert ca-cert.pem

# 3. 将自签证书安装到系统信任库
# Windows: 导入到"受信任的根证书颁发机构"
# macOS: security add-trusted-cert ca-cert.pem

# 4. 配置目标程序使用代理（如果程序支持）
# 或Hook网络函数强制走代理
```

### 策略4: 修改TLS配置

```python
# Frida脚本：修改TLS配置禁用证书验证
TLS_CONFIG_SCRIPT = """
// Hook rustls ClientConfig创建
Interceptor.attach(Module.findExportByName(null, "_ZN4rustls6client12ClientConfig3new..."), {
    onEnter: function(args) {
        console.log("[+] ClientConfig::new 被调用");
        
        // 修改配置参数
        // 禁用证书验证
        var config = args[0];
        
        // 设置dangerous()选项（如果存在）
        // rustls有dangerous()方法用于测试，可禁用验证
        
        console.log("[+] 尝试禁用证书验证");
    }
});

// Hook证书验证结果
Interceptor.attach(Module.findExportByName(null, "_ZN4rustls...verify..."), {
    onLeave: function(retval) {
        console.log("[+] 证书验证结果: " + retval);
        
        // 强制返回成功
        retval.replace(0);
        console.log("[+] 已强制验证通过");
    }
});
"""
```

## 特定TLS库绕过

### rustls绕过

```rust
// rustls特征
// - 使用ring库进行加密
// - 纯Rust实现
// - 配置驱动

// 绕过方法1: 替换ServerCertVerifier
// rustls允许自定义ServerCertVerifier

// 绕过方法2: Hook ring库的验证函数
// ring::signature::verify

// 绕过方法3: 修改ClientConfig的alpn_protocols
// 某些情况下可绕过特定协议检查
```

### OpenSSL绕过

```python
# OpenSSL证书验证Hook
OPENSSL_HOOK = """
// Hook SSL_CTX_set_verify
Interceptor.attach(Module.findExportByName(null, "SSL_CTX_set_verify"), {
    onEnter: function(args) {
        // 修改验证模式为SSL_VERIFY_NONE
        args[1] = ptr(0x00); // SSL_VERIFY_NONE
        console.log("[+] SSL验证模式已禁用");
    }
});

// Hook X509_verify_cert
Interceptor.attach(Module.findExportByName(null, "X509_verify_cert"), {
    onLeave: function(retval) {
        // 强制返回验证成功
        retval.replace(0x1);
        console.log("[+] X509验证已强制通过");
    }
});
"""
```

### WinHTTP绕过

```python
# WinHTTP证书验证Hook
WINHTTP_HOOK = """
// Hook WinHttpSetOption
Interceptor.attach(Module.findExportByName(null, "WinHttpSetOption"), {
    onEnter: function(args) {
        var option = args[1].toInt32();
        
        // WINHTTP_OPTION_SECURITY_FLAGS = 31
        if (option === 31) {
            console.log("[+] 拦截安全标志设置");
            
            // 设置 SECURITY_FLAG_IGNORE_UNKNOWN_CA
            // 设置 SECURITY_FLAG_IGNORE_CERT_WRONG_USAGE
            // 设置 SECURITY_FLAG_IGNORE_CERT_CN_INVALID
            // 设置 SECURITY_FLAG_IGNORE_CERT_DATE_INVALID
            var new_flags = 0x00000100 | 0x00000200 | 0x00001000 | 0x00002000;
            args[2] = ptr(new_flags);
            console.log("[+] 已禁用证书验证");
        }
    }
});
"""
```

## IP白名单绕过

### 检测IP校验

```bash
# 搜索IP地址
strings target.exe | grep -E "\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b" | sort | uniq

# 搜索域名
strings target.exe | grep -E "[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" | sort | uniq | head -20

# 搜索connect调用
objdump -d target.exe | grep -E "call.*connect|call.*WSAConnect" | head -20
```

### 绕过策略

| 策略 | 方法 | 适用场景 |
|------|------|----------|
| Hosts劫持 | 修改hosts文件指向本地 | 域名验证 |
| DNS劫持 | 控制DNS响应 | 域名验证 |
| 代理转发 | 设置HTTP/HTTPS代理 | 支持代理的程序 |
| Frida Hook | Hook connect函数替换IP | 硬编码IP |
| 路由器劫持 | 在路由器层面转发 | 局域网环境 |

### Frida Hook connect

```python
CONNECT_HOOK_SCRIPT = """
// Hook Windows connect
Interceptor.attach(Module.findExportByName("ws2_32.dll", "connect"), {
    onEnter: function(args) {
        var sockaddr = ptr(args[1]);
        var family = Memory.readU16(sockaddr);
        
        if (family === 2) { // AF_INET
            var port = Memory.readU16(sockaddr.add(2));
            port = ((port & 0xFF) << 8) | ((port >> 8) & 0xFF); // 字节序转换
            
            var ip = Memory.readU8(sockaddr.add(4)) + "." +
                     Memory.readU8(sockaddr.add(5)) + "." +
                     Memory.readU8(sockaddr.add(6)) + "." +
                     Memory.readU8(sockaddr.add(7));
            
            console.log("[+] connect: " + ip + ":" + port);
            
            // 替换为本地IP
            if (ip === "115.159.3.176" || ip === "111.170.163.77") {
                console.log("[+] 拦截服务器连接，重定向到本地");
                Memory.writeU8(sockaddr.add(4), 127);
                Memory.writeU8(sockaddr.add(5), 0);
                Memory.writeU8(sockaddr.add(6), 0);
                Memory.writeU8(sockaddr.add(7), 1);
            }
        }
    }
});
"""
```

## 协议分析与伪造

### 自定义二进制协议分析

```python
# 协议分析框架
class ProtocolAnalyzer:
    def __init__(self):
        self.packets = []
        self.patterns = {}
    
    def capture_packet(self, data, direction):
        """捕获数据包"""
        self.packets.append({
            'data': data,
            'direction': direction,
            'timestamp': time.time()
        })
    
    def analyze_structure(self):
        """分析协议结构"""
        if not self.packets:
            return None
        
        # 分析包长度分布
        lengths = [len(p['data']) for p in self.packets]
        avg_len = sum(lengths) / len(lengths)
        
        # 分析头部模式
        headers = [p['data'][:16] for p in self.packets]
        
        return {
            'avg_length': avg_len,
            'length_range': (min(lengths), max(lengths)),
            'common_headers': self._find_common_patterns(headers)
        }
    
    def _find_common_patterns(self, headers):
        """查找共同模式"""
        if not headers:
            return []
        
        # 逐字节比较
        patterns = []
        for i in range(min(len(h) for h in headers)):
            bytes_at_pos = [h[i] for h in headers]
            if len(set(bytes_at_pos)) == 1:
                patterns.append((i, bytes_at_pos[0]))
        
        return patterns

# 使用示例
analyzer = ProtocolAnalyzer()
# 捕获数据包...
result = analyzer.analyze_structure()
print(f"平均包长: {result['avg_length']}")
print(f"固定头部字节: {result['common_headers']}")
```

### 响应伪造

```python
# 伪造服务器响应
class FakeServer:
    def __init__(self, listen_port=8080):
        self.port = listen_port
        self.handlers = {}
    
    def register_handler(self, pattern, response):
        """注册响应处理器"""
        self.handlers[pattern] = response
    
    def handle_request(self, data):
        """处理请求并返回伪造响应"""
        for pattern, response in self.handlers.items():
            if pattern in data:
                return response
        
        # 默认响应
        return b'\x01\x00\x00\x00'  # 简单的成功响应
    
    def start(self):
        """启动伪造服务器"""
        import socket
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('0.0.0.0', self.port))
        sock.listen(5)
        
        print(f"[*] 伪造服务器监听端口 {self.port}")
        
        while True:
            client, addr = sock.accept()
            data = client.recv(4096)
            
            print(f"[+] 收到请求: {data[:50].hex()}")
            
            response = self.handle_request(data)
            client.send(response)
            client.close()

# 使用示例
fake = FakeServer(8080)
fake.register_handler(b'\x01\x01', b'\x01\x00\x00\x00\x01')  # 成功响应
fake.register_handler(b'\x02\x01', b'\x01\x00\x00\x00\x01')  # 成功响应
fake.start()
```

## 综合实战：四层防线突破

### 场景
目标程序有完整四层防线：
1. IP白名单验证
2. TLS证书固定
3. 自定义协议加密
4. 功能心跳检测

### 突破方案

```python
# 综合突破脚本
class FourLayerBypass:
    def __init__(self, target_process):
        self.target = target_process
        self.session = None
    
    def bypass_layer1_ip(self):
        """突破IP白名单"""
        # 方法1: Hosts劫持
        # 方法2: Frida Hook connect
        # 方法3: 代理转发
        pass
    
    def bypass_layer2_tls(self):
        """突破TLS证书固定"""
        # 方法1: Hook证书验证
        # 方法2: 替换证书数据
        # 方法3: 中间人+自签
        pass
    
    def bypass_layer3_protocol(self):
        """突破协议加密"""
        # 方法1: 分析协议结构
        # 方法2: Hook加密/解密函数
        # 方法3: 内存Dump明文
        pass
    
    def bypass_layer4_app(self):
        """突破应用层验证"""
        # 方法1: Hook功能检查
        # 方法2: 伪造心跳响应
        # 方法3: Patch验证逻辑
        pass
    
    def full_bypass(self):
        """完整突破"""
        print("[*] 开始四层防线突破...")
        
        self.bypass_layer1_ip()
        print("[+] 第一层突破: IP白名单")
        
        self.bypass_layer2_tls()
        print("[+] 第二层突破: TLS证书固定")
        
        self.bypass_layer3_protocol()
        print("[+] 第三层突破: 协议加密")
        
        self.bypass_layer4_app()
        print("[+] 第四层突破: 应用验证")
        
        print("[+] 全部防线突破完成！")

# 使用
bypass = FourLayerBypass("target.exe")
bypass.full_bypass()
```

## 工具推荐

| 工具 | 用途 | 链接 |
|------|------|------|
| mitmproxy | HTTP/HTTPS中间人 | mitmproxy.org |
| Burp Suite | Web协议分析 | portswigger.net |
| Frida | 动态插桩 | frida.re |
| x64dbg | Windows调试 | x64dbg.com |
| Wireshark | 网络抓包 | wireshark.org |
| OpenSSL | 证书操作 | openssl.org |
| certutil | Windows证书管理 | 系统自带 |

## 参考

- `rust-program-analysis-guide.md` - Rust程序分析
- `references/network-bypass-guide.md` - 网络验证绕过
- `references/frida-request-signing-guide.md` - Frida请求签名
