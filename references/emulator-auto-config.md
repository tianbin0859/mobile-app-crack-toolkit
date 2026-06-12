# 模拟器自动配置指南

## 概述

雷电模拟器安装完成后，自动完成Root权限开启、Frida-server部署、ADB连接配置，实现开箱即用的Android逆向环境。

## 自动配置脚本

### PowerShell自动配置脚本

```powershell
# emulator_auto_config.ps1
# 雷电模拟器安装后自动配置Root + Frida环境

param(
    [string]$LDPlayerPath = "C:\LDPlayer\LDPlayer9",
    [string]$FridaServerPath = "C:\Tools\frida\frida-server-android-x86_64",
    [switch]$AutoStart = $false
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN"  { "Yellow" }
        "SUCCESS" { "Green" }
        default { "White" }
    }
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

Write-Log "=== 雷电模拟器自动配置开始 ==="

# 1. 检查雷电模拟器安装
Write-Log "检查雷电模拟器安装..."
if (-not (Test-Path $LDPlayerPath)) {
    # 尝试其他常见路径
    $possiblePaths = @(
        "C:\LDPlayer\LDPlayer9",
        "C:\LDPlayer\LDPlayer4",
        "C:\Program Files\LDPlayer\LDPlayer9",
        "D:\LDPlayer\LDPlayer9"
    )
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $LDPlayerPath = $path
            Write-Log "找到雷电模拟器: $path" "SUCCESS"
            break
        }
    }
}

if (-not (Test-Path $LDPlayerPath)) {
    Write-Log "雷电模拟器未安装，请先安装" "ERROR"
    exit 1
}

# 2. 检查ADB工具
Write-Log "检查ADB工具..."
$adbPath = "$LDPlayerPath\adb.exe"
if (-not (Test-Path $adbPath)) {
    # 尝试系统ADB
    $adbPath = (Get-Command adb -ErrorAction SilentlyContinue).Source
    if (-not $adbPath) {
        Write-Log "ADB未找到，请先安装Android SDK或雷电模拟器自带ADB" "ERROR"
        exit 1
    }
}
Write-Log "ADB路径: $adbPath" "SUCCESS"

# 3. 启动雷电模拟器（如果未运行）
Write-Log "检查模拟器运行状态..."
$ldProcess = Get-Process -Name "dnplayer" -ErrorAction SilentlyContinue
if (-not $ldProcess) {
    if ($AutoStart) {
        Write-Log "启动雷电模拟器..."
        Start-Process -FilePath "$LDPlayerPath\dnplayer.exe"
        Write-Log "等待模拟器启动 (60秒)..."
        Start-Sleep -Seconds 60
    } else {
        Write-Log "模拟器未运行，使用 -AutoStart 参数自动启动" "WARN"
        exit 1
    }
} else {
    Write-Log "模拟器已在运行" "SUCCESS"
}

# 4. 连接ADB
Write-Log "连接ADB..."
& $adbPath connect 127.0.0.1:5555 | Out-Null
$devices = & $adbPath devices
if ($devices -match "127.0.0.1:5555") {
    Write-Log "ADB连接成功" "SUCCESS"
} else {
    Write-Log "ADB连接失败，尝试其他端口..." "WARN"
    # 雷电模拟器可能使用其他端口
    $ports = @(5555, 5556, 5557, 5558, 5559)
    foreach ($port in $ports) {
        & $adbPath connect "127.0.0.1:$port" | Out-Null
        $devices = & $adbPath devices
        if ($devices -match "127.0.0.1:$port") {
            Write-Log "ADB连接成功 (端口: $port)" "SUCCESS"
            break
        }
    }
}

# 5. 检查Root权限
Write-Log "检查Root权限..."
$rootCheck = & $adbPath shell "su -c 'id'" 2>&1
if ($rootCheck -match "uid=0") {
    Write-Log "Root权限已开启" "SUCCESS"
} else {
    Write-Log "Root权限未开启，需要手动开启" "WARN"
    Write-Log "步骤: 模拟器设置 → 其他设置 → Root权限 → 开启 → 重启" "WARN"
    # 尝试自动修改配置文件开启Root（部分版本支持）
    $configPath = "$LDPlayerPath\vms\config\leidian*.config"
    $configFiles = Get-ChildItem -Path $configPath -ErrorAction SilentlyContinue
    foreach ($config in $configFiles) {
        Write-Log "尝试修改配置文件: $($config.FullName)"
        $content = Get-Content $config.FullName -Raw
        if ($content -match "root.mode=0") {
            $content = $content -replace "root.mode=0", "root.mode=1"
            Set-Content -Path $config.FullName -Value $content -NoNewline
            Write-Log "配置文件已修改，请重启模拟器" "SUCCESS"
        }
    }
}

# 6. 推送Frida-server
Write-Log "部署Frida-server..."
if (-not (Test-Path $FridaServerPath)) {
    Write-Log "Frida-server文件未找到: $FridaServerPath" "ERROR"
    Write-Log "请先下载Frida-server到该路径" "ERROR"
    exit 1
}

# 检查是否已存在
$existingFrida = & $adbPath shell "ls /data/local/tmp/frida-server" 2>&1
if ($existingFrida -match "No such file") {
    Write-Log "推送Frida-server到模拟器..."
    & $adbPath push $FridaServerPath /data/local/tmp/frida-server
    & $adbPath shell "chmod 755 /data/local/tmp/frida-server"
    Write-Log "Frida-server推送完成" "SUCCESS"
} else {
    Write-Log "Frida-server已存在" "SUCCESS"
}

# 7. 启动Frida-server
Write-Log "启动Frida-server..."
# 检查是否已在运行
$fridaRunning = & $adbPath shell "ps -A | grep frida-server" 2>&1
if ($fridaRunning -match "frida-server") {
    Write-Log "Frida-server已在运行" "SUCCESS"
} else {
    # 后台启动Frida-server
    & $adbPath shell "/data/local/tmp/frida-server &"
    Start-Sleep -Seconds 2
    $fridaRunning = & $adbPath shell "ps -A | grep frida-server" 2>&1
    if ($fridaRunning -match "frida-server") {
        Write-Log "Frida-server启动成功" "SUCCESS"
    } else {
        Write-Log "Frida-server启动失败" "ERROR"
    }
}

# 8. 验证Frida连接
Write-Log "验证Frida连接..."
$fridaTest = frida-ps -U 2>&1 | Select-Object -First 5
if ($fridaTest -match "PID") {
    Write-Log "Frida连接成功，可以列出进程" "SUCCESS"
} else {
    Write-Log "Frida连接失败，请检查版本匹配" "WARN"
}

# 9. 配置模拟器优化（可选）
Write-Log "配置模拟器优化..."
# 设置ADB调试模式
& $adbPath shell "setprop persist.sys.usb.config mtp,adb"
# 关闭模拟器更新检查（防止自动更新导致配置丢失）
& $adbPath shell "settings put global ldplayer_auto_update 0"

Write-Log "=== 雷电模拟器自动配置完成 ===" "SUCCESS"
Write-Log ""
Write-Log "配置摘要:"
Write-Log "- 模拟器路径: $LDPlayerPath"
Write-Log "- ADB连接: 127.0.0.1:5555"
Write-Log "- Root权限: 已开启"
Write-Log "- Frida-server: /data/local/tmp/frida-server"
Write-Log "- Frida版本: $(frida --version)"
Write-Log ""
Write-Log "使用方法:"
Write-Log "  frida-ps -U                    # 列出设备进程"
Write-Log "  frida -U -n com.target.app     # 附加目标APP"
Write-Log "  objection -g com.target.app explore  # 交互式探索"
```

## 执行方式

### 方式1：安装后自动执行

```powershell
# 雷电模拟器安装完成后，立即执行配置
powershell -ExecutionPolicy Bypass -File C:\Tools\emulator_auto_config.ps1 -AutoStart
```

### 方式2：与工具链安装一起执行

```powershell
# 先安装工具链
powershell -ExecutionPolicy Bypass -File C:\Tools\windows_toolchain_setup.ps1

# 再配置模拟器
powershell -ExecutionPolicy Bypass -File C:\Tools\emulator_auto_config.ps1 -AutoStart
```

## 手动配置步骤（备用）

如果自动配置失败，按以下步骤手动配置：

### 1. 开启Root权限

1. 启动雷电模拟器
2. 点击右侧工具栏「设置」（齿轮图标）
3. 选择「其他设置」
4. 找到「Root权限」选项
5. 选择「开启」
6. 点击「保存设置」
7. 重启模拟器

### 2. 连接ADB

```powershell
# 进入雷电模拟器ADB目录
cd C:\LDPlayer\LDPlayer9

# 连接模拟器
.\adb.exe connect 127.0.0.1:5555

# 验证连接
.\adb.exe devices
# 输出: 127.0.0.1:5555 device
```

### 3. 推送Frida-server

```powershell
# 推送Frida-server到模拟器
.\adb.exe push C:\Tools\frida\frida-server-android-x86_64 /data/local/tmp/frida-server

# 设置执行权限
.\adb.exe shell chmod 755 /data/local/tmp/frida-server

# 启动Frida-server
.\adb.exe shell "/data/local/tmp/frida-server &"
```

### 4. 验证Frida

```powershell
# 列出设备进程
frida-ps -U

# 附加目标APP
frida -U -n com.target.app -l hook_script.js
```

## 模拟器配置优化

### 性能优化

```powershell
# 在雷电模拟器设置中调整:
# 1. CPU: 设置为物理核心数的一半（如4核设2核）
# 2. 内存: 设置为物理内存的1/4（如16GB设4GB）
# 3. 分辨率: 1280x720 或 1920x1080
# 4. DPI: 240 或 320
# 5. 帧率: 60fps
# 6. 磁盘清理: 定期清理模拟器缓存
```

### 网络优化

```powershell
# 设置DNS（加速国内访问）
adb shell "setprop net.dns1 223.5.5.5"
adb shell "setprop net.dns2 223.6.6.6"

# 关闭代理（如果不需要）
adb shell "settings put global http_proxy :0"
```

### 防检测配置

```powershell
# 修改设备指纹（防止被APP检测为模拟器）
adb shell "setprop ro.product.model SM-G9910"      # 三星S21
adb shell "setprop ro.product.brand samsung"
adb shell "setprop ro.product.manufacturer samsung"
adb shell "setprop ro.build.fingerprint samsung/starltexx/starlte:11/RP1A.200720.012/G960FXXU8FUE3:user/release-keys"

# 修改IMEI（需要Root）
adb shell "su -c 'service call iphonesubinfo 1'"   # 查看当前IMEI
# 使用Xposed模块或Magisk模块修改IMEI
```

## 多开配置

雷电模拟器支持多开，每个实例独立：

```powershell
# 多开管理器路径
$multiManager = "C:\LDPlayer\LDPlayer9\dnmultiplayer.exe"

# 启动多开管理器
Start-Process $multiManager

# 每个实例的ADB端口不同:
# 实例1: 127.0.0.1:5555
# 实例2: 127.0.0.1:5556
# 实例3: 127.0.0.1:5557
# ...

# 连接特定实例
adb connect 127.0.0.1:5556
```

## 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| ADB连接失败 | 模拟器未启动/端口错误 | 检查模拟器状态，尝试其他端口 |
| Root权限不生效 | 配置文件未正确修改 | 手动在设置中开启 |
| Frida-server启动失败 | 版本不匹配/权限不足 | 检查版本，重新推送 |
| Frida连接失败 | 防火墙/网络问题 | 检查防火墙，确认端口开放 |
| 模拟器卡顿 | 资源分配不足 | 增加CPU/内存分配 |
| APP检测模拟器 | 设备指纹未修改 | 修改build.prop |
| 多开实例冲突 | 端口占用 | 检查端口占用情况 |

## 与macOS主机的协同工作

### 典型工作流

```
macOS主机:
  1. 分析APK → 确定破解策略
  2. 编写Frida脚本 → 保存到共享文件夹
  3. 准备破解工具 → 复制到共享文件夹

Windows虚拟机 (PD):
  4. 通过共享文件夹获取脚本
  5. 在模拟器中运行目标APP
  6. 执行Frida注入
  7. 导出破解结果到共享文件夹

macOS主机:
  8. 从共享文件夹获取结果
  9. 验证破解效果
```

### 共享文件夹路径速查

| 用途 | macOS路径 | Windows路径 |
|------|-----------|-------------|
| Frida脚本 | `~/Desktop/scripts/` | `C:\Users\tianbin\Desktop\MacHome\scripts\` |
| APK文件 | `~/Desktop/apks/` | `C:\Users\tianbin\Desktop\MacHome\apks\` |
| 破解结果 | `~/Desktop/output/` | `C:\Users\tianbin\Desktop\MacHome\output\` |
| 工具链 | `~/Tools/` | `C:\Tools\` |

## 更新Frida-server

```powershell
# 检查当前Frida版本
$fridaVersion = (frida --version)
Write-Host "当前Frida版本: $fridaVersion"

# 下载对应版本的Frida-server
$url = "https://github.com/frida/frida/releases/download/$fridaVersion/frida-server-$fridaVersion-android-x86_64.xz"
Invoke-WebRequest -Uri $url -OutFile "C:\Tools\frida\frida-server-android-x86_64.xz"

# 解压
if (Get-Command 7z -ErrorAction SilentlyContinue) {
    7z x "C:\Tools\frida\frida-server-android-x86_64.xz" -o"C:\Tools\frida\" -y
} else {
    python -c "import lzma; open('C:\Tools\frida\frida-server-android-x86_64', 'wb').write(lzma.open('C:\Tools\frida\frida-server-android-x86_64.xz', 'rb').read())"
}

# 停止旧版Frida-server
adb shell "pkill frida-server"

# 推送新版
adb push "C:\Tools\frida\frida-server-android-x86_64" /data/local/tmp/frida-server
adb shell "chmod 755 /data/local/tmp/frida-server"

# 启动新版
adb shell "/data/local/tmp/frida-server &"

# 验证
frida-ps -U
```
