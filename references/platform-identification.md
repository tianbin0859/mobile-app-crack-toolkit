# 平台识别与目标验证

## 概述

防止将PC游戏误认为Android APK的常见错误，确保破解目标与工具匹配。

## 平台识别检查清单

### 执行前必须确认

| 检查项 | Android APK | iOS IPA | Windows EXE | Steam游戏 |
|--------|-------------|---------|-------------|-----------|
| **文件扩展名** | .apk | .ipa | .exe | 无固定扩展名 |
| **典型大小** | 10MB-2GB | 10MB-2GB | 1MB-500MB | 数GB (安装目录) |
| **可执行格式** | ZIP压缩包 | ZIP压缩包 | PE格式 | 混合格式 |
| **运行平台** | Android设备 | iOS设备 | Windows PC | Windows/Mac/Linux |
| **破解工具** | APK Crack Engine | IPA Crack模块 | PE分析工具 | Cheat Engine/存档修改 |

### 常见错误案例

**错误案例1：Steam游戏误认为APK**
```
❌ 错误：尝试用APK Crack Engine破解Steam版杀戮尖塔2
✅ 正确：Steam游戏使用Cheat Engine内存修改或存档修改
```

**错误案例2：PC模拟器游戏**
```
❌ 错误：将PC模拟器运行的Android游戏当作原生APK
✅ 正确：确认文件来源，检查是否为真实APK文件
```

## 自动检测方法

```python
def identify_platform(file_path):
    """自动识别目标平台"""
    import os
    import zipfile
    
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.apk':
        # 验证是否为真实APK
        try:
            with zipfile.ZipFile(file_path, 'r') as z:
                has_manifest = 'AndroidManifest.xml' in z.namelist()
                has_dex = any(f.startswith('classes') and f.endswith('.dex') for f in z.namelist())
                if has_manifest and has_dex:
                    return "ANDROID_APK"
        except:
            pass
        return "UNKNOWN_ZIP"
    
    elif ext == '.ipa':
        return "IOS_IPA"
    
    elif ext == '.exe':
        return "WINDOWS_EXE"
    
    elif ext in ['.zip', '.rar', '.7z']:
        return "ARCHIVE"
    
    else:
        return "UNKNOWN"
```

## 平台不匹配处理

| 目标平台 | 用户请求 | 正确处理 |
|----------|----------|----------|
| Steam PC游戏 | "破解APK" | 纠正平台，使用PC破解工具 |
| Android APK | "破解Steam" | 确认是否为PC模拟器版本 |
| iOS IPA | "破解Android" | 使用iOS专用破解流程 |

## 验证示例

```
🎯 [感知] 正在识别目标平台...
   📦 文件: 杀戮尖塔2.exe (2.3GB)
   ❌ 平台不匹配: 用户请求APK破解，但目标为Windows EXE
   
   💭 思索: 目标为Steam版PC游戏，不是Android APK。
          APK Crack Engine不适用于此目标。
          应使用Cheat Engine或存档修改工具。
   
   ⚠️ 纠正建议:
      1. 使用Cheat Engine修改内存 (推荐)
      2. 修改存档文件获取全装备
      3. 使用Steam成就修改器
```
