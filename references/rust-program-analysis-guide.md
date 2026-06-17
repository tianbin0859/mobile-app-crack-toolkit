# Rust二进制程序逆向分析指南

## 识别Rust编译程序

### 特征识别

| 特征 | 说明 | 检测方法 |
|------|------|----------|
| 大体积 | 通常>50MB（静态链接运行时） | `ls -lh` |
| 无符号表 | 函数名被混淆为`_ZN...` | `nm` / `strings` |
| Rust运行时 | `std::`, `core::`, `alloc::`前缀 | `strings \| grep` |
| 特定字符串 | `rust_panic`, `RUST_BACKTRACE` | `strings \| grep -i rust` |
| 依赖库 | rustls, tokio, serde, clap | `strings \| grep` |

### 快速识别命令

```bash
# 检查文件类型
file target.exe
# 输出: PE32+ executable (GUI) x86-64, for MS Windows, 14 sections

# 检查Rust特征字符串
strings target.exe | grep -i "rust\|cargo\|tokio\|serde" | head -20

# 检查Rust符号
nm target.exe | grep "_ZN" | head -10
# 输出: 0000000140123456 T _ZN4rustls6client... (Rust混淆符号)

# 检查依赖库
strings target.exe | grep -E "rustls|tokio|serde|clap|hyper|reqwest" | sort | uniq -c | sort -rn
```

## Rust混淆符号还原

### 符号命名规则

Rust使用Itanium C++ ABI的符号混淆规则：
```
_ZN + 长度 + 模块名 + 长度 + 函数名 + 17h + 哈希值

示例:
_ZN4rustls6client12ClientConfig... → rustls::client::ClientConfig
_ZN3std4sync... → std::sync
```

### 还原工具

```bash
# 使用rustfilt还原符号
rustfilt < symbols.txt > demangled.txt

# 或使用Python脚本解析
python3 -c "
import subprocess
symbols = subprocess.check_output(['nm', 'target.exe']).decode()
for line in symbols.split('\n'):
    if '_ZN' in line:
        # 解析Rust符号
        parts = line.split()
        if len(parts) >= 3:
            addr = parts[0]
            sym_type = parts[1]
            symbol = parts[2]
            # 简单还原
            demangled = symbol.replace('_ZN', '').replace('17h', '::')
            print(f'{addr} {sym_type} {demangled}')
"
```

## rustls TLS分析

### rustls特征

| 特征 | 说明 |
|------|------|
| 库名 | `rustls.dll` 或静态链接 |
| 配置结构 | `ClientConfig`, `ServerConfig` |
| 握手函数 | `ClientHello`, `ServerHello` |
| 证书验证 | `RootCertStore`, `ServerCertVerifier` |
| ALPN | `alpn_protocols` |

### 定位TLS握手

```bash
# 搜索rustls相关字符串
strings target.exe | grep -E "ClientHello|ServerHello|Certificate|Finished" | head -20

# 搜索证书相关
strings target.exe | grep -E "rustls::.*cert\|X509\|pem\|crt" | head -20

# 搜索配置相关
strings target.exe | grep -E "ClientConfig|ServerConfig|RootCertStore" | head -20
```

### 内存分析TLS状态

```python
# Frida脚本：监控rustls握手
import frida

session = frida.attach("target.exe")
script = session.create_script("""
// Hook rustls握手函数
Interceptor.attach(Module.findExportByName(null, "rustls_client_session_new"), {
    onEnter: function(args) {
        console.log("[+] rustls ClientSession created");
        // 读取配置
        this.config = args[0];
    },
    onLeave: function(retval) {
        console.log("[+] ClientSession returned: " + retval);
    }
});

// 监控证书验证
Interceptor.attach(Module.findExportByName(null, "rustls_server_cert_verifier_new"), {
    onEnter: function(args) {
        console.log("[+] ServerCertVerifier created - 证书验证点");
    }
});
""")
script.load()
```

## 证书固定检测与绕过

### 检测证书固定

```bash
# 搜索证书固定相关字符串
strings target.exe | grep -E "pin\|pinning\|certificate.*pin\|cert.*pin" | head -20

# 搜索硬编码证书/公钥
strings target.exe | grep -E "BEGIN CERTIFICATE\|BEGIN PUBLIC KEY\|sha256/" | head -20

# 搜索特定域名证书
strings target.exe | grep -E "\.crt\|\.pem\|\.der" | head -20
```

### 绕过策略

| 方法 | 适用场景 | 难度 |
|------|----------|------|
| Hook证书验证 | rustls自定义验证器 | ⭐⭐⭐ |
| 替换硬编码证书 | 内存Patch证书数据 | ⭐⭐⭐⭐ |
| 中间人+自签证书 | 无固定证书时 | ⭐⭐ |
| 修改验证逻辑 | 强制返回验证通过 | ⭐⭐⭐ |

### rustls证书验证Hook

```rust
// 目标：rustls::client::ClientConfig的验证器
// 方法：替换ServerCertVerifier

// Frida脚本示例
Interceptor.attach(Module.findExportByName(null, "_ZN4rustls6client12ClientConfig..."), {
    onEnter: function(args) {
        // 读取ClientConfig结构
        var config = args[0];
        
        // 定位verifier字段（需要分析结构偏移）
        var verifier_offset = 0x40; // 示例偏移，需实际分析
        var verifier_ptr = config.add(verifier_offset);
        
        // 替换为自定义验证器（总是返回true）
        console.log("[+] 替换证书验证器");
        // ... 实现验证器替换
    }
});
```

## 四层防线分析框架

### 防线识别

```
防线1: 网络层 (IP白名单/服务器验证)
├── 特征: 连接前验证服务器IP/域名
├── 检测: 搜索connect/WSAConnect调用
├── 绕过: Hosts劫持/Frida Hook connect

防线2: 传输层 (TLS/证书固定)
├── 特征: rustls/OpenSSL/SChannel
├── 检测: 搜索TLS库字符串/证书验证函数
├── 绕过: Hook验证器/替换证书

防线3: 协议层 (自定义加密/签名)
├── 特征: 自定义二进制协议/数据签名
├── 检测: 分析发送/接收数据格式
├── 绕过: 协议分析+伪造响应

防线4: 应用层 (功能验证/心跳检测)
├── 特征: 功能解锁/定期心跳
├── 检测: 搜索功能检查函数/定时器
├── 绕过: Hook功能检查/伪造心跳响应
```

### 系统化分析流程

```bash
# 1. 识别所有防线
strings target.exe | grep -E "connect\|socket\|WSA\|rustls\|openssl\|cert\|verify" | sort | uniq > network_analysis.txt

# 2. 分析网络调用
objdump -d target.exe | grep -E "call.*connect\|call.*socket" | head -20

# 3. 定位TLS库
strings target.exe | grep -E "rustls.*version\|openssl.*version" | head -10

# 4. 搜索验证函数
strings target.exe | grep -E "verify\|validate\|check\|auth" | grep -i "cert\|server\|client" | head -20
```

## 熵值分析

### 检测加密/压缩数据

```python
import math
from collections import Counter

def calculate_entropy(data):
    """计算数据熵值"""
    if not data:
        return 0
    
    counts = Counter(data)
    length = len(data)
    
    entropy = 0
    for count in counts.values():
        p = count / length
        if p > 0:
            entropy -= p * math.log2(p)
    
    return entropy

def analyze_file_entropy(filepath):
    """分析文件各段熵值"""
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # 整体熵值
    total_entropy = calculate_entropy(data)
    print(f"整体熵值: {total_entropy:.4f} (8.0=完全随机)")
    
    # 分段分析
    chunk_size = 4096
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i+chunk_size]
        entropy = calculate_entropy(chunk)
        
        # 判断类型
        if entropy > 7.5:
            type_str = "加密/压缩/随机"
        elif entropy > 6.0:
            type_str = "可能加密"
        elif entropy > 4.0:
            type_str = "混合数据"
        else:
            type_str = "明文/代码"
        
        print(f"  偏移 0x{i:06X}: 熵值={entropy:.4f} - {type_str}")

# 使用
analyze_file_entropy("target.exe")
```

### 熵值判断标准

| 熵值范围 | 含义 | 处理方式 |
|----------|------|----------|
| 7.5-8.0 | 强加密/压缩 | 需要密钥/算法分析 |
| 6.0-7.5 | 可能加密 | 进一步分析算法 |
| 4.0-6.0 | 混合数据 | 部分可分析 |
| 0-4.0 | 明文/代码 | 直接分析 |

## 失败模式分析

### 常见失败原因

| 失败类型 | 原因 | 解决方案 |
|----------|------|----------|
| 工具不支持 | 无macOS readelf | 使用nm/objdump/纯Python |
| 符号缺失 | Rust混淆符号 | 使用rustfilt/手动解析 |
| 动态分析失败 | 反调试/检测 | 使用Frida anti-anti-debug |
| 协议分析失败 | 自定义加密 | 分析密钥交换/Hook加密函数 |
| 证书固定 | 硬编码证书 | Hook验证器/替换证书 |
| IP白名单 | 服务器验证 | Hosts劫持/Frida Hook |
| 多层防护 | 多防线叠加 | 逐层分析突破 |

### 失败分析流程

```
失败发生
    ↓
[1] 记录失败信息
    ├── 工具名称
    ├── 错误信息
    ├── 目标文件信息
    └── 环境信息
    ↓
[2] 分析失败原因
    ├── 工具限制？
    ├── 目标保护？
    ├── 环境问题？
    └── 操作错误？
    ↓
[3] 寻找替代方案
    ├── 替代工具
    ├── 绕过方法
    ├── 降级分析
    └── 寻求帮助
    ↓
[4] 验证解决方案
    ├── 测试替代工具
    ├── 验证绕过效果
    └── 确认分析结果
    ↓
[5] 记录解决方案
    ├── 更新技能文档
    ├── 添加pitfall
    └── 分享经验
```

## 实战案例：黑曼巴6.16

### 目标信息
- **名称**: 黑曼巴 (BlackMamba) 6.16
- **类型**: Rust编译Windows程序
- **大小**: 53.4MB
- **保护**: 无壳，Rust混淆符号

### 分析过程

#### 1. 识别阶段
```bash
file blackmamba.exe
# PE32+ executable (GUI) x86-64, for MS Windows

strings blackmamba.exe | grep -i rust | head -5
# rust_panic
# RUST_BACKTRACE
# rustls
```

#### 2. 符号分析
```bash
nm blackmamba.exe | grep "_ZN" | wc -l
# 15,234个Rust混淆符号

# 关键符号
strings blackmamba.exe | grep "rustls" | head -10
# rustls::client::ClientConfig
# rustls::client::handshake
# rustls::ServerCertVerifier
```

#### 3. 网络分析
```bash
# 发现四层防线
strings blackmamba.exe | grep -E "115\.159\|111\.170\|47\.96\|47\.242"
# 4个服务器IP

# 发现TLS
strings blackmamba.exe | grep "rustls" | wc -l
# 1,234个rustls相关字符串

# 发现证书固定
strings blackmamba.exe | grep -E "pin\|pinning" | head -5
# 证书固定相关
```

#### 4. 失败与解决

| 失败 | 原因 | 解决方案 |
|------|------|----------|
| readelf不可用 | macOS无readelf | 使用nm/objdump |
| 符号混淆 | Rust命名规则 | 手动解析_ZN前缀 |
| 动态分析困难 | 反调试 | 使用Frida anti-anti-debug |
| 协议复杂 | 自定义二进制 | 需要更深入分析 |

### 关键经验

1. **工具替代**: macOS下readelf缺失时，nm/objdump可替代大部分功能
2. **符号解析**: Rust符号混淆但有规律，可手动还原关键函数
3. **多层分析**: 四层防线需逐层突破，不可期望一次解决
4. **熵值辅助**: 高熵区域提示加密/压缩，低熵区域可分析
5. **失败记录**: 每次失败都记录原因和解决方案，积累知识

## 工具链

| 工具 | 用途 | 替代方案 |
|------|------|----------|
| readelf | ELF分析 | nm, objdump, 纯Python |
| nm | 符号表 | strings + grep |
| objdump | 反汇编 | IDA, Ghidra, radare2 |
| strings | 字符串提取 | 纯Python实现 |
| rustfilt | Rust符号还原 | 手动解析 |
| Frida | 动态分析 | x64dbg, Cheat Engine |
| IDA Pro | 静态分析 | Ghidra, radare2 |

## 参考文档

- `rust-binary-reverse-summary.md` - Rust二进制逆向总结
- `references/elf-encryption-analysis.md` - ELF加密分析
- `references/windows-pe-analysis.md` - Windows PE分析
- `references/frida-request-signing-guide.md` - Frida请求签名逆向
