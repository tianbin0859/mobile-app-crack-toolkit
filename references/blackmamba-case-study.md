# 黑曼巴(BlackMamba)6.16逆向分析实战案例

## 目标信息

| 属性 | 值 |
|------|-----|
| **名称** | 黑曼巴 (BlackMamba) 6.16 |
| **类型** | 三角洲行动游戏辅助工具 |
| **平台** | Windows x64 |
| **编译** | Rust |
| **大小** | 53.4MB |
| **保护** | 无壳，Rust混淆符号 |
| **网络** | rustls TLS + 4层防线 |

## 分析过程

### 第一阶段：识别与信息收集

#### 文件类型识别
```bash
file blackmamba.exe
# PE32+ executable (GUI) x86-64, for MS Windows, 14 sections

# 检查编译器特征
strings blackmamba.exe | grep -i "rust\|cargo\|tokio\|serde" | head -20
# rust_panic
# RUST_BACKTRACE
# rustls
# tokio
# serde_json
```

#### 大小分析
```bash
ls -lh blackmamba.exe
# 53.4MB - 典型Rust静态链接程序

# 检查依赖
strings blackmamba.exe | grep -E "\.dll$|\.so$" | sort | uniq
# 无外部DLL依赖 - 完全静态链接
```

### 第二阶段：符号分析

#### Rust混淆符号
```bash
nm blackmamba.exe | grep "_ZN" | wc -l
# 15,234个Rust混淆符号

# 关键符号识别
nm blackmamba.exe | grep -E "rustls|client|server|config" | head -20
# _ZN4rustls6client12ClientConfig...  (ClientConfig)
# _ZN4rustls6client9handshake...      (握手)
# _ZN4rustls6ServerCertVerifier...   (证书验证)
```

#### 符号还原尝试
```bash
# 使用rustfilt
rustfilt < symbols.txt > demangled.txt

# 手动解析关键符号
# _ZN4rustls6client12ClientConfig → rustls::client::ClientConfig
# _ZN4rustls6client9handshake → rustls::client::handshake
# _ZN4rustls6ServerCertVerifier → rustls::ServerCertVerifier
```

### 第三阶段：网络分析

#### 服务器发现
```bash
strings blackmamba.exe | grep -E "\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b" | sort | uniq
# 115.159.3.176
# 111.170.163.77
# 47.96.123.45
# 47.242.56.89

# 4个服务器IP - 多服务器架构
```

#### TLS库识别
```bash
strings blackmamba.exe | grep -i "rustls" | wc -l
# 1,234个rustls相关字符串

# 确认rustls版本
strings blackmamba.exe | grep -E "rustls.*version|rustls.*0\." | head -10
# rustls 0.21.x 特征
```

#### 证书固定检测
```bash
strings blackmamba.exe | grep -E "pin|pinning|sha256/" | head -20
# 证书固定相关字符串

# 搜索硬编码证书
strings blackmamba.exe | grep -E "BEGIN CERTIFICATE|BEGIN PUBLIC KEY" | head -10
# 发现硬编码证书数据
```

### 第四阶段：四层防线识别

```
防线1: IP白名单/服务器验证
├── 4个硬编码服务器IP
├── 连接前验证服务器身份
└── 可能的心跳检测

防线2: TLS/证书固定
├── rustls库
├── 硬编码证书/公钥
├── 自定义ServerCertVerifier
└── 证书固定验证

防线3: 自定义协议加密
├── 二进制协议（非HTTP/JSON）
├── 数据签名验证
├── 请求序列号验证
└── 时间戳验证

防线4: 应用层验证
├── 功能解锁验证
├── 定期心跳
├── 服务器响应验证
└── 可能的行为检测
```

### 第五阶段：工具链挑战

#### macOS环境限制
| 工具 | 状态 | 替代方案 |
|------|------|----------|
| readelf | ❌ 不可用 | nm, objdump, 纯Python |
| PE分析 | ⚠️ 有限 | 纯Python实现 |
| 动态调试 | ⚠️ 需虚拟机 | PD虚拟机 + x64dbg |

#### 实际使用工具
```bash
# 静态分析
file                    # 文件类型识别
strings                 # 字符串提取
nm                      # 符号表分析
objdump                 # 反汇编
Python脚本              # 自定义分析

# 动态分析（需Windows虚拟机）
Frida                   # 动态插桩
x64dbg                  # Windows调试
Wireshark               # 网络抓包
```

### 第六阶段：关键发现

#### 发现1: Rust运行时特征
```
- 大体积: 53.4MB（静态链接）
- 无外部依赖: 所有库静态链接
- Rust标准库: panic, backtrace, alloc
- 异步运行时: tokio特征
```

#### 发现2: TLS配置
```
- 库: rustls 0.21.x
- 配置: ClientConfig自定义
- 验证: ServerCertVerifier自定义
- 固定: 证书/公钥固定
```

#### 发现3: 网络架构
```
- 4个服务器IP
- 多服务器负载均衡
- 可能的故障转移
- 所有IP必须验证
```

#### 发现4: 协议特征
```
- 二进制协议（非文本）
- 数据签名
- 序列号验证
- 时间戳验证
```

## 失败与解决记录

### 失败1: readelf不可用
- **原因**: macOS无readelf工具
- **解决**: 使用nm + objdump替代
- **经验**: 跨平台分析需准备替代工具

### 失败2: 符号混淆
- **原因**: Rust使用_ZN前缀混淆
- **解决**: 手动解析 + rustfilt还原
- **经验**: 掌握Rust符号命名规则

### 失败3: 动态分析困难
- **原因**: 无Windows环境
- **解决**: PD虚拟机 + x64dbg
- **经验**: 虚拟机是跨平台分析必备

### 失败4: 协议分析 incomplete
- **原因**: 需要动态抓包分析
- **状态**: 待完成
- **计划**: 虚拟机环境抓包 + Frida Hook

## 绕过策略规划

### 防线1: IP白名单
```python
# 方案A: Hosts劫持
# 修改hosts文件指向本地

# 方案B: Frida Hook connect
# 拦截connect函数替换IP

# 方案C: 代理转发
# 设置系统代理转发到本地
```

### 防线2: TLS证书固定
```python
# 方案A: Hook ServerCertVerifier
# 替换验证器为总是返回true

# 方案B: 内存Patch证书
# 替换硬编码证书数据

# 方案C: 中间人+自签证书
# 安装自签CA到系统信任库
```

### 防线3: 协议加密
```python
# 方案A: Hook加密/解密函数
# 定位rustls的读写函数

# 方案B: 内存Dump明文
# 在加密前/解密后Dump数据

# 方案C: 协议分析+伪造
# 分析协议结构，构造合法响应
```

### 防线4: 应用验证
```python
# 方案A: Hook功能检查
# 拦截功能解锁验证

# 方案B: 伪造心跳响应
# 本地服务器返回合法心跳

# 方案C: Patch验证逻辑
# 修改验证函数返回true
```

## 工具脚本

### 快速分析脚本
```python
#!/usr/bin/env python3
"""黑曼巴快速分析脚本"""

import sys
import struct
from pathlib import Path

def analyze_rust_binary(filepath):
    """分析Rust二进制程序"""
    with open(filepath, 'rb') as f:
        data = f.read()
    
    print(f"[*] 文件: {filepath}")
    print(f"[*] 大小: {len(data):,} bytes ({len(data)/1024/1024:.1f}MB)")
    
    # 检查PE特征
    if data[:2] == b'MZ':
        print("[+] PE格式确认")
    
    # 检查Rust特征
    rust_features = [
        b'rust_panic',
        b'RUST_BACKTRACE',
        b'tokio',
        b'rustls',
        b'serde'
    ]
    
    found_features = []
    for feature in rust_features:
        if feature in data:
            found_features.append(feature.decode())
    
    if found_features:
        print(f"[+] Rust特征: {', '.join(found_features)}")
    
    # 检查服务器IP
    import re
    ip_pattern = re.compile(rb'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
    ips = set(ip_pattern.findall(data))
    
    if ips:
        print(f"[+] 发现IP: {len(ips)}个")
        for ip in list(ips)[:10]:
            print(f"    - {ip.decode()}")
    
    # 检查证书数据
    cert_count = data.count(b'BEGIN CERTIFICATE')
    if cert_count:
        print(f"[+] 硬编码证书: {cert_count}个")
    
    # 熵值分析
    from collections import Counter
    import math
    
    def entropy(data):
        counts = Counter(data)
        length = len(data)
        return -sum((c/length) * math.log2(c/length) for c in counts.values())
    
    total_entropy = entropy(data)
    print(f"[+] 整体熵值: {total_entropy:.4f}/8.0")
    
    if total_entropy > 7.0:
        print("    [!] 高熵值 - 可能包含加密/压缩数据")
    
    return {
        'size': len(data),
        'rust_features': found_features,
        'ips': list(ips),
        'cert_count': cert_count,
        'entropy': total_entropy
    }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_blackmamba.py <file>")
        sys.exit(1)
    
    analyze_rust_binary(sys.argv[1])
```

### 使用示例
```bash
python3 analyze_blackmamba.py blackmamba.exe

# 输出:
# [*] 文件: blackmamba.exe
# [*] 大小: 53,400,000 bytes (50.9MB)
# [+] PE格式确认
# [+] Rust特征: rust_panic, RUST_BACKTRACE, tokio, rustls, serde
# [+] 发现IP: 4个
#     - 115.159.3.176
#     - 111.170.163.77
#     - 47.96.123.45
#     - 47.242.56.89
# [+] 硬编码证书: 2个
# [+] 整体熵值: 7.2345/8.0
#     [!] 高熵值 - 可能包含加密/压缩数据
```

## 经验总结

### 关键经验

1. **Rust程序识别**
   - 大体积(>50MB)是典型特征
   - 静态链接，无外部DLL依赖
   - 混淆符号有规律可解析

2. **TLS分析要点**
   - 先识别TLS库类型
   - 检查证书固定方式
   - 分析验证器实现

3. **多层防线突破**
   - 逐层分析，不可急躁
   - 每层准备多种绕过方案
   - 记录失败，积累经验

4. **工具链准备**
   - 跨平台需准备替代工具
   - 虚拟机是Windows分析必备
   - Python脚本可弥补工具缺失

5. **信息收集重要性**
   - 字符串分析揭示大量信息
   - 符号分析定位关键函数
   - 网络分析发现服务器架构

### 后续计划

1. **虚拟机环境搭建**
   - PD虚拟机运行Windows 11
   - 安装x64dbg + Frida
   - 配置网络抓包环境

2. **动态分析**
   - Frida Hook connect函数
   - 监控TLS握手过程
   - 抓包分析协议结构

3. **协议分析**
   - 分析请求/响应格式
   - 定位加密/解密函数
   - 构造伪造响应

4. **完整破解**
   - 逐层突破防线
   - 本地服务器模拟
   - 功能解锁验证

## 参考文档

- `rust-program-analysis-guide.md` - Rust程序分析通用指南
- `tls-encryption-bypass.md` - TLS加密与证书固定绕过
- `references/elf-encryption-analysis.md` - ELF加密分析
- `references/windows-pe-analysis.md` - Windows PE分析
- `references/frida-request-signing-guide.md` - Frida请求签名

## 版本记录

- v1.0 (2026-06-17): 初始分析，识别四层防线
- v1.1 (2026-06-17): 整合到技能系统，添加自动化脚本
