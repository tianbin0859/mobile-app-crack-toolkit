# Windows调试器环境配置指南（x64dbg + Themidie + ScyllaHide）

## 场景
在macOS主机通过Parallels Desktop虚拟机运行Windows 11，配置完整的逆向工程调试环境，用于分析加壳保护的Windows程序（如Themida/SecureEngine/HAP SDK三重保护）。

## 环境架构

```
macOS主机
├── PD虚拟机 (Windows 11)
│   ├── x64dbg（主调试器）
│   ├── Themidie插件（Themida脱壳）
│   ├── ScyllaHide插件（反调试绕过）
│   └── 目标程序 (C:\Crack\target.exe)
└── 共享文件夹 (C:\Mac\Home\Desktop)
```

## 工具链安装

### 1. x64dbg 安装

**官方下载（可能失效）：**
- 官网：`https://x64dbg.com/` → 下载链接可能失效

**GitHub API动态获取最新Release（推荐）：**
```python
import requests

# 获取最新release信息
resp = requests.get('https://api.github.com/repos/x64dbg/x64dbg/releases/latest')
data = resp.json()

# 提取下载链接
for asset in data['assets']:
    if 'snapshot' in asset['name'] and asset['name'].endswith('.zip'):
        download_url = asset['browser_download_url']
        print(f"下载链接: {download_url}")
        break
```

**安装步骤：**
1. 下载zip包到共享文件夹
2. 在Windows中解压到 `C:\tools\x64dbg\`
3. 运行 `x64dbg.exe` 或 `x32dbg.exe`

### 2. Themidie插件安装（Themida脱壳）

**来源：** GitHub `mrexodia/Themidie`

**安装步骤：**
1. 下载Themidie插件（.dp32或.dp64文件）
2. 复制到x64dbg插件目录：
   ```
   C:\tools\x64dbg\release\x64\plugins\Themidie.dp64
   C:\tools\x64dbg\release\x32\plugins\Themidie.dp32
   ```
3. 重启x64dbg

**使用：**
- 打开目标程序前，在Plugins菜单启用Themidie
- 自动处理Themida保护壳的入口点混淆

### 3. ScyllaHide插件安装（反调试绕过）

**来源：** GitHub `x64dbg/ScyllaHide`

**安装步骤：**
1. 下载ScyllaHide插件
2. 复制到x64dbg插件目录：
   ```
   C:\tools\x64dbg\release\x64\plugins\ScyllaHideX64DBG.dp64
   C:\tools\x64dbg\release\x32\plugins\ScyllaHideX32DBG.dp32
   ```
3. 重启x64dbg

**使用：**
- 打开目标程序前，在Plugins菜单启用ScyllaHide
- 自动绕过常见的反调试检测（IsDebuggerPresent, CheckRemoteDebuggerPresent, NtQueryInformationProcess等）

## PD虚拟机操作要点

### 文件传递

**通过共享文件夹：**
```
macOS: ~/Desktop/target.exe
Windows: C:\Mac\Home\Desktop\target.exe
```

**复制到工作目录：**
```powershell
# 在Windows中执行
copy C:\Mac\Home\Desktop\target.exe C:\Crack\
```

### prlctl exec 注意事项

**避免复杂PowerShell命令：**
- ❌ 不要传递 `Where-Object {$_.Name -match ...}`
- ❌ 不要传递管道符号 `|`
- ✅ 使用简单cmd命令

**示例：**
```bash
# ✅ 检查文件存在
prlctl exec "Windows 11" cmd /c "dir C:\Crack\target.exe"

# ✅ 创建目录
prlctl exec "Windows 11" cmd /c "mkdir C:\Crack"

# ❌ 避免复杂PowerShell
prlctl exec "Windows 11" powershell -Command "Get-Process | Where-Object ..."
```

## 调试环境配置流程

### 1. 创建破解工作目录
```powershell
mkdir C:\Crack
mkdir C:\Crack\dump
mkdir C:\Crack\scripts
```

### 2. 复制目标程序
```powershell
copy C:\Mac\Home\Desktop\target.exe C:\Crack\
```

### 3. 启动x64dbg
```powershell
C:\tools\x64dbg\release\x64\x64dbg.exe C:\Crack\target.exe
```

### 4. 启用插件
- 菜单: Plugins → Themidie → Enable
- 菜单: Plugins → ScyllaHide → Options → 勾选所有反调试绕过

### 5. 开始调试
- F9 运行到入口点
- F8 单步执行
- F7 步入函数

## 常见问题

### 1. x64dbg下载链接失效
**解决：** 使用GitHub API动态获取最新release（见上文代码）

### 2. 插件不加载
**检查：**
- 插件文件是否放在正确的plugins目录
- 是否使用了匹配的架构（x64程序用dp64插件，x32用dp32）
- x64dbg版本是否兼容

### 3. Themida保护无法绕过
**解决：**
- 确保Themidie插件已启用
- 尝试手动设置断点在OEP（原始入口点）
- 使用ScyllaDump在OEP处dump内存

### 4. 反调试检测绕过失败
**解决：**
- 检查ScyllaHide选项是否全部启用
- 手动Patch IsDebuggerPresent返回0
- 使用硬件断点替代软件断点

## 工具链版本参考

| 工具 | 版本 | 用途 |
|------|------|------|
| x64dbg | 2024-06-14 | 主调试器 |
| Themidie | 最新 | Themida脱壳 |
| ScyllaHide | 最新 | 反调试绕过 |
| Scylla | 最新 | 导入表修复 |

## 参考

- x64dbg GitHub: https://github.com/x64dbg/x64dbg
- Themidie: https://github.com/mrexodia/Themidie
- ScyllaHide: https://github.com/x64dbg/ScyllaHide
- Themida保护分析: https://github.com/ThunderCls/xAnalyzer
