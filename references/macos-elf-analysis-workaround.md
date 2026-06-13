# macOS ELF分析工具替代方案

## 问题背景

macOS系统默认不提供`readelf`工具（GNU Binutils的一部分），但APK破解中经常需要分析Android Native库（.so文件，ELF格式）。直接调用`readelf`会导致`FileNotFoundError`，且如果代码未处理异常，会陷入重复调用循环。

## 工具替代矩阵

| 功能 | Linux (readelf) | macOS替代方案 | 可用性 |
|------|----------------|--------------|--------|
| 查看ELF头 | `readelf -h` | `file` + `otool -h` | ✅ 内置 |
| 查看节区表 | `readelf -S` | `nm` + `objdump -h` | ✅ 需安装binutils |
| 查看导出符号 | `readelf -s` | `nm -D` | ✅ 内置 |
| 查看动态段 | `readelf -d` | `otool -l` | ✅ 内置 |
| 查看重定位 | `readelf -r` | `objdump -r` | ✅ 需安装binutils |
| 反汇编 | `readelf -x` | `objdump -d` | ✅ 需安装binutils |

## 推荐方案

### 方案1: 使用`nm`（最可靠，macOS内置）

```bash
# 查看导出符号（替代 readelf -s）
nm -D libtarget.so

# 查看所有符号
nm -a libtarget.so

# 仅查看外部符号
nm -g libtarget.so
```

### 方案2: 使用`otool`（macOS内置）

```bash
# 查看动态段（替代 readelf -d）
otool -l libtarget.so | grep -A 5 "LC_LOAD_DYLIB"

# 查看符号表
otool -I libtarget.so
```

### 方案3: 安装binutils获取`objdump`

```bash
# 通过Homebrew安装（如果可用）
brew install binutils

# 安装后使用g前缀（避免与macOS工具冲突）
gobjdump -h libtarget.so
gobjdump -d libtarget.so
```

### 方案4: Python纯代码分析（无需外部工具）

```python
import struct

def parse_elf_header(path):
    """纯Python解析ELF头，无需readelf"""
    with open(path, 'rb') as f:
        # ELF魔数
        magic = f.read(4)
        if magic != b'\x7fELF':
            raise ValueError("Not an ELF file")
        
        # 32/64位
        ei_class = f.read(1)[0]
        bitness = 32 if ei_class == 1 else 64
        
        # 字节序
        ei_data = f.read(1)[0]
        endian = '<' if ei_data == 1 else '>'
        
        # 机器类型
        f.seek(18)
        e_machine = struct.unpack(f'{endian}H', f.read(2))[0]
        
        # 入口点
        if bitness == 32:
            f.seek(24)
            e_entry = struct.unpack(f'{endian}I', f.read(4))[0]
        else:
            f.seek(24)
            e_entry = struct.unpack(f'{endian}Q', f.read(8))[0]
        
        return {
            'bitness': bitness,
            'endian': 'little' if ei_data == 1 else 'big',
            'machine': e_machine,
            'entry_point': hex(e_entry)
        }

# 使用示例
info = parse_elf_header('libtarget.so')
print(f"架构: {info['bitness']}-bit, 入口点: {info['entry_point']}")
```

## 工具循环防护

### 问题描述

当代码重复调用失败的外部工具时，会触发工具循环警告（如本次会话中execute_code重复调用23次）。

### 防护代码模板

```python
import subprocess
import shutil

def safe_tool_call(cmd, fallback_cmds=None, max_retries=1):
    """
    安全调用外部工具，带降级和重试保护
    
    Args:
        cmd: 主命令列表，如 ['readelf', '-h', 'file.so']
        fallback_cmds: 降级命令列表，如 [['nm', '-D', 'file.so'], ['otool', '-l', 'file.so']]
        max_retries: 最大重试次数（默认1，避免循环）
    
    Returns:
        (stdout, stderr, returncode, used_cmd)
    """
    tool_name = cmd[0]
    
    # 检查工具是否存在
    if not shutil.which(tool_name):
        print(f"⚠️ 工具 {tool_name} 不可用，尝试降级方案...")
        
        # 尝试降级方案
        if fallback_cmds:
            for fallback in fallback_cmds:
                fallback_tool = fallback[0]
                if shutil.which(fallback_tool):
                    print(f"✅ 使用替代工具: {fallback_tool}")
                    result = subprocess.run(fallback, capture_output=True, text=True)
                    return result.stdout, result.stderr, result.returncode, fallback
        
        # 所有方案都失败
        return "", f"工具 {tool_name} 及其替代方案均不可用", 127, cmd
    
    # 执行主命令
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # 如果失败且有重试次数
    if result.returncode != 0 and max_retries > 0:
        print(f"⚠️ {tool_name} 失败，尝试降级...")
        return safe_tool_call(cmd, fallback_cmds, max_retries=0)
    
    return result.stdout, result.stderr, result.returncode, cmd

# 使用示例
stdout, stderr, rc, used = safe_tool_call(
    ['readelf', '-h', 'libtarget.so'],
    fallback_cmds=[
        ['file', 'libtarget.so'],
        ['nm', '-D', 'libtarget.so'],
        ['otool', '-l', 'libtarget.so']
    ]
)

if rc == 0:
    print(f"成功使用 {used[0]} 分析")
    print(stdout[:500])
else:
    print(f"分析失败: {stderr}")
```

## 完整分析脚本（macOS兼容版）

```python
#!/usr/bin/env python3
"""
macOS兼容的ELF/PE分析脚本
无需readelf，使用内置工具或纯Python实现
"""

import subprocess
import shutil
import struct
import sys

def analyze_elf(path):
    """分析ELF文件（macOS兼容）"""
    print(f"\n=== 分析: {path} ===")
    
    # 1. 文件类型识别（内置file命令）
    result = subprocess.run(['file', path], capture_output=True, text=True)
    print(f"文件类型: {result.stdout.strip()}")
    
    # 2. 导出符号（nm -D，内置）
    if shutil.which('nm'):
        result = subprocess.run(['nm', '-D', path], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            print(f"\n导出符号 ({len(lines)}个):")
            for line in lines[:20]:
                print(f"  {line}")
            if len(lines) > 20:
                print(f"  ... 还有 {len(lines)-20} 个")
    
    # 3. 字符串提取（strings，内置）
    result = subprocess.run(['strings', path], capture_output=True, text=True)
    strings = result.stdout.strip().split('\n')
    
    # 搜索关键字符串
    keywords = ['http', 'api', 'auth', 'license', 'vip', 'verify', 'server', 'url']
    found = [s for s in strings if any(k in s.lower() for k in keywords)]
    if found:
        print(f"\n关键字符串 ({len(found)}个):")
        for s in found[:10]:
            print(f"  {s}")
    
    # 4. Python解析ELF头
    try:
        info = parse_elf_header(path)
        print(f"\nELF头信息:")
        print(f"  架构: {info['bitness']}-bit")
        print(f"  字节序: {info['endian']}")
        print(f"  入口点: {info['entry_point']}")
    except Exception as e:
        print(f"ELF解析失败: {e}")

def parse_elf_header(path):
    """纯Python解析ELF头"""
    with open(path, 'rb') as f:
        magic = f.read(4)
        if magic != b'\x7fELF':
            raise ValueError("Not an ELF file")
        
        ei_class = f.read(1)[0]
        ei_data = f.read(1)[0]
        endian = '<' if ei_data == 1 else '>'
        bitness = 32 if ei_class == 1 else 64
        
        f.seek(18)
        e_machine = struct.unpack(f'{endian}H', f.read(2))[0]
        
        if bitness == 32:
            f.seek(24)
            e_entry = struct.unpack(f'{endian}I', f.read(4))[0]
        else:
            f.seek(24)
            e_entry = struct.unpack(f'{endian}Q', f.read(8))[0]
        
        return {
            'bitness': bitness,
            'endian': 'little' if ei_data == 1 else 'big',
            'machine': e_machine,
            'entry_point': hex(e_entry)
        }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python macos_elf_analyzer.py <elf_file>")
        sys.exit(1)
    
    analyze_elf(sys.argv[1])
```

## 实战应用

### 分析Arkari混淆的SO库

```python
# 本次会话中的实际案例：Loader.apk_副本
so_path = "lib/arm64-v8a/libid1z5u62rg48rrchhw3.so"

# 1. 使用nm查看导出符号（发现关键函数）
nm -D libid1z5u62rg48rrchhw3.so
# 输出: JNI_OnLoad, Mundo_Activate_SDK

# 2. 使用strings搜索混淆器特征
strings libid1z5u62rg48rrchhw3.so | grep -i "Arkari"
# 输出: clang version 19.1.3 (git@github.com:KomiMoe/Arkari.git)

# 3. 使用Python解析ELF头（无需readelf）
python3 -c "
import struct
with open('libid1z5u62rg48rrchhw3.so', 'rb') as f:
    f.read(4)  # ELF magic
    bitness = 64 if f.read(1)[0] == 2 else 32
    endian = '<' if f.read(1)[0] == 1 else '>'
    f.seek(24)
    entry = struct.unpack(f'{endian}Q', f.read(8))[0] if bitness == 64 else struct.unpack(f'{endian}I', f.read(4))[0]
    print(f'{bitness}-bit ELF, entry: {hex(entry)}')
"
```

## 陷阱与注意事项

1. **不要假设readelf存在**：macOS上没有readelf，代码必须先检查`shutil.which()`
2. **优先使用内置工具**：`file`, `nm`, `strings`, `otool` 都是macOS内置的
3. **异常处理必须完善**：每个subprocess.run都要有returncode检查，失败时不能重复调用相同命令
4. **工具循环防护**：设置最大重试次数为1，失败后立即尝试降级方案，不要无限重试
5. **纯Python备用**：对于简单分析（ELF头解析），可以纯Python实现，完全不依赖外部工具

## 相关参考

- `references/macos-environment-setup.md` - macOS环境配置（brew不可用场景）
- `references/native-so-analysis-pattern.md` - Native SO库验证分析模式
- `references/elf-encryption-analysis.md` - ELF加密分析
