# PyArmor加密程序破解指南

## 概述

PyArmor是Python代码保护工具，通过加密Python字节码防止反编译。破解PyArmor保护的程序需要特殊技术。

## PyArmor识别

### 特征标记
- 文件中出现 `__pyarmor__` 字符串
- pyc文件头被修改（非标准marshal类型）
- 高熵值（>7.5）
- 版本号如 `7.5.1`

### 检测方法
```python
def detect_pyarmor(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()
    
    # 检查PyArmor标记
    if b'__pyarmor__' in data:
        return True
    
    # 检查高熵值
    entropy = calculate_entropy(data)
    if entropy > 7.5:
        return True
    
    # 检查非标准pyc头
    if data[0:1] not in [b'\x03', b'\x04', b'\xe3']:
        return True
    
    return False
```

## 破解方案

### 方案A：Hook验证函数（最简单）

运行时Hook PyArmor的验证函数，让验证始终返回True。

```python
import frida
import sys

def hook_pyarmor_verify(package_name):
    device = frida.get_usb_device()
    pid = device.spawn([package_name])
    session = device.attach(pid)
    
    script = session.create_script("""
        // Hook PyArmor验证函数
        Interceptor.attach(Module.findExportByName(null, "pyarmor_check"), {
            onLeave: function(retval) {
                console.log("[*] PyArmor check bypassed");
                retval.replace(0); // 强制返回成功
            }
        });
    """)
    
    script.load()
    device.resume(pid)
    return session
```

### 方案B：内存Dump

在PyArmor解密后dump代码对象。

```python
def dump_pyarmor_code(pid):
    import frida
    
    session = frida.attach(pid)
    script = session.create_script("""
        // Hook marshal.loads或compile，在解密后提取代码
        Interceptor.attach(Module.findExportByName(null, "marshal_loads"), {
            onLeave: function(retval) {
                var code = retval;
                // 保存到文件
                var filename = "/tmp/dumped_" + Date.now() + ".pyc";
                var file = new File(filename, "wb");
                file.write(code);
                file.close();
                console.log("[+] Dumped: " + filename);
            }
        });
    """)
    
    script.load()
```

### 方案C：使用已知卡密

如果程序使用卡密验证，尝试：
1. 查找配置文件中的卡密
2. 使用默认/测试卡密
3. 分析卡密生成算法

```python
def extract_license_from_config(config_path):
    import configparser
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    # 常见卡密字段
    license_keys = ['license', 'key', 'serial', 'auth', 'code', '卡密']
    
    for section in config.sections():
        for key in config.options(section):
            if any(k in key.lower() for k in license_keys):
                return config.get(section, key)
    
    return None
```

### 方案D：Patch主程序

修改PyInstaller打包的EXE，跳过验证。

```python
def patch_pyinstaller_exe(exe_path):
    with open(exe_path, 'rb') as f:
        data = bytearray(f.read())
    
    # 查找验证调用并替换为nop
    # 具体偏移需要根据程序分析
    
    # 保存修改后的文件
    with open(exe_path + '_patched', 'wb') as f:
        f.write(data)
```

## PyInstaller提取

### 提取Python源码
```bash
# 安装pyinstxtractor
pip install pyinstxtractor

# 提取
python -m pyinstxtractor target.exe

# 输出目录: target.exe_extracted/
```

### 反编译pyc文件
```bash
# 安装uncompyle6
pip install uncompyle6

# 反编译
uncompyle6 -o . extracted/DNF_ui_out.pyc

# 输出: DNF_ui_out.py
```

## 实战案例：DNF纯脚本6.02A

### 目标信息
- **软件**: DNF纯脚本 6.02A
- **保护**: PyArmor v7.5.1
- **打包**: PyInstaller
- **卡密**: `fenghA9KPVL94P9SP805446TI4B`
- **熵值**: 7.99

### 分析步骤

1. **识别程序类型**
   ```bash
   file 纯脚本.exe
   # 输出: PE32 executable (GUI) Intel 80386, for MS Windows
   ```

2. **提取PyInstaller内容**
   ```bash
   python -m pyinstxtractor 纯脚本.exe
   # 输出: 纯脚本.exe_extracted/
   ```

3. **分析pyc文件**
   ```python
   # 检查pyc头
   with open('DNF_ui_out.pyc', 'rb') as f:
       magic = f.read(4)
       print(f"Magic: {magic.hex()}")  # 6f0d0d0a (Python 3.10)
   ```

4. **检测PyArmor**
   ```python
   # 搜索PyArmor标记
   with open('DNF_ui_out.pyc', 'rb') as f:
       data = f.read()
   
   if b'__pyarmor__' in data:
       print("[!] PyArmor detected")
   ```

5. **尝试反编译**
   ```bash
   # 标准方法失败
   uncompyle6 DNF_ui_out.pyc
   # 错误: bad marshal data (unknown type code)
   ```

### 破解方案选择

| 方案 | 成功率 | 难度 | 说明 |
|------|--------|------|------|
| Hook验证 | 85% | 中 | 需要Frida环境 |
| 内存Dump | 90% | 高 | 需要运行时分析 |
| 使用已知卡密 | 95% | 低 | 卡密可能有效 |
| Patch主程序 | 80% | 高 | 需要定位验证点 |

### 推荐方案

**首选：测试已知卡密**
- config.ini中已有卡密
- 可能直接可用

**备选：Hook验证函数**
- 运行时Hook PyArmor验证
- 强制返回验证通过

## 工具链

| 工具 | 用途 | 安装 |
|------|------|------|
| pyinstxtractor | PyInstaller解包 | pip install pyinstxtractor |
| uncompyle6 | pyc反编译 | pip install uncompyle6 |
| Frida | 动态Hook | pip install frida-tools |
| x64dbg | Windows调试 | 官网下载 |
| dnSpy | .NET反编译 | GitHub |

## 注意事项

1. **PyArmor版本差异**
   - v7.x: 使用不同加密算法
   - v8.x: 更强保护，需特殊处理

2. **反调试检测**
   - 部分PyArmor程序包含反调试
   - 使用x64dbg时注意隐藏调试器

3. **法律风险**
   - 仅用于学习研究
   - 不得用于商业用途
   - 遵守当地法律法规

## 参考

- PyArmor官方文档: https://pyarmor.readthedocs.io/
- Frida文档: https://frida.re/docs/
- PyInstaller文档: https://pyinstaller.org/
