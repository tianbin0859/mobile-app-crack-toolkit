# 环境依赖检查与准备

## 概述

APK Crack Engine需要特定的工具链支持，执行前必须检查环境完整性，缺失时提供替代方案。

## 必需工具清单

| 工具 | 用途 | 检查命令 | 缺失处理 |
|------|------|----------|----------|
| **apktool** | 反编译/重打包APK | `which apktool` | 使用Python zipfile替代 |
| **aapt** | 获取APK包名信息 | `which aapt` | 使用Python二进制XML解析 |
| **adb** | 连接Android设备 | `which adb` | 切换离线模式 |
| **frida** | 运行时Hook | `which frida` | 切换离线模式 |
| **jarsigner** | APK签名 | `which jarsigner` | 使用Python签名工具 |
| **java** | 运行Java工具 | `which java` | 切换纯Python方案 |

## 自动检查流程

```python
import subprocess
import shutil

def check_environment():
    """检查环境工具链完整性"""
    tools = {
        'apktool': {'required': False, 'fallback': 'python_zipfile'},
        'aapt': {'required': False, 'fallback': 'python_xml_parser'},
        'adb': {'required': False, 'fallback': 'offline_mode'},
        'frida': {'required': False, 'fallback': 'offline_mode'},
        'jarsigner': {'required': False, 'fallback': 'python_signer'},
        'java': {'required': False, 'fallback': 'python_only'},
    }
    
    results = {}
    for tool, config in tools.items():
        available = shutil.which(tool) is not None
        results[tool] = {
            'available': available,
            'fallback': config['fallback'] if not available else None
        }
    
    return results
```

## 缺失处理策略

### apktool缺失
```python
# 替代方案：使用Python zipfile直接操作APK
import zipfile
import os

def extract_apk(apk_path, output_dir):
    """无需apktool解压APK"""
    with zipfile.ZipFile(apk_path, 'r') as z:
        z.extractall(output_dir)
    return True

def repack_apk(source_dir, output_apk):
    """无需apktool重新打包"""
    with zipfile.ZipFile(output_apk, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zf.write(file_path, arcname)
    return True
```

### aapt缺失
```python
# 替代方案：Python解析二进制XML获取包名
def get_package_name(apk_path):
    """无需aapt获取包名"""
    import zipfile
    import re
    
    with zipfile.ZipFile(apk_path, 'r') as z:
        manifest = z.read('AndroidManifest.xml')
    
    # 解析二进制XML中的包名
    manifest_str = manifest.decode('utf-8', errors='ignore')
    matches = re.findall(r'com\.[a-zA-Z0-9_.]+', manifest_str)
    
    # 过滤最可能的包名
    for m in matches:
        if len(m) > 10 and not m.startswith('com.android'):
            return m
    
    return None
```

### adb/frida缺失
```python
# 自动切换离线模式
if not shutil.which('adb') or not shutil.which('frida'):
    print("⚠️ 设备工具缺失，自动切换离线模式")
    mode = 'offline'
```

## 脚本参数使用示例

### 正确参数格式
```bash
# ✅ 正确：指定包名 + APK路径 + 离线模式
python3 apk_crack_enhanced.py com.humble.SlayTheSpire --apk "/path/to/game.apk" --offline

# ✅ 正确：仅指定包名（在线模式，需要设备）
python3 apk_crack_enhanced.py com.nx.assist

# ❌ 错误：缺少包名参数
python3 apk_crack_enhanced.py --apk "/path/to/game.apk" --offline

# ❌ 错误：使用不支持的参数
python3 apk_crack_enhanced.py --mode auto --verbose
```

### 参数说明
```
usage: apk_crack_enhanced.py [-h] [--apk APK] [--offline] [--cloud CLOUD]
                             [--batch BATCH [BATCH ...]]
                             package

positional arguments:
  package               目标包名 (必需)

optional arguments:
  -h, --help            显示帮助
  --apk APK             APK文件路径（离线模式必需）
  --offline             强制离线模式（无需设备）
  --cloud CLOUD         云手机IP:端口
  --batch BATCH ...     批量破解包名列表
```

## 常见错误处理

### 错误1：缺少包名参数
```
apk_crack_enhanced.py: error: the following arguments are required: package
```
**解决**：必须提供包名作为第一个参数

### 错误2：不支持的参数
```
apk_crack_enhanced.py: error: unrecognized arguments: --mode auto --verbose
```
**解决**：删除不支持的参数，使用标准参数

### 错误3：apktool未找到
```
[Errno 2] No such file or directory: 'apktool'
```
**解决**：使用Python zipfile替代，或安装apktool

## 环境准备脚本

```python
#!/usr/bin/env python3
"""环境检查与准备脚本"""

import shutil
import subprocess
import sys

def setup_environment():
    """检查并准备破解环境"""
    print("🔧 检查APK Crack Engine环境...")
    
    tools = ['apktool', 'aapt', 'adb', 'frida', 'jarsigner', 'java']
    missing = []
    
    for tool in tools:
        if shutil.which(tool):
            print(f"  ✅ {tool}")
        else:
            print(f"  ❌ {tool} (将使用替代方案)")
            missing.append(tool)
    
    if missing:
        print(f"\n⚠️ 缺失 {len(missing)} 个工具，将启用兼容模式")
        print("替代方案:")
        for tool in missing:
            fallback = {
                'apktool': 'Python zipfile',
                'aapt': 'Python XML解析',
                'adb': '离线模式',
                'frida': '离线模式',
                'jarsigner': 'Python签名',
                'java': '纯Python方案'
            }.get(tool, '未知')
            print(f"  - {tool} → {fallback}")
    
    return len(missing) == 0

if __name__ == '__main__':
    ready = setup_environment()
    sys.exit(0 if ready else 1)
```
