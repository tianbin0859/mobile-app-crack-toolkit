# Windows虚拟机PD操作指南

## 问题背景

在macOS上使用Parallels Desktop (PD)虚拟机运行Windows 11时，需要通过命令行在Windows虚拟机中执行操作。但直接通过 `prlctl exec` 传递复杂PowerShell命令会遇到严重的编码和转义问题。

## 已知问题

### 1. PowerShell特殊字符转义问题

**症状：**
- `$_.Name` 被错误解析为 `/Users/tianbin.Name`
- `$` 符号被当作环境变量展开
- `_` 下划线导致路径拼接错误

**示例：**
```bash
# ❌ 错误：$_.Name被转义
prlctl exec "Windows 11" powershell -Command "Get-Process | Where-Object {$_.ProcessName -match 'ldplayer'}"
# 输出：/Users/tianbin.ProcessName 无法识别...

# ❌ 错误：管道符号导致解析失败
prlctl exec "Windows 11" powershell -Command "Invoke-WebRequest -Uri 'http://...' -OutFile 'C:\...'"
# 输出：编码错误，命令无法执行
```

**原因：**
- `prlctl exec` 将命令字符串通过shell传递，特殊字符被macOS shell解释
- PowerShell的 `$` 符号与Unix shell的环境变量语法冲突
- 管道符号 `|` 在多层shell传递中被错误解析

### 2. 网络隔离问题

**症状：**
- macOS启动HTTP服务器，Windows虚拟机无法访问
- `Invoke-WebRequest` 超时
- 虚拟机与主机网络不通

**原因：**
- PD默认网络配置可能使用NAT而非桥接模式
- 虚拟机IP地址与主机不在同一网段
- 防火墙或安全策略阻止访问

### 3. 用户目录问题

**症状：**
- `echo %USERPROFILE%` 返回 `C:\WINDOWS\system32\config\systemprofile`
- 而不是预期的 `C:\Users\tianbin`

**原因：**
- `prlctl exec` 以系统服务账户运行，不是普通用户账户
- 需要显式指定用户路径

### 4. 下载文件被系统进程锁定（严重问题）

**症状：**
- 下载的 `.exe` 安装包无法执行，提示"文件被占用"
- `tasklist` 显示 `ldplayerservice.exe` 正在运行（即使雷电模拟器未完整安装）
- 文件被 `MsMpEng.exe`（Windows Defender）扫描锁定
- 重启虚拟机后文件锁定可能解除，但下载完成后又会被锁定

**原因：**
- 雷电模拟器安装包会启动后台服务 `ldplayerservice.exe`（即使安装未完成）
- Windows Defender 自动扫描下载目录中的可执行文件
- 系统进程锁定文件导致无法删除/执行

**影响：**
- 无法执行安装程序
- 无法删除被锁定文件
- 无法重新下载（文件名冲突）

**解决方案：**
```bash
# 1. 终止雷电服务进程
prlctl exec "Windows 11" cmd /c "taskkill /F /IM ldplayerservice.exe"

# 2. 关闭Windows Defender实时保护
prlctl exec "Windows 11" powershell -Command "Set-MpPreference -DisableRealtimeMonitoring 1"

# 3. 删除被锁定文件（可能需要重启虚拟机）
prlctl exec "Windows 11" cmd /c "del /F /Q C:\Users\tianbin\Downloads\LDPlayer.exe"

# 4. 如果仍无法删除，重启虚拟机后立刻删除
```

**预防措施：**
- 下载到 Desktop 而非 Downloads（Defender 对 Downloads 扫描更严格）
- 下载完成后立即执行安装，不要等待
- 关闭 Defender 实时保护后再下载

### 5. prlctl "Unable to open new session" 错误

**症状：**
- `prlctl exec "Windows 11" cmd /c "..."` 返回 `Unable to open new session`
- 虚拟机正在启动，但 prlctl 无法建立会话

**原因：**
- 虚拟机启动过程中，Parallels Tools 尚未完全加载
- 需要等待虚拟机完全启动

**解决方案：**
```bash
# 等待虚拟机完全启动（60秒通常足够）
sleep 60

# 然后重试
prlctl exec "Windows 11" cmd /c "echo ready"
```

### 6. prlctl exec 中文路径编码问题（严重）

**症状：**
- 通过 `prlctl exec` 传递包含中文路径的命令时，文件名显示为乱码或问号
- `cmd /c dir` 显示中文文件名为 `????.zip`
- 无法访问或操作中文命名的文件

**示例：**
```bash
# ❌ 错误：中文文件名显示为乱码
prlctl exec "Windows 11" cmd /c "dir C:\Mac\Home\Desktop"
# 输出：????.zip  (应为：W工具_破解版.zip)

# ❌ 错误：无法通过中文文件名访问文件
prlctl exec "Windows 11" cmd /c "copy C:\Mac\Home\Desktop\W工具_破解版.zip C:\test\"
# 输出：系统找不到指定的文件
```

**原因：**
- prlctl exec 通过 shell 传递命令，中文编码在多层传递中丢失
- Windows cmd 默认使用 GBK/GB2312 编码，而 macOS 使用 UTF-8
- 编码不一致导致中文文件名无法正确解析

**解决方案：**

**方案A：在macOS端重命名为英文文件名（推荐）**
```bash
# 在macOS端将中文文件重命名为英文
mv "W工具_破解版.zip" "w_tool_cracked.zip"

# 然后通过共享文件夹传递到Windows
# Windows中即可正常访问
prlctl exec "Windows 11" cmd /c "dir C:\Mac\Home\Desktop\w_tool_cracked.zip"
```

**方案B：使用Python subprocess直接调用（绕过shell编码问题）**
```python
import subprocess

# 使用Python直接调用prlctl，避免shell编码问题
result = subprocess.run(
    ["prlctl", "exec", "Windows 11", "cmd", "/c", "dir", "C:\\Mac\\Home\\Desktop"],
    capture_output=True,
    text=True,
    errors='replace'  # 关键：用?替换无法解码的字符
)
print(result.stdout)
```

**方案C：使用PowerShell替代cmd（编码支持更好）**
```bash
# PowerShell对UTF-8支持更好，但仍可能有问题
prlctl exec "Windows 11" powershell -Command "Get-ChildItem -Path 'C:\Mac\Home\Desktop'"
```

### 7. 共享文件夹实际路径发现

**症状：**
- 原以为共享文件夹路径是 `C:\Users\tianbin\Desktop\MacHome\`
- 实际找不到该路径，或路径不存在

**实际路径：**
```powershell
# 在Windows中查看实际挂载的共享文件夹路径
# 方式1：通过资源管理器地址栏输入
\\Mac\Home\Desktop

# 方式2：映射为网络驱动器后的路径
C:\Mac\Home\Desktop

# 方式3：通过PowerShell查看
Get-ChildItem "C:\Mac\Home\Desktop"
```

**关键发现：**
- PD共享文件夹实际挂载为 `C:\Mac\Home\`（不是 `C:\Users\tianbin\Desktop\MacHome\`）
- 这是通过网络驱动器映射实现的，不是本地文件夹
- 在cmd中可以直接使用 `C:\Mac\Home\Desktop\文件名`

**验证方法：**
```bash
# 在macOS中创建测试文件
touch ~/Desktop/test_shared_folder.txt

# 在Windows中检查是否能访问
prlctl exec "Windows 11" cmd /c "dir C:\Mac\Home\Desktop\test_shared_folder.txt"
# 如果显示文件存在，说明路径正确
```

### 8. prlctl exec 以 SYSTEM 账户执行

**症状：**
- `echo %USERPROFILE%` 返回 `C:\WINDOWS\system32\config\systemprofile`
- 而不是预期的 `C:\Users\tianbin`
- 环境变量与用户账户不同

**原因：**
- `prlctl exec` 以 SYSTEM 服务账户运行命令
- 不是以登录用户（tianbin）身份执行
- 因此用户目录、环境变量都不同

**影响：**
- 无法访问用户目录下的配置文件
- 下载的文件保存在 SYSTEM 目录，用户看不到
- 环境变量与用户账户不一致

**解决方案：**

**方案A：显式使用绝对路径**
```bash
# 不要依赖 %USERPROFILE% 或 %HOME%
# 使用绝对路径指向用户目录
prlctl exec "Windows 11" cmd /c "dir C:\Users\tianbin\Desktop"
```

**方案B：使用共享文件夹路径（不受用户账户影响）**
```bash
# 共享文件夹路径与当前用户无关
prlctl exec "Windows 11" cmd /c "dir C:\Mac\Home\Desktop"
```

**方案C：在Windows中切换到用户上下文执行**
```powershell
# 在Windows PowerShell中执行（以登录用户身份）
runas /user:tianbin "powershell -Command Get-ChildItem C:\Users\tianbin\Desktop"
```

### 9. tar 在 Windows 中解压中文文件名出错

**症状：**
- 使用 `tar xf` 解压包含中文文件名的压缩包时出错
- 错误：`tar: Error exit delayed from previous errors`
- 中文文件名显示为乱码，文件无法正确解压

**示例：**
```bash
# ❌ 错误：中文文件名解压失败
prlctl exec "Windows 11" cmd /c "tar xf C:\Mac\Home\Desktop\W工具.zip -C C:\test"
# 输出：tar: 无法创建符号链接 ... 错误
```

**原因：**
- Windows 版本的 tar 对中文文件名支持不佳
- 编码问题导致文件名解析错误

**解决方案：**

**方案A：在macOS端解压后传递（推荐）**
```bash
# 在macOS端解压
unzip "W工具.zip" -d w_tool_extracted/

# 重命名为英文
mv w_tool_extracted/"中文文件.txt" w_tool_extracted/"english_file.txt"

# 然后通过共享文件夹传递到Windows
```

**方案B：使用7z替代tar（对中文支持更好）**
```bash
# 在Windows中安装7z后使用
prlctl exec "Windows 11" cmd /c "7z x C:\Mac\Home\Desktop\W工具.zip -oC:\test"
```

**方案C：重命名为英文文件名后压缩**
```bash
# 在macOS端重命名所有文件为英文
for f in *.txt; do mv "$f" "file_$(date +%s).txt"; done

# 重新压缩
zip w_tool_renamed.zip *.txt

# 传递到Windows
```

### 10. 复杂命令分解为简单步骤

**原则：**
- 避免通过 `prlctl exec` 传递复杂的多步骤命令
- 每个 `prlctl exec` 调用只执行一个简单操作
- 在macOS端用Python脚本编排多个简单步骤

**示例：多步骤文件操作**
```python
import subprocess
import time

def vm_exec(cmd, timeout=30):
    """在VM中执行简单命令，处理编码问题"""
    result = subprocess.run(
        ["prlctl", "exec", "Windows 11"] + cmd.split(),
        capture_output=True,
        text=True,
        errors='replace',
        timeout=timeout
    )
    return result.stdout, result.stderr

# 步骤1：创建目录
vm_exec("cmd /c mkdir C:\\test")

# 步骤2：复制文件（英文文件名）
vm_exec("cmd /c copy C:\\Mac\\Home\\Desktop\\w_tool.zip C:\\test\\")

# 步骤3：解压
vm_exec("cmd /c tar xf C:\\test\\w_tool.zip -C C:\\test\\")

# 步骤4：检查文件
stdout, _ = vm_exec("cmd /c dir C:\\test\\")
print(stdout)
```

**优势：**
- 每个步骤独立，错误容易定位
- 避免长命令的编码和转义问题
- 可以在步骤间添加延迟或检查
- Python 处理逻辑更清晰

### 11. PyInstaller 程序测试方法

**场景：**
- 破解后的 PyInstaller 程序需要在 Windows 虚拟机中测试
- 程序是 GUI 应用，无法直接查看运行结果

**测试方法：**

**方法1：检查 launcher.log（推荐）**
```bash
# 运行程序后检查日志文件
prlctl exec "Windows 11" cmd /c "type C:\\test\\launcher.log"

# 日志内容示例：
# 2026-06-13 10:30:00 - Launcher started
# 2026-06-13 10:30:01 - Loading modules...
# 2026-06-13 10:30:02 - Ready
```

**方法2：检查进程是否存在**
```bash
# 检查程序进程是否启动
prlctl exec "Windows 11" cmd /c "tasklist | findstr launcher"
```

**方法3：检查输出文件**
```bash
# 检查程序是否生成了预期文件
prlctl exec "Windows 11" cmd /c "dir C:\\test\\output"
```

**关键发现：**
- 不需要实际运行 GUI 程序来验证破解是否成功
- 检查 launcher.log 即可确认程序是否正常启动
- 日志中的时间戳和状态信息可以证明程序已执行

## 解决方案

### 方案1：使用PD共享文件夹（推荐）

PD虚拟机默认会挂载macOS的Home目录到Windows中。

**步骤：**
1. 在macOS中准备文件（脚本、安装包等）
2. 通过PD共享文件夹传递到Windows
3. 在Windows中直接访问

**Windows中的共享文件夹路径：**
```powershell
# 通常挂载在
C:\Users\tianbin\Desktop\MacHome\  # 或类似路径
# 或
Z:\  # 如果配置了网络驱动器
```

**检查共享文件夹：**
```powershell
# 在Windows中查看挂载的共享文件夹
Get-PSDrive
Get-ChildItem "C:\Users\tianbin\Desktop"  # 查看桌面文件
```

### 方案2：使用简单cmd命令（避免PowerShell复杂语法）

**原则：**
- 使用 `cmd /c` 而非 `powershell -Command`
- 避免特殊字符：`|`, `>`, `<`, `$`, `_`
- 使用简单命令，分步执行

**示例：**
```bash
# ✅ 简单命令可以工作
prlctl exec "Windows 11" cmd /c "echo %OS%"
prlctl exec "Windows 11" cmd /c "tasklist"
prlctl exec "Windows 11" cmd /c "dir /b C:\Users\tianbin"

# ✅ 检查进程（简单过滤）
prlctl exec "Windows 11" cmd /c "tasklist | findstr ldplayer"

# ❌ 避免复杂PowerShell管道
prlctl exec "Windows 11" powershell -Command "Get-Process | Where-Object ..."
```

### 方案3：在Windows中直接下载（最可靠）

**步骤：**
1. 在macOS上准备PowerShell脚本
2. 将脚本内容通过简单方式传递到Windows（如共享文件夹、剪贴板）
3. 在Windows中打开PowerShell，粘贴执行

**示例脚本（在Windows中执行）：**
```powershell
# 在Windows PowerShell中直接执行
$temp = "$env:TEMP\LDSetup"
New-Item -ItemType Directory -Force -Path $temp | Out-Null
Invoke-WebRequest -Uri "https://www.ldplayer.tw/download" -OutFile "$temp\ldplayer.exe"
Start-Process -FilePath "$temp\ldplayer.exe" -Wait
```

### 方案4：使用prlctl copy命令（文件传递）

**检查prlctl是否支持copy：**
```bash
prlctl --help | grep -i copy
```

**如果支持：**
```bash
# 从macOS复制到Windows虚拟机
prlctl copy "Windows 11" /Users/tianbin/ldplayer_auto_install.ps1 C:\Users\tianbin\Desktop\

# 从Windows虚拟机复制到macOS
prlctl copy "Windows 11" C:\Users\tianbin\Desktop\report.txt /Users/tianbin/
```

## 最佳实践

### 1. 环境检查清单

在尝试自动化操作前，先确认：
```bash
# 检查虚拟机状态
prlctl list --all

# 检查Windows是否运行
prlctl exec "Windows 11" cmd /c "echo %OS%"

# 检查用户目录
prlctl exec "Windows 11" cmd /c "dir /b C:\Users\tianbin"

# 检查共享文件夹
prlctl exec "Windows 11" cmd /c "dir /b C:\Users\tianbin\Desktop"
```

### 2. 脚本传递流程

```
macOS准备脚本
    ↓
保存到共享文件夹或桌面
    ↓
Windows通过资源管理器访问
    ↓
右键 → 使用PowerShell运行
    ↓
执行完成
```

### 3. 避免的操作

| 避免 | 原因 | 替代方案 |
|------|------|----------|
| 复杂PowerShell管道 | 编码问题 | 简单cmd命令 |
| 通过prlctl传递$变量 | 被shell解释 | 使用固定路径 |
| 多层嵌套引号 | 解析错误 | 使用临时文件 |
| 依赖网络互通 | 可能隔离 | 使用共享文件夹 |

## 实战：雷电模拟器自动下载安装

### 背景

雷电模拟器官网有反爬虫保护，直接下载会返回403 Access Denied。需要使用第三方镜像站获取直链。

### 下载直链获取方法

**方法1：通过阿荣福利味网站获取直链**
1. 访问 `https://www.azofreeware.com/2018/06/ldplayer.html`
2. 找到子页面 `https://www.azofreeware.com/p/ldplayer.html`
3. 解析页面获取实际下载直链：`https://static.ldrescdn.com/download/package/LDPlayer_9.5.15.1.exe`

**方法2：通过多开鸭网站获取版本信息**
1. 访问 `https://www.duokaiya.com/ldversion.html`
2. 页面为JavaScript渲染，需用浏览器提取版本号
3. 构造下载直链

### 自动下载安装流程（推荐方案）

```powershell
# 在Windows PowerShell中执行（避免prlctl编码问题）

# 1. 关闭Defender实时保护（防止下载后文件被锁定）
Set-MpPreference -DisableRealtimeMonitoring 1

# 2. 下载到Desktop（避免Downloads目录Defender扫描）
$url = "https://static.ldrescdn.com/download/package/LDPlayer_9.5.15.1.exe"
$out = "C:\Users\tianbin\Desktop\LDPlayer.exe"

# 3. 使用后台作业避免超时（大文件下载可能需要10-15分钟）
$job = Start-Job -ScriptBlock {
    param($url, $out)
    Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing
} -ArgumentList $url, $out

# 4. 监控下载进度（每30秒检查一次文件大小）
while ($job.State -eq 'Running') {
    if (Test-Path $out) {
        $size = (Get-Item $out).Length
        Write-Host "下载进度: $size bytes"
    }
    Start-Sleep -Seconds 30
}

# 5. 等待完成
$job | Wait-Job
$job | Receive-Job

# 6. 验证文件大小（完整版约54MB）
$fileSize = (Get-Item $out).Length
if ($fileSize -lt 50000000) {
    Write-Host "下载不完整，文件大小: $fileSize"
    exit 1
}

# 7. 立即执行安装（防止被系统进程锁定）
Start-Process -FilePath $out -ArgumentList "/S" -Wait

# 8. 清理安装包
Remove-Item $out -Force

Write-Host "雷电模拟器安装完成!"
```

### 关键注意事项

| 问题 | 解决方案 | 优先级 |
|------|----------|--------|
| 官网403反爬虫 | 使用第三方镜像站直链 | 必须 |
| 前台下载超时 | 使用Start-Job后台作业 | 必须 |
| 文件被Defender锁定 | 关闭实时保护 + 下载到Desktop | 必须 |
| 文件被ldplayerservice锁定 | 下载完成后立即安装 | 必须 |
| prlctl编码问题 | 在Windows内直接执行PowerShell | 必须 |
| 下载进度未知 | 定期dir检查文件大小变化 | 推荐 |
| 安装包残留 | 安装完成后立即删除 | 推荐 |

### 进度监控方法

```bash
# 从macOS监控Windows下载进度（每30秒执行一次）
prlctl exec "Windows 11" cmd /c "dir C:\Users\tianbin\Desktop\LDPlayer.exe"

# 输出示例：
# 2026/06/13  10:30    16,491,288 LDPlayer.exe
# 文件大小持续增长表示下载进行中
```

## 配置Root权限（安装后）

1. 启动雷电模拟器
2. 点击右侧工具栏「设置」
3. 选择「其他设置」
4. 找到「Root权限」选项
5. 选择「开启」
6. 重启模拟器

## 安装Frida-server（Root后）

```bash
# 在Windows中打开CMD，进入雷电模拟器ADB目录
cd C:\LDPlayer\adb

# 连接模拟器
adb connect 127.0.0.1:5555

# 推送Frida-server
adb push frida-server-android-x86_64 /data/local/tmp/frida-server

# 设置权限并启动
adb shell chmod 755 /data/local/tmp/frida-server
adb shell /data/local/tmp/frida-server &

# 验证
frida-ps -U
```

## 故障排查

| 问题 | 检查 | 解决 |
|------|------|------|
| prlctl命令无响应 | 虚拟机是否运行 | `prlctl list --all` |
| 编码错误 | 避免特殊字符 | 使用简单cmd命令 |
| 网络不通 | 检查IP配置 | 使用共享文件夹 |
| 权限不足 | 是否系统账户 | 显式指定用户路径 |
| 文件找不到 | 路径是否正确 | 使用绝对路径 |
| 文件被锁定 | 检查占用进程 | `taskkill /F /IM` |
| 下载403 | 官网反爬虫 | 使用镜像站直链 |
| 下载超时 | 文件太大 | 使用后台作业 |
| 安装失败 | 文件不完整 | 验证文件大小 |
| prlctl无法连接 | 虚拟机启动中 | 等待60秒后重试 |

## 参考

- Parallels Desktop文档: https://www.parallels.com/products/desktop/docs/
- prlctl命令参考: `prlctl --help`
- 雷电模拟器官网: https://www.ldplayer.tw/
- 阿荣福利味镜像站: https://www.azofreeware.com/2018/06/ldplayer.html
