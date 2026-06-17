# Rust 二进制逆向分析框架

## 适用场景
- Rust 编写的程序（如黑曼巴/BlackMamba）
- 全链路 TLS 加密（rustls）
- IP 校验 + 端口复用
- 证书固定（Certificate Pinning）

## 核心难点

| 保护层级 | 技术 | 破解难度 |
|---------|------|---------|
| 传输加密 | Rustls (TLS) | ⭐⭐⭐⭐⭐ |
| 来源验证 | IP 校验 | ⭐⭐⭐⭐ |
| 连接复用 | 单持久连接 | ⭐⭐⭐⭐ |
| 证书固定 | rustls pinning | ⭐⭐⭐⭐⭐ |

## 分析流程

### 阶段一：环境准备

**必需工具：**
- IDA Pro / Ghidra / Binary Ninja（反编译器）
- radare2 / rizin（开源替代）
- x64dbg / WinDbg / GDB / LLDB（调试器）
- Frida（动态插桩）
- rustfilt / rust-demangler（Rust 符号还原）
- Wireshark（驱动层抓包）

**macOS 环境检查：**
```bash
# 检查可用工具
which lldb && echo "LLDB: $(lldb --version)"
which frida-ps && echo "Frida: $(frida-ps --version)"
which file strings nm objdump

# 安装缺失工具
brew install radare2 ghidra  # 可能超时，考虑手动下载
```

### 阶段二：静态分析

**1. 识别 Rust 编译特征：**
```bash
# 检查文件类型
file target_binary

# 查找 Rust 运行时特征
strings target_binary | grep -i "rust\|rustc\|cargo"

# 检查符号表（如有）
nm target_binary | head -50
objdump -d target_binary | head -100
```

**2. Rust 符号还原：**
```bash
# 使用 rustfilt 还原符号
nm target_binary | rustfilt > demangled_symbols.txt

# 或使用 Python 脚本还原
python3 -c "
import subprocess
symbols = subprocess.check_output(['nm', 'target_binary']).decode()
# 还原 Rust 符号格式
"
```

**3. 定位 rustls 相关代码：**
- 搜索 `rustls` 字符串
- 查找 TLS 握手函数：`client_hello`, `server_hello`, `finish`
- 查找证书校验函数：`verify_certificate`, `check_pin`

### 阶段三：动态分析

**1. 调试器附加：**
```bash
# LLDB (macOS)
lldb target_binary
(lldb) breakpoint set --name rustls::client::ClientConnection::new
(lldb) run

# 或 Frida 插桩
frida -f target_binary -l trace_tls.js
```

**2. 关键断点：**
- TLS 握手入口
- 证书校验函数
- 数据发送/接收函数
- IP 校验逻辑

**3. 内存分析：**
- 找解密后的数据缓冲区
- 跟踪协议格式解析
- 定位关键验证函数

### 阶段四：协议分析

**1. 驱动层抓包（Wireshark）：**
- 即使 TLS 加密，仍可分析握手过程
- 查看 SNI（Server Name Indication）
- 分析证书交换

**2. 内存 Dump 分析：**
- 在解密后、加密前拦截数据
- 找明文协议格式
- 识别请求/响应结构

### 阶段五：Patch 方案

**1. 证书固定绕过：**
- 定位 rustls 证书校验代码
- Patch 校验函数返回 true
- 或替换内置证书

**2. IP 校验绕过：**
- Hook 获取 IP 的函数
- 返回伪造的合法 IP

**3. 协议重放/伪造：**
- 分析成功响应格式
- 构建伪造响应
- 拦截并替换真实响应

## 工具安装（macOS）

```bash
# radare2（开源逆向框架）
brew install radare2
# 或手动安装
git clone https://github.com/radareorg/radare2.git
cd radare2
sys/install.sh

# Ghidra（免费反编译器）
brew install --cask ghidra
# 或从官网下载：https://ghidra-sre.org/

# rustfilt（Rust 符号还原）
cargo install rustfilt
# 或 pip install rust-demangler
```

## 已知陷阱

| 陷阱 | 说明 | 解决 |
|------|------|------|
| brew 安装超时 | radare2/ghidra 安装耗时 | 手动下载或使用预编译包 |
| 符号缺失 | Rust 发布构建剥离符号 | 使用字符串分析 + 函数特征识别 |
| 反调试 | Rust 程序可能集成反调试 | 使用 Frida 绕过或内核调试 |
| 异步运行时 | Rust async/await 增加分析复杂度 | 跟踪 tokio/async-std 运行时 |

## 实战案例

### 案例：黑曼巴（BlackMamba）

**目标：** Rust 编写的程序，rustls TLS + IP 校验 + 端口复用

**分析步骤：**
1. 确认程序类型：`file blackmamba` → Mach-O/ELF/PE
2. 检查保护：`strings blackmamba | grep -i "rustls\|tls\|cert\|pin"`
3. 符号分析：`nm blackmamba | rustfilt | grep -i "tls\|cert\|verify"`
4. 动态调试：LLDB/Frida 附加，断点 TLS 握手
5. 协议分析：Wireshark 抓包 + 内存 Dump
6. Patch：证书固定绕过 + IP 校验绕过

**预期难点：**
- 证书固定导致 MITM 无效
- IP 校验导致代理无效
- 单连接复用增加拦截难度

## 替代方案

如果逆向难度过高，考虑：
1. **正版卡密** — 当前唯一实际可行方案
2. **找未保护版本** — 旧版本可能保护较弱
3. **服务端模拟** — 搭建假服务器，修改 hosts 指向
4. **内存修改** — 运行时修改验证状态（需绕过反调试）

## 参考

- rustls 文档：https://docs.rs/rustls/
- Rust 二进制分析：https://lief-project.github.io/doc/latest/tutorials/11_rust.html
- Frida Rust 插桩：https://frida.re/docs/functions/
