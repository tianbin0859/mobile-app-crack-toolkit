# Windows虚拟机工具链自动安装指南

## 概述

在Parallels Desktop Windows 11虚拟机中，自动安装Android逆向工程所需的完整工具链，无需手动干预。

## 自动安装脚本

### PowerShell一键安装脚本

```powershell
# windows_toolchain_setup.ps1
# 在Windows 11虚拟机中执行，自动安装完整工具链

param(
    [string]$InstallDir = "C:\Tools",
    [switch]$SkipDefender = $false
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "Continue"

# 创建安装目录
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$logFile = "$InstallDir\install.log"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $Message" | Tee-Object -FilePath $logFile -Append
}

Write-Log "=== Windows工具链自动安装开始 ==="

# 1. 关闭Windows Defender实时保护（防止工具被误删）
if (-not $SkipDefender) {
    Write-Log "关闭Windows Defender实时保护..."
    try {
        Set-MpPreference -DisableRealtimeMonitoring $true
        Set-MpPreference -DisableArchiveScanning $true
        Set-MpPreference -DisableBehaviorMonitoring $true
        Write-Log "Defender已关闭"
    } catch {
        Write-Log "警告: 无法关闭Defender，可能需要手动操作"
    }
}

# 2. 安装Chocolatey包管理器
Write-Log "安装Chocolatey..."
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    Write-Log "Chocolatey安装完成"
} else {
    Write-Log "Chocolatey已存在"
}

# 3. 安装Python 3.11
Write-Log "安装Python 3.11..."
choco install python311 -y --force
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
Write-Log "Python安装完成"

# 4. 安装Git
Write-Log "安装Git..."
choco install git -y
Write-Log "Git安装完成"

# 5. 安装ADB工具
Write-Log "安装ADB (Android Debug Bridge)..."
choco install adb -y
Write-Log "ADB安装完成"

# 6. 安装Java (OpenJDK 17)
Write-Log "安装Java OpenJDK 17..."
choco install openjdk17 -y
$env:JAVA_HOME = "C:\Program Files\OpenJDK\jdk-17"
[Environment]::SetEnvironmentVariable("JAVA_HOME", $env:JAVA_HOME, "Machine")
Write-Log "Java安装完成"

# 7. 安装apktool
Write-Log "安装apktool..."
$apktoolDir = "$InstallDir\apktool"
New-Item -ItemType Directory -Force -Path $apktoolDir | Out-Null
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/windows/apktool.bat" -OutFile "$apktoolDir\apktool.bat"
Invoke-WebRequest -Uri "https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.9.3.jar" -OutFile "$apktoolDir\apktool.jar"
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$apktoolDir", "Machine")
Write-Log "apktool安装完成"

# 8. 安装Frida工具链
Write-Log "安装Frida..."
python -m pip install frida frida-tools
Write-Log "Frida安装完成"

# 9. 下载Frida-server (Android x86_64，用于模拟器)
Write-Log "下载Frida-server..."
$fridaDir = "$InstallDir\frida"
New-Item -ItemType Directory -Force -Path $fridaDir | Out-Null
$fridaVersion = (python -c "import frida; print(frida.__version__)")
Invoke-WebRequest -Uri "https://github.com/frida/frida/releases/download/$fridaVersion/frida-server-$fridaVersion-android-x86_64.xz" -OutFile "$fridaDir\frida-server-android-x86_64.xz"
# 解压.xz文件
if (Get-Command 7z -ErrorAction SilentlyContinue) {
    7z x "$fridaDir\frida-server-android-x86_64.xz" -o"$fridaDir\" -y
} else {
    # 使用Python解压
    python -c "import lzma; open('$fridaDir\frida-server-android-x86_64', 'wb').write(lzma.open('$fridaDir\frida-server-android-x86_64.xz', 'rb').read())"
}
Write-Log "Frida-server下载完成"

# 10. 安装Jadx (DEX反编译)
Write-Log "安装Jadx..."
$jadxDir = "$InstallDir\jadx"
New-Item -ItemType Directory -Force -Path $jadxDir | Out-Null
Invoke-WebRequest -Uri "https://github.com/skylot/jadx/releases/download/v1.4.7/jadx-1.4.7.zip" -OutFile "$jadxDir\jadx.zip"
Expand-Archive -Path "$jadxDir\jadx.zip" -DestinationPath $jadxDir -Force
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$jadxDir\bin", "Machine")
Write-Log "Jadx安装完成"

# 11. 安装 objection (Frida辅助工具)
Write-Log "安装objection..."
python -m pip install objection
Write-Log "objection安装完成"

# 12. 安装 mitmproxy
Write-Log "安装mitmproxy..."
python -m pip install mitmproxy
Write-Log "mitmproxy安装完成"

# 13. 安装其他Python工具
Write-Log "安装其他Python工具..."
python -m pip install pyinstxtractor uncompyle6 pyarmor pyaxmlparser
Write-Log "Python工具安装完成"

# 14. 创建工具链验证脚本
Write-Log "创建验证脚本..."
$verifyScript = @"
# 工具链验证脚本
`$tools = @{
    "python" = "python --version"
    "adb" = "adb version"
    "java" = "java -version"
    "git" = "git --version"
    "frida" = "frida --version"
    "apktool" = "apktool --version"
    "jadx" = "jadx --version"
    "objection" = "objection --version"
}

foreach (`$tool in `$tools.Keys) {
    try {
        Invoke-Expression `$tools[`$tool] | Out-Null
        Write-Host "`u2705 `$tool: OK"
    } catch {
        Write-Host "`u274c `$tool: FAILED"
    }
}
"@
$verifyScript | Out-File -FilePath "$InstallDir\verify.ps1" -Encoding UTF8

Write-Log "=== 安装完成 ==="
Write-Log "工具链安装目录: $InstallDir"
Write-Log "验证脚本: $InstallDir\verify.ps1"
Write-Log ""
Write-Log "已安装工具:"
Write-Log "- Python 3.11 + pip"
Write-Log "- Git"
Write-Log "- ADB (Android Debug Bridge)"
Write-Log "- Java OpenJDK 17"
Write-Log "- apktool"
Write-Log "- Frida + frida-tools"
Write-Log "- Frida-server (Android x86_64)"
Write-Log "- Jadx (DEX反编译)"
Write-Log "- objection"
Write-Log "- mitmproxy"
Write-Log "- pyinstxtractor / uncompyle6 / pyarmor"

# 显示完成信息
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "Windows工具链自动安装完成!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "安装目录: $InstallDir"
Write-Host "日志文件: $logFile"
Write-Host ""
Write-Host "验证安装:"
Write-Host "  powershell -ExecutionPolicy Bypass -File $InstallDir\verify.ps1"
Write-Host ""
Write-Host "注意: Windows Defender已关闭，生产环境请手动配置例外规则"
```

## 执行方式

### 方式1：在Windows中直接执行（推荐）

```powershell
# 在Windows PowerShell中执行
powershell -ExecutionPolicy Bypass -File C:\Users\tianbin\Desktop\windows_toolchain_setup.ps1
```

### 方式2：通过PD共享文件夹传递后执行

```bash
# 在macOS中准备脚本
cat > /Users/tianbin/windows_toolchain_setup.ps1 << 'EOF'
# ... 脚本内容 ...
EOF

# 通过PD共享文件夹传递到Windows
# Windows路径: C:\Users\tianbin\Desktop\MacHome\windows_toolchain_setup.ps1

# 在Windows中执行
prlctl exec "Windows 11" powershell -ExecutionPolicy Bypass -File "C:\Users\tianbin\Desktop\MacHome\windows_toolchain_setup.ps1"
```

### 方式3：远程下载执行

```powershell
# 在Windows中下载并执行
Invoke-WebRequest -Uri "https://your-server.com/windows_toolchain_setup.ps1" -OutFile "$env:TEMP\setup.ps1"
powershell -ExecutionPolicy Bypass -File "$env:TEMP\setup.ps1"
```

## 工具链验证

安装完成后，运行验证脚本：

```powershell
# 在Windows中执行
powershell -ExecutionPolicy Bypass -File C:\Tools\verify.ps1
```

**预期输出：**
```
✅ python: OK
✅ adb: OK
✅ java: OK
✅ git: OK
✅ frida: OK
✅ apktool: OK
✅ jadx: OK
✅ objection: OK
```

## 环境变量配置

安装脚本会自动配置以下环境变量：

| 变量 | 值 | 说明 |
|------|-----|------|
| JAVA_HOME | C:\Program Files\OpenJDK\jdk-17 | Java安装路径 |
| Path | 追加: C:\Tools\apktool;C:\Tools\jadx\bin | 工具可执行文件路径 |

## 工具链清单

| 工具 | 版本 | 用途 | 安装方式 |
|------|------|------|----------|
| Python | 3.11 | 脚本执行 | Chocolatey |
| Git | 最新 | 版本控制 | Chocolatey |
| ADB | 最新 | Android调试 | Chocolatey |
| Java | OpenJDK 17 | 反编译/打包 | Chocolatey |
| apktool | 2.9.3 | APK反编译/重打包 | 手动下载 |
| Frida | 最新 | 动态注入 | pip |
| Frida-server | 匹配版本 | Android服务端 | GitHub Release |
| Jadx | 1.4.7 | DEX反编译 | GitHub Release |
| objection | 最新 | Frida辅助 | pip |
| mitmproxy | 最新 | HTTP代理 | pip |
| pyinstxtractor | 最新 | PyInstaller解包 | pip |
| uncompyle6 | 最新 | pyc反编译 | pip |
| pyarmor | 最新 | PyArmor分析 | pip |

## 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| Chocolatey安装失败 | 执行策略限制 | `Set-ExecutionPolicy Bypass` |
| 下载超时 | 网络问题 | 使用镜像源或手动下载 |
| pip安装失败 | 权限不足 | 使用 `--user` 或管理员权限 |
| 环境变量未生效 | 需要重启终端 | 重新打开PowerShell |
| Frida-server版本不匹配 | 与pip安装的frida版本不一致 | 检查版本并重新下载 |
| apktool无法运行 | Java未安装 | 检查JAVA_HOME |
| 工具命令未找到 | Path未配置 | 手动添加或重启 |

## 与macOS主机的协同

### 文件共享路径

| 位置 | macOS路径 | Windows路径 |
|------|-----------|-------------|
| 桌面 | `/Users/tianbin/Desktop` | `C:\Users\tianbin\Desktop\MacHome` |
| 文档 | `/Users/tianbin/Documents` | `C:\Users\tianbin\Documents\MacHome` |
| 下载 | `/Users/tianbin/Downloads` | `C:\Users\tianbin\Downloads\MacHome` |

### 双向文件传递

```bash
# macOS → Windows: 复制到macOS桌面，Windows通过共享文件夹访问
cp /Users/tianbin/target.apk /Users/tianbin/Desktop/

# Windows → macOS: 复制到Windows桌面，macOS通过共享文件夹访问
# 在Windows中: Copy-Item C:\target.apk C:\Users\tianbin\Desktop\MacHome\
```

## 更新工具链

```powershell
# 更新所有Chocolatey包
choco upgrade all -y

# 更新Python包
python -m pip install --upgrade frida frida-tools objection mitmproxy

# 更新Frida-server
$fridaVersion = (python -c "import frida; print(frida.__version__)")
Invoke-WebRequest -Uri "https://github.com/frida/frida/releases/download/$fridaVersion/frida-server-$fridaVersion-android-x86_64.xz" -OutFile "C:\Tools\frida\frida-server-android-x86_64.xz"
```
