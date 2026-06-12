# PyInstaller EXE 逆向分析指南

## 适用场景
- PyInstaller打包的Python程序逆向
- 游戏辅助/自动化脚本破解
- 商业软件授权验证绕过

## 识别PyInstaller打包

### 文件特征
```
1. 文件大小: 通常50MB-200MB (包含Python运行时)
2. PE头: 正常的Windows PE文件
3. 字符串特征: 包含大量Python相关字符串
   - PyInit_*, PyImport_*, PyModule_*
   - _MEIPASS, base_library.zip
   - Cryptodome (常见加密库)
4. 节区: 通常包含UPX压缩或大量资源节区
```

### 快速识别命令
```bash
# 查看字符串
strings -n 8 program.exe | grep -iE "(PyInstaller|_MEIPASS|PyInit|base_library)"

# 查看PE信息
file program.exe
pefile分析工具
```

## 从ZIP/压缩包提取EXE

PyInstaller程序常被打包在ZIP中分发。当标准解压工具失败时：

### 标准解压
```bash
unzip -o archive.zip -d output_dir/
```

### 当unzip失败时的替代方案
```bash
# 错误特征: "invalid compressed data to inflate" / "bad zipfile offset"
# 解决方案: 使用7z替代

# 7z提取 (支持更多压缩格式和损坏修复)
7z x archive.zip -ooutput_dir/

# 7z测试完整性
7z t archive.zip

# 7z列出内容
7z l archive.zip
```

### 提取后验证
```bash
# 检查提取的EXE
file output_dir/launcher.exe
# 预期输出: PE32+ executable (GUI) x86-64, for MS Windows

# 检查_internal目录（PyInstaller onedir模式特征）
ls output_dir/_internal/
# 预期: python38.dll, base_library.zip, 各种.pyd/.dll文件
```

## 提取Python源码

### 工具链
| 工具 | 用途 | 安装 |
|------|------|------|
| pyinstxtractor | 提取PyInstaller存档 | `pip install pyinstxtractor` |
| pyinstxtractor-ng | 增强版提取器 (支持新版PyInstaller) | `pip install pyinstxtractor-ng` |
| uncompyle6 | 反编译Python 3.8- | `pip install uncompyle6` |
| decompyle3 | 反编译Python 3.7+ | `pip install decompyle3` |
| pycdc | 通用反编译器 | 编译安装 |
| pyarmor_decrypt | 解密pyarmor | 专用工具 |

### 提取流程

```bash
# Step 1: 提取PyInstaller存档
python -m pyinstxtractor program.exe
# 输出: program.exe_extracted/ 目录

# Step 2: 找到主程序入口
# 查看 program.exe_extracted/PYZ-00.pyz 或 struct文件

# Step 3: 反编译pyc文件
# Python 3.8及以下
uncompyle6 -o . program.exe_extracted/*.pyc

# Python 3.9+
pycdc program.exe_extracted/*.pyc

# Step 4: 分析源码，定位验证逻辑
# 搜索关键词: auth, license, verify, check, key, activate
```

### 高级：当pyinstxtractor失败时的手动分析

当pyinstxtractor报告"Missing pyinstaller archive"或"Expected magic number 4D454913, got 00000000"时，说明CArchive头被加密、压缩或位于非标准位置。此时需要手动分析：

#### 1. 检查PE overlay/appendix
```bash
# 计算PE总大小 vs 实际文件大小
objdump -h program.exe
# 计算各节区大小总和，与实际文件大小对比
# 差值即为overlay（附加数据）大小

# 提取overlay
python3 -c "
import pefile
pe = pefile.PE('program.exe')
overlay_offset = pe.get_overlay_data_start_offset()
if overlay_offset:
    with open('program.exe','rb') as f:
        f.seek(overlay_offset)
        overlay = f.read()
    with open('overlay.bin','wb') as f:
        f.write(overlay)
    print(f'Overlay extracted: {len(overlay)} bytes at offset {hex(overlay_offset)}')
else:
    print('No overlay found')
"
```

#### 2. 搜索zlib压缩流
```bash
# PyInstaller常用zlib压缩，搜索zlib头(0x789c)
python3 -c "
import zlib
data = open('program.exe','rb').read()
# 搜索zlib头
for i in range(len(data)-2):
    if data[i:i+2] == b'\x78\x9c':
        try:
            decompressed = zlib.decompress(data[i:])
            print(f'Found zlib stream at {hex(i)}, decompressed {len(decompressed)} bytes')
            print(f'First 100 bytes: {decompressed[:100]}')
            break
        except:
            pass
"
```

#### 3. 检查_internal目录（onedir模式）
```bash
# 如果是onedir模式，程序代码可能在_internal目录中
find program_extracted/_internal -name '*.pyc' -o -name '*.py' 2>/dev/null

# 检查base_library.zip（标准库）
unzip -l program_extracted/_internal/base_library.zip

# 搜索可能的PYZ或PKG文件
find program_extracted -name '*.pyz' -o -name '*.pkg' -o -name '*archive*'
```

#### 4. 使用pyinstxtractor-ng（增强版）
```bash
# 安装增强版提取器
pip install pyinstxtractor-ng

# 尝试提取（支持更多PyInstaller版本和加密变体）
python -m pyinstxtractor-ng program.exe
```

#### 5. 内存Dump（最后手段）
```bash
# 在Windows虚拟机中运行程序，使用Process Hacker或WinDbg Dump内存
# 搜索Python字节码特征（如marshal头）
# 然后使用pycdc反编译Dump出的数据
```

### Python自动化提取脚本

```python
#!/usr/bin/env python3
"""
PyInstaller EXE自动提取工具
"""

import struct
import os
import subprocess

class PyInstallerExtractor:
    def __init__(self, exe_path):
        self.exe_path = exe_path
        self.extract_dir = exe_path + "_extracted"
        
    def extract(self):
        """提取PyInstaller存档"""
        # 方法1: 使用pyinstxtractor
        result = subprocess.run(
            ["python", "-m", "pyinstxtractor", self.exe_path],
            capture_output=True, text=True
        )
        
        if "Successfully" in result.stdout:
            print(f"[+] 提取成功: {self.extract_dir}")
            return True
        else:
            print(f"[!] 提取失败: {result.stderr}")
            return False
    
    def find_main_script(self):
        """找到主程序入口"""
        for root, dirs, files in os.walk(self.extract_dir):
            for file in files:
                if file.endswith('.pyc') and 'struct' not in file:
                    return os.path.join(root, file)
        return None
    
    def decompile(self, pyc_path):
        """反编译pyc文件"""
        output_dir = os.path.dirname(pyc_path)
        
        # 尝试多种反编译器
        tools = [
            ["uncompyle6", "-o", output_dir, pyc_path],
            ["decompyle3", "-o", output_dir, pyc_path],
            ["pycdc", pyc_path],
        ]
        
        for tool in tools:
            try:
                result = subprocess.run(tool, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    print(f"[+] 反编译成功: {tool[0]}")
                    return True
            except:
                continue
        
        print("[!] 反编译失败，可能需要手动处理")
        return False

# 使用示例
if __name__ == "__main__":
    extractor = PyInstallerExtractor("target.exe")
    if extractor.extract():
        main_script = extractor.find_main_script()
        if main_script:
            extractor.decompile(main_script)
```

## 破解授权验证

### 常见验证模式

#### 模式1: 本地文件验证
```python
# 原始代码
def check_license():
    with open('license.dat', 'rb') as f:
        data = f.read()
    return verify_signature(data)

# 破解: 直接返回True
def check_license():
    return True
```

#### 模式2: 网络API验证
```python
# 原始代码
def verify_online(key):
    response = requests.post('https://api.example.com/verify', 
                           data={'key': key})
    return response.json()['valid']

# 破解方案A: 本地返回
def verify_online(key):
    return {'valid': True, 'expire': '2099-12-31'}

# 破解方案B: 劫持DNS/Hosts
# 搭建本地假服务器返回永久授权
```

#### 模式3: 注册表验证
```python
# 原始代码 (Windows)
import winreg

def check_registry():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                           "Software\\App\\License")
        value, _ = winreg.QueryValueEx(key, "Activated")
        return value == 1
    except:
        return False

# 破解: 直接返回True
def check_registry():
    return True
```

#### 模式4: 加密配置验证
```python
# 原始代码
from Cryptodome.Cipher import AES

def decrypt_license(encrypted_data):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.decrypt(encrypted_data)

# 破解: 跳过解密，直接返回有效配置
def decrypt_license(encrypted_data):
    return b'{"valid": true, "expire": "2099-12-31"}'
```

### 自动化Patch脚本

```python
#!/usr/bin/env python3
"""
Python授权验证自动Patch工具
"""

import re
import os

class LicensePatcher:
    def __init__(self, source_dir):
        self.source_dir = source_dir
        
    def patch_all(self):
        """自动Patch所有验证逻辑"""
        for root, dirs, files in os.walk(self.source_dir):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    self.patch_file(filepath)
    
    def patch_file(self, filepath):
        """Patch单个文件"""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original = content
        
        # Pattern 1: 简单验证函数
        content = re.sub(
            r'def\s+(check|verify|auth)_\w+\s*\([^)]*\)\s*:\s*\n(?:\s+.+\n)*',
            lambda m: f'{m.group(0).split(chr(10))[0]}\n    return True\n',
            content
        )
        
        # Pattern 2: 类方法
        content = re.sub(
            r'def\s+(is_licensed|is_activated|is_valid)\s*\([^)]*\)\s*:\s*\n(?:\s+.+\n)*',
            lambda m: f'{m.group(0).split(chr(10))[0]}\n    return True\n',
            content
        )
        
        # Pattern 3: 网络请求验证
        content = re.sub(
            r'requests\.(post|get)\s*\([^)]*verify[^)]*\)',
            '{"valid": True, "expire": "2099-12-31"}',
            content
        )
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[+] Patched: {filepath}")

# 使用
# patcher = LicensePatcher("/path/to/extracted/source")
# patcher.patch_all()
```

## 重新打包

### 方法1: 直接运行Python源码
```bash
# 最简单的方式，直接运行修改后的Python代码
python extracted_source/main.py
```

### 方法2: PyInstaller重新打包
```bash
# 安装PyInstaller
pip install pyinstaller

# 打包为单文件
pyinstaller --onefile --noconsole modified_main.py

# 打包为目录 (保留资源文件)
pyinstaller --noconsole modified_main.py
```

### 方法3: 创建启动器
```python
#!/usr/bin/env python3
"""
破解程序启动器
绕过验证直接启动核心功能
"""

import sys
import os

# 添加源码目录到路径
sys.path.insert(0, 'extracted_source')

# 导入并Patch验证模块
import original_module
original_module.check_license = lambda: True
original_module.verify_online = lambda x: {"valid": True}

# 启动主程序
from original_module import main
main()
```

## 高级技巧

### 1. 内存Dump (无法静态提取时)
```bash
# 使用Process Hacker / Memory Scanner
# 在程序运行时Dump内存中的Python字节码
# 然后使用pycdc反编译
```

### 2. Hook Python C API
```c
// 编写DLL注入Python进程
// Hook PyRun_SimpleString等函数
// 在运行时修改验证逻辑
```

### 3. 调试器动态分析
```bash
# x64dbg / OllyDbg
# 设置断点在验证函数
# 修改返回值或跳转逻辑
```

### 检查已破解/预提取的文件

有时分发的ZIP中已包含破解后的文件或预提取的源码：

```bash
# 检查_internal目录中是否有非标准文件
find extracted/_internal -type f | sort

# 检查是否有Python源码文件（而非仅.pyc）
find extracted/_internal -name '*.py' 2>/dev/null

# 检查是否有patch文件或修改标记
find extracted -name '*.patch' -o -name '*.bak' -o -name '*crack*' -o -name '*patch*'

# 检查配置文件是否已被修改
grep -r "2099\|9999\|True\|false" extracted/_internal/*.ini extracted/_internal/*.cfg 2>/dev/null

# 检查是否有额外的脚本文件
find extracted -name '*.lua' -o -name '*.js' -o -name '*.txt' | grep -v base_library
```

### 常见问题

### Q: 提取后只有.pyc文件，如何反编译？
A: 尝试多种工具：uncompyle6 → decompyle3 → pycdc。如果都失败，可能是pyarmor加密，需要专用解密工具。

### Q: 程序使用pyarmor加密？
A: pyarmor加密的代码需要特殊处理：
1. 查找pyarmor运行时密钥
2. 使用pyarmor_decrypt工具
3. 或者Hook pyarmor的解密函数

### Q: 反编译后的代码有语法错误？
A: 反编译不完美，需要手动修复：
1. 检查缩进
2. 修复异常处理语法
3. 补充缺失的导入

### Q: 修改后程序无法运行？
A: 检查：
1. 依赖包是否完整
2. 资源文件路径是否正确
3. 是否有硬编码的路径/签名验证

## 参考案例

### 案例1: DNF自动搬砖脚本破解
- **目标**: PyInstaller打包的Python程序 (97.4MB)
- **保护**: Cryptodome加密 + 在线卡密验证
- **卡密**: `fenghA9KPVL94P9SP805446TI4B`
- **技术栈**: pmem内存驱动 + libVNC + BMP图像识别
- **破解方案**: 
  1. pyinstxtractor提取Python源码
  2. 定位验证函数 (requests.post到验证服务器)
  3. Patch验证函数返回永久授权
  4. 重新打包或直接使用源码运行

### 案例2: 528文件破解 (PyInstaller onedir模式)
- **目标**: PyInstaller打包的Windows程序 (launcher.exe + _internal目录)
- **分发**: ZIP压缩包 (337MB，解压后3.8MB EXE + 大量DLL)
- **环境**: macOS (无法直接运行Windows PE)
- **技术栈**: 7z提取 + 静态PE分析 + pyinstxtractor-ng
- **分析过程**:
  1. `unzip`失败 → 使用`7z x`成功提取（ZIP文件损坏/非标准压缩）
  2. 识别PyInstaller结构：`launcher.exe` + `_internal/`目录
  3. `pyinstxtractor`失败（CArchive头缺失/非标准位置）
  4. 手动分析PE overlay：计算节区大小，提取尾部数据
  5. 搜索zlib流：在PE文件中寻找压缩数据
  6. 检查`_internal`目录：确认标准运行时库，无预提取源码
  7. 结论：需要Windows环境运行后动态分析，或尝试pyinstxtractor-ng
- **关键教训**: 
  - 当`unzip`失败时，`7z`是更可靠的替代方案
  - PyInstaller onedir模式的代码可能在EXE的overlay中，也可能在`_internal`的隐藏文件中
  - 静态分析无法提取时，需要Windows虚拟机+动态调试

## 工具推荐

| 工具 | 用途 | 链接 |
|------|------|------|
| pyinstxtractor | PyInstaller提取 | pip安装 |
| uncompyle6 | Python反编译 | pip安装 |
| pycdc | 通用反编译 | GitHub |
| x64dbg | Windows调试器 | x64dbg.com |
| Process Hacker | 内存分析 | processhacker.sourceforge.io |
| dnSpy | .NET反编译 | GitHub |

---

*提取日期: 2026-06-09 | 来源: DNF脚本6.02A逆向分析*
