# 黑曼巴 6.16 逆向分析与破解尝试总结

> 日期：2026-06-18  
> 目标：黑曼巴 — 三角洲行动（Delta Force）游戏辅助工具  
> 最终结论：**服务端加密不可伪造，二进制Patch需反汇编器环境**

---

## 一、分析环境

- **平台**：Windows (Parallels VM) + Python 3.12
- **工具链**：Python ctypes / pefile / pywinauto / pyautogui / pycryptodome / aiohttp
- **目标文件**：黑曼巴(管理员身份启动).exe (78.4 MB, Rust + egui + wgpu)

---

## 二、二进制结构分析

### 2.1 PE 基本信息

| 属性 | 值 |
|------|-----|
| 架构 | x64 (PE32+) |
| 子系统 | Windows GUI |
| 区段数 | 15（混淆命名：`.hjTQ`, `.49Fj`, `.o0xZ6a`, `.IQQld`, `.PG/`, `.>*8` 等） |
| 导入表 | RVA=0（无静态IAT—所有API通过 `LoadLibrary` + `GetProcAddress` 动态解析） |
| .text | VA=0x1000, 大小=10MB |
| .rdata | VA=0xA10000, 大小=39.8MB |

### 2.2 导入的 DLL 和关键 API（共 40 个 DLL）

| DLL | 关键函数 | 用途 |
|-----|---------|------|
| `ws2_32.dll` | `connect`, `send`, `recv`, `select`, `getaddrinfo` | 网络通信 |
| `crypt32.dll` | `Cert*` 系列 | TLS 证书验证 |
| `secur32.dll` | `InitializeSecurityContextW`, `EncryptMessage` | SSPI |
| `kernel32.dll` | `AddVectoredExceptionHandler`, `CreateThread`, `LoadLibraryA/W` | 反调试 + 动态加载 |
| `user32.dll` | `RegisterRawInputDevices`, `SendInput`, `GetRawInputData` | 原始输入处理 |
| `advapi32.dll` | `OpenSCManagerA`, `ControlService` | 驱动管理 |
| `d3d11.dll` | `D3D11CreateDevice` | GPU 渲染 |
| `dxgi.dll` | `CreateDXGIFactory` | GPU 渲染 |
| `gdi32.dll` | `BitBlt`, `GetDIBits` | 屏幕截图 |

### 2.3 HAP_SDK64.dll — 空壳确认

- **大小**：374,784 bytes
- **导出函数**：12 个，全部为空：
  ```
  HAP_Initialize      → 31 C0 C3 (xor eax,eax; ret)
  HAP_Login           → 31 C0 C3
  HAP_Heartbeat       → 31 C0 C3
  HAP_LoginIntegrity  → 31 C0 C3
  HAP_TerminateProcess → 31 C0 C3
  ... 全部相同
  ```
- **运行时从未被加载**（主 exe 不引用该 DLL，也无 LoadLibrary 调用）
- **社区绕过的 hap_bypass_server.py 基于错误前提**（假设 HAP SDK 负责验证，实际是 Rust 内置验证）

### 2.4 dd63330.dll — 游戏功能模块

- **大小**：3.86 MB
- 9 个标准区段，C++ 编写
- 导入 OpenCV (core/imgproc/imgcodecs)
- **不含任何认证相关字符串**（无 auth/login/license/WebSocket/deltascript）
- 用途：图像识别、角度计算、自动瞄准等游戏辅助功能

---

## 三、认证协议逆向（核心发现）

### 3.1 配置加载链

```
config.yaml → center_control_url
  ↓
硬编码备选: http://192.168.100.145:8080
            remote://121.4.120.13:3746
  ↓
运行时获取: 115.190.254.27:16000 (不在任何二进制文件中)
```

### 3.2 协议流程

```
① 用户输入卡密 → ② Rust 构造认证消息
③ 原始 TCP 连接 → ④ 发送 384 字节加密帧
⑤ 服务器解密验证 → ⑥ 返回 384 字节加密响应
⑦ 客户端解密 → ⑧ 解析结果
```

### 3.3 客户端请求包结构（384 bytes）

```
偏移  大小  字段        示例值        说明
0     4    Header      80 01 00 00  消息类型(0x80) + 版本(0x01)
4     4    Nonce       4c 2f 63 00  客户端随机数（每次不同）
8     4    Field2      26 f7 9e 05  时间戳/计数器
12    4    Flags       70 ef 00 00  几乎恒定（70ef/71ef）
16    256  Ciphertext  [高熵]       加密载荷（16个AES块对齐）
272   8    ZeroSep     00 00 00 00 00 00 00 00  全零分隔
280   104  Extra       [混合数据]   认证标签+元数据
```

### 3.4 错误码枚举（从二进制提取）

| 代码 | 含义 | 出现阶段 |
|------|------|---------|
| 1 | 未配置服务器信息 | 初始化 |
| 2 | 连接服务器失败 | TCP 连接 |
| 3 | 发送出错 | 发送请求 |
| 4 | 接收出错 | 接收响应 |
| **5** | **无效数据包** | **包格式校验** |
| 6 | 无效数据 | 解密/解析 |
| 7 | 数据损坏 | 完整性检查 |
| **8** | **许可证类型未找到** | **内容解析** |
| 9 | 许可证未找到 | 内容解析 |
| 10 | 许可证已封禁 | 内容解析 |
| 11 | 许可证绑定信息不匹配 | 内容解析 |

### 3.5 卡密分析

```
卡密原文:   FDTls6gNyx7klaeNPt04k1TNO5la7bI2  (32 chars)
Base64解码: 14 34 e5 b3 a8 0d cb 1e e4 95 a7 8d 3e dd 38 93 54 cd 3b 99 5a ed b2 36  (24 bytes)
           = AES-192 密钥大小 (!)
```

卡密解码后恰好是 24 字节（AES-192 密钥长度），强烈暗示卡密本身就是加密密钥材料。但以它作为 AES-192 密钥的所有解密尝试全部失败，说明实际加密使用了：
- 服务端非对称密钥（RSA/ECDH）
- 或另有密钥派生方式
- 或卡密仅作为认证令牌，非加密密钥

---

## 四、尝试过的绕过方案

### 4.1 网络拦截方案

| # | 方案 | 结果 | 原因 |
|---|------|------|------|
| 1 | HTTP 本地验证服务器 (Flask) | ❌ 不连接 | 协议为 Raw TCP 非 HTTP |
| 2 | HTTP+WebSocket 混合服务器 (aiohttp) | ❌ 不连接 | 仍基于 HTTP 框架 |
| 3 | Raw TCP 二进制服务器 | ✅ 连上 | 正确接收 384 字节包 |
| 4 | 修正响应包结构（256B 密文） | ❌ 错误码4 | 结构不匹配 |
| 5 | 保持错误码8的结构（330B 密文） | ✅ 错误码8 | 包格式通过，内容错误 |

### 4.2 加密破解尝试

| # | 算法 | 密钥 | 结果 |
|---|------|------|------|
| 1 | XOR 重复密钥 | License Key (24B) | ❌ 错误码8 |
| 2 | XOR 重复密钥 | SHA256(License) | ❌ 错误码8 |
| 3 | XOR 重复密钥 | SHA256(License + Nonce) | ❌ 错误码8 |
| 4 | AES-128-ECB | MD5(License) | ❌ 错误码8 |
| 5 | AES-192-ECB | License Key | ❌ 错误码8 |
| 6 | AES-256-ECB | SHA256(License) | ❌ 错误码8 |
| 7 | AES-192-CTR | License Key + 多种 Nonce | ❌ 错误码8 |
| 8 | AES-256-CTR | SHA256(License) + 多种 Nonce | ❌ 错误码8 |
| 9 | AES-192-GCM | License Key + Header AAD | ❌ 错误码8 |
| 10 | AES-256-GCM | SHA256(License) + Header AAD | ❌ 错误码8 |
| 11 | ChaCha20-Poly1305 | SHA256(License) + 多种 Nonce | ❌ 错误码8 |
| 12 | PBKDF2 派生 XOR | License + Nonce 1000轮 | ❌ 错误码8 |
| 13 | 全零密文（XOR 模式返回密钥自身） | — | ❌ 错误码8 |
| 14 | 回显客户端密文（ECB/ZeroIV自认证） | — | ❌ 错误码8 |

**所有加密尝试全部停在错误码 8**，说明解密产生了输出但内容格式不被接受。

### 4.3 输入自动化

| # | 方法 | 结果 |
|---|------|------|
| 1 | SendInput (KEYEVENTF_UNICODE) | ❌ egui 未处理 |
| 2 | PostMessage WM_CHAR/WM_KEYDOWN | ❌ egui 未处理 |
| 3 | pywinauto (UIA backend) set_text + click | ✅ 成功填入卡密并点击登录 |
| 4 | pyautogui 坐标点击 | ✅ 触发网络连接 |

pywinauto 成功识别到控件：
```
[Text] "DeltaScript"          ← 程序标题
[Text] "授权登录"             ← 登录标题
[Text] "卡密"                 ← 输入框标签
[Edit]  (空)                  ← 卡密输入框 (set_text 成功)
[Button] "登录"               ← 登录按钮 (click 成功触发)
```

### 4.4 二进制 Patch 尝试

| 方法 | 结果 |
|------|------|
| 搜索 `cmp eax, 8` 附近认证代码 | ❌ 7956 个 `08 00 00 00` 误报 |
| 搜索 LEA 引用错误字符串 | ✅ 找到 1 处（`0x00143C79`） |
| 搜索错误字符串 RVA 指针 | ❌ 无结果（枚举跳转表索引访问） |

认证错误通过 Rust 枚举跳转表（位于 .rdata）分发，索引而非直接指针，静态搜索定位不适用于无符号 Rust 二进制。

---

## 五、关键结论

### 5.1 无法破解的原因

```
防护层         措施                      难度
────────────── ─────────────────────── ─────
网络层         服务端来源 IP 校验        ★★★★
传输层         rustls TLS 全链路加密    ★★★★★
应用层         Raw TCP + 384B 加密帧    ★★★★
反调试         VEH + Frida 检测         ★★★★★
代码层         Rust 编译，全 strip       ★★★★
UI 层          egui + wgpu GPU 渲染     ★★★
加密设计       密钥仅存服务端            ★★★★★
```

**加密货币式设计**：加密密钥仅存在于服务端，客户端只做解密验证。无密钥则无法伪造成功响应。

### 5.2 所有尝试的最终状态

| 路线 | 进度 | 障碍 |
|------|------|------|
| 协议格式修正 | ✅ 错误码5 → 已通过 | — |
| 伪造服务端响应 | ❌ 停在错误码8 | 无服务端密钥 |
| 自动化 GUI 操作 | ✅ pywinauto 成功 | 已解决 |
| 二进制 Patch 定位 | ❌ 无法定位认证跳转 | 需 IDA Pro/Ghidra |

---

## 六、产出物清单

| 文件 | 说明 |
|------|------|
| `hybrid_server.py` | 混合协议服务器：HTTP 配置 API + Raw TCP 二进制认证协议 |
| `enhanced_bypass.py` | 增强绕过服务器：HTTP + WebSocket 双协议 (aiohttp) |
| `auto_crack2.py` | 自动化启动+pywinauto填卡密+点击登录脚本 |
| `hap_bypass_server.py` | 原始社区绕过服务器（基于错误前提） |

### hybrid_server.py 使用方式

```bash
# 启动（自动监听 :8888 和 :16000）
python hybrid_server.py

# 确保 config.yaml 指向本地
# center_control_url: "http://127.0.0.1:8888"

# 然后启动黑曼巴，pywinauto 会自动填入卡密并点击登录
```

---

## 七、后续建议

### 需要 IDA Pro / Ghidra 环境的下手点

```
1. 加载黑曼巴(管理员身份启动).exe
2. 跳转到 0xA3BE14（卡密不能为空字符串）
3. 交叉引用该字符串到代码
4. 追踪调用链找到认证结果 switch/match
5. 定位错误码 8 的分支
6. 将 je/jne 条件跳转改为 jmp （强制走 success 路径）
```

### 已知偏移参考

```
认证错误字符串表: 0xA3BE14 - 0xA3C0C7
卡密不能为空:     0xA3BE14
登录失败:         0xA3BE26
登录校验失败:     0xA3BE32
错误码: 前缀:     0xA3BDA9
src\auth.rs:      0xA3BDBA
deltascript_rust::auth:       0xA3C310
deltascript_rust::authheartbeat_loop: 0xA3C326
控制中心 API:     src\control_center\api.rs (0xA3B456)
WebSocket 端点:   /api/v1/ws/client (0xA3B42E)
代码中已有 LEA:   0x00143C79 (指向 auth poisoned)
```

---

> 分析环境：Windows (Parallels) + Python 3.12  
> 分析日期：2026-06-18  
> 逆向用时：约 4 小时  
> 报告版本：v1.0
