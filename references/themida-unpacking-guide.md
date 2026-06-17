# Themida 脱壳实战指南

> 针对 Themida + SecureEngine + HAP SDK 保护的 Windows 程序脱壳与破解

## 目标程序特征

**MC副机6.7.exe 分析结果：**
- 保护壳: Themida (WinLicense) + SecureEngine
- 附加保护: HAP SDK (网络验证)
- 架构: 64位 PE (x86-64)
- 文件大小: ~2.8MB (主程序)
- 依赖: SecureEngineSDK64.dll

## 工具链

| 工具 | 用途 | 版本 |
|------|------|------|
| x64dbg | 64位调试器 | 最新版 |
| Themidie | Themida 脱壳插件 | 最新版 |
| ScyllaHide | 反调试绕过插件 | 最新版 |
| Scylla | IAT修复/PE重建 | 内置 |
| PE-Bear | PE文件分析 | 可选 |

## 脱壳流程

### 阶段一：环境准备

```powershell
# 1. 创建破解工作目录
mkdir C:\Crack

# 2. 复制目标程序到工作目录
copy "C:\Users\User\Desktop\MC副机6.7.exe" C:\Crack\
copy "C:\Users\User\Desktop\SecureEngineSDK64.dll" C:\Crack\

# 3. 启动 x64dbg (管理员权限)
# 右键 x64dbg.exe → 以管理员身份运行
```

### 阶段二：插件配置

**Themidie 插件配置：**
1. 打开 x64dbg → 选项 → 插件
2. 确认 Themidie.dp64 已加载
3. 配置 Themidie:
   - 脱壳模式: `Auto (自动检测)`
   - IAT修复: `Enabled`
   - 反调试绕过: `Enabled`
   - 输出目录: `C:\Crack\dumped\`

**ScyllaHide 配置：**
1. 打开 x64dbg → 选项 → 插件 → ScyllaHide
2. 选择预设: `Themida / WinLicense`
3. 启用选项:
   - ✅ Hide from FindWindow
   - ✅ Hide from EnumWindows
   - ✅ Hide from GetTickCount
   - ✅ Hide from NtQueryInformationProcess
   - ✅ Hide debug registers
   - ✅ Hide from NtSetInformationThread
   - ✅ Hide from OutputDebugString
   - ✅ Handle NtCreateThreadEx
   - ✅ Handle NtSetContextThread
   - ✅ Handle NtResumeThread
   - ✅ Handle NtClose (invalid handle)
   - ✅ Hide from NtQuerySystemInformation
   - ✅ Hide from NtYieldExecution
   - ✅ Hide from NtQueryObject
   - ✅ Hide from NtQueryPerformanceCounter
   - ✅ Hide from timeGetTime
   - ✅ Hide from GetLocalTime
   - ✅ Hide from GetSystemTime
   - ✅ Hide from NtGetWriteWatch
   - ✅ Hide from NtQueryInformationProcess (ProcessDebugFlags)
   - ✅ Hide from NtQueryInformationProcess (ProcessDebugPort)
   - ✅ Hide from NtQueryInformationProcess (ProcessDebugObjectHandle)
   - ✅ Start anti-anti-debug

### 阶段三：脱壳执行

```
1. x64dbg 打开 MC副机6.7.exe
2. 等待程序加载到入口点 (OEP)
3. Themidie 自动检测壳类型
4. 按 F9 运行程序
5. Themidie 在合适时机自动脱壳
6. 脱壳完成后，dump 文件保存到 C:\Crack\dumped\
```

**手动脱壳（自动失败时）：**
```
1. 设置断点到常见 API:
   - bp GetProcAddress
   - bp LoadLibraryA
   - bp VirtualAlloc
   - bp VirtualProtect

2. 按 F9 运行，多次命中断点后观察堆栈

3. 当发现大量连续内存分配时，可能是 IAT 重建阶段

4. 在 VirtualProtect 返回前设置条件断点:
   保护属性为 PAGE_EXECUTE_READWRITE 时暂停

5. 在内存中搜索 PE 头特征 (MZ...)

6. 找到原始 PE 后，使用 Scylla  dump 进程
```

### 阶段四：IAT 修复

```
1. 打开 Scylla (x64dbg 插件菜单)
2. 选择正确的进程
3. 点击 "IAT Autosearch"
4. 如果自动搜索失败，手动指定 IAT 地址:
   - 在内存中搜索 kernel32.dll 字符串
   - 向上找到 IAT 表起始地址
   - 输入到 Scylla 的 RVA 字段

5. 点击 "Get Imports"
6. 检查导入表完整性:
   - 所有 API 应显示为绿色 (已识别)
   - 红色条目需要手动修复

7. 点击 "Fix Dump"
8. 选择之前 dump 的文件
9. 输出修复后的 PE 文件
```

### 阶段五：验证脱壳结果

```powershell
# 1. 检查文件大小
ls C:\Crack\dumped\MC副机6.7_dump.exe
# 正常应比原文件大 (包含解压后的代码)

# 2. 检查 PE 结构
# 使用 PE-Bear 或 CFF Explorer 打开
# 确认:
# - 节表正常 (.text, .data, .rsrc)
# - 导入表完整
# - 无 Themida 特征节 (.themida, .secure)

# 3. 尝试运行
C:\Crack\dumped\MC副机6.7_dump.exe
# 如果正常运行，脱壳成功
# 如果崩溃，可能需要修复重定位表或 TLS
```

## HAP SDK 网络验证分析

### 识别 HAP SDK

```
脱壳后，在导入表中搜索:
- HAP_Initialize
- HAP_VerifyLicense
- HAP_CheckAuth
- HAP_GetUserInfo

在字符串中搜索:
- "hap." 域名
- "license" 相关字符串
- 加密/解密函数名
```

### 绕过策略

**策略1: Hook HAP API**
```c
// 使用 MinHook 或 Detours
// 在脱壳后的程序中 Hook HAP_VerifyLicense

typedef int (*HAP_VerifyLicense_t)(const char* license_key);
HAP_VerifyLicense_t original_verify = NULL;

int hooked_verify(const char* license_key) {
    // 强制返回验证成功
    return 0; // 0 = 成功
}

// 安装 Hook
MH_Initialize();
MH_CreateHook(
    (LPVOID)GetProcAddress(hHAP, "HAP_VerifyLicense"),
    (LPVOID)hooked_verify,
    (LPVOID*)&original_verify
);
MH_EnableHook(MH_ALL_HOOKS);
```

**策略2: Patch 验证函数**
```
1. 在 x64dbg 中定位 HAP_VerifyLicense
2. 找到返回指令 (ret 或 mov eax, xxx; ret)
3. 修改返回值:
   - 原: mov eax, 1 (失败)
   - 改: mov eax, 0 (成功)
4. 保存修改到文件
```

**策略3: 修改 Hosts**
```
# 将 HAP 验证服务器指向本地
127.0.0.1  hap.example.com
127.0.0.1  auth.hapserver.com

# 启动本地假服务器响应验证请求
```

**策略4: 内存 Patch (运行时)**
```python
import pymem

# 附加到运行中的进程
pm = pymem.Pymem("MC副机6.7.exe")

# 搜索 HAP 验证函数特征码
pattern = b"\x48\x89\x5C\x24\x08\x48\x89\x74\x24\x10"
address = pm.pattern_scan_module(pm.process_handle, "HAP.dll", pattern)

# Patch 返回成功
# 将函数开头改为: mov eax, 0; ret
patch = b"\xB8\x00\x00\x00\x00\xC3"
pm.write_bytes(address, patch, len(patch))
```

## 常见问题

### 问题1: 脱壳后程序崩溃

**原因:**
- IAT 未完全修复
- 重定位表损坏
- TLS 回调未处理
- 反调试检测未完全绕过

**解决:**
1. 使用 Scylla 的 "Rebuild PE" 功能
2. 手动修复重定位表 (使用 PE-Bear)
3. 检查并修复 TLS 目录
4. 确保 ScyllaHide 所有选项已启用

### 问题2: 无法找到 OEP

**解决:**
1. 使用 Themidie 的 "Trace to OEP" 功能
2. 手动设置断点到常见 OEP 模式:
   - `push rbp; mov rbp, rsp`
   - `sub rsp, 0xXX`
   - `mov rcx, [rip+0xXX]`
3. 使用 ESP 定律: 在栈平衡后设置硬件断点

### 问题3: HAP 验证绕过失败

**原因:**
- HAP 使用多验证点
- 验证结果加密传输
- 有二次验证 (心跳检测)

**解决:**
1. 使用 API Monitor 监控所有 HAP API 调用
2. 分析验证协议，找到所有验证点
3. 同时 Hook 所有验证函数
4. 如果存在心跳检测，Hook 心跳函数返回正常

## 完整破解流程图

```
MC副机6.7.exe (Themida + HAP)
    ↓
[1] 环境准备
    ├─→ 安装 x64dbg + Themidie + ScyllaHide
    ├─→ 配置 ScyllaHide (Themida 预设)
    └─→ 创建破解工作目录
    ↓
[2] 脱壳
    ├─→ 打开程序到 x64dbg
    ├─→ Themidie 自动检测壳
    ├─→ 运行程序触发脱壳
    ├─→ Dump 进程内存
    └─→ Scylla 修复 IAT
    ↓
[3] 验证脱壳
    ├─→ 检查 PE 结构
    ├─→ 测试运行
    └─→ 修复崩溃问题
    ↓
[4] 分析 HAP 验证
    ├─→ 搜索 HAP API
    ├─→ 定位验证函数
    ├─→ 分析验证逻辑
    └─→ 确定绕过策略
    ↓
[5] 绕过验证
    ├─→ Hook HAP_VerifyLicense → 返回成功
    ├─→ Patch 验证结果检查
    ├─→ 可选: 修改 Hosts/启动假服务器
    └─→ 验证所有功能解锁
    ↓
[6] 输出
    ├─→ 脱壳后的可执行文件
    ├─→ Patch 后的可执行文件 (可选)
    ├─→ DLL 注入器 (如果采用 Hook 方案)
    └─→ 使用说明
```

## 工具下载链接

| 工具 | 下载地址 | 获取方式 |
|------|----------|----------|
| x64dbg | https://github.com/x64dbg/x64dbg/releases | GitHub API 动态获取 |
| Themidie | https://github.com/VenTaz/Themidie/releases | GitHub API 动态获取 |
| ScyllaHide | https://github.com/x64dbg/ScyllaHide/releases | GitHub API 动态获取 |

**GitHub API 获取最新版：**
```python
import requests

def get_latest_release(repo):
    """获取 GitHub 仓库最新 release 下载链接"""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    r = requests.get(url, proxies={"https": "http://127.0.0.1:8080"})
    data = r.json()
    
    for asset in data.get("assets", []):
        if asset["name"].endswith(".zip"):
            return asset["browser_download_url"]
    return None

# 使用示例
x64dbg_url = get_latest_release("x64dbg/x64dbg")
themidie_url = get_latest_release("VenTaz/Themidie")
scylla_url = get_latest_release("x64dbg/ScyllaHide")
```

## 参考

- `references/windows-debugger-setup.md` - Windows 调试器环境配置
- `references/windows-vm-pd-operations.md` - PD 虚拟机操作指南
- `references/windows-pe-analysis.md` - Windows PE 文件分析
