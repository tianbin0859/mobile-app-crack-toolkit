# ELF加密分析与破解技术

## 概述

针对使用自定义加密/压缩的ELF共享库（常见于Android游戏辅助、注入型外挂）的分析与破解技术。

## 文件结构识别

### 典型结构
```
[0x000000 - 0x100000]  代码段（解密逻辑）
[0x100000 - EOF]       加密/压缩的数据段（高熵）
```

### 识别特征
1. **ELF头正常** - 可正常解析程序头表
2. **高熵数据段** - 熵值 > 7.5（加密/压缩特征）
3. **大量XOR指令** - 代码段包含数千个XOR操作
4. **无标准加密常量** - 无AES S-box、RC4初始化等

## 分析流程

### 1. 基础分析
```bash
# 文件类型识别
file target.so
# 输出: ELF 64-bit LSB shared object, ARM aarch64

# ELF头信息
readelf -h target.so
readelf -l target.so  # 程序头表

# 段分析
readelf -S target.so  # 节头表
```

### 2. 熵分析（检测加密段）
```python
import math

def calc_entropy(data):
    entropy = 0
    for x in range(256):
        p_x = float(data.count(bytes([x]))) / len(data)
        if p_x > 0:
            entropy += - p_x * math.log(p_x, 2)
    return entropy

# 分段计算熵值
for i in range(0, len(data), 4096):
    chunk = data[i:i+4096]
    entropy = calc_entropy(chunk)
    if entropy > 7.5:
        print(f"高熵区域: 0x{i:x} - {entropy:.2f}")
```

### 3. 指令模式分析

#### XOR指令检测（ARM64）
```python
# EOR (register): 0xCA000000 - 0xCAFFFFFF
# EOR (immediate): 0xD2000000 - 0xD2FFFFFF

xor_count = 0
for i in range(0, len(code), 4):
    instr = int.from_bytes(code[i:i+4], 'little')
    if (instr & 0xFF000000) == 0xCA000000:
        xor_count += 1
```

#### 密集区域定位
```python
# 滑动窗口检测XOR密集区域
window_size = 256
threshold = 10  # 每窗口至少10个XOR

xor_regions = []
for i in range(0, len(code)-window_size, window_size):
    count = sum(1 for j in range(i, i+window_size, 4) 
                if (int.from_bytes(code[j:j+4], 'little') & 0xFF000000) == 0xCA000000)
    if count >= threshold:
        xor_regions.append((i, count))
```

### 4. 加密算法识别

#### 常见常量检测
```python
constants = {
    b'\x63\x7c\x77\x7b': 'AES S-box',
    b'\x01\x02\x04\x08': 'Power of 2',
    b'\x67\x45\x23\x01': 'TEA/XTEA',
    b'\x9e\x37\x79\xb9': 'SM3/SM4',
    bytes(range(256)): 'RC4 S-box',
}

for const, name in constants.items():
    if const in data:
        print(f"找到: {name}")
```

#### AES指令检测（ARMv8）
```python
# AES指令范围: 0x4E280800 - 0x4E28BF00
aes_count = 0
for i in range(0, len(code), 4):
    instr = int.from_bytes(code[i:i+4], 'little')
    if (instr & 0xFFFF0C00) == 0x4E280800:
        aes_count += 1
```

## 破解策略

### 策略1：静态Patch（条件跳转绕过）

适用于：代码逻辑简单的验证绕过

```python
def patch_conditions(data):
    """将所有条件跳转改为NOP"""
    patched = bytearray(data)
    patches = 0
    
    for i in range(0, len(data), 4):
        instr = int.from_bytes(data[i:i+4], 'little')
        
        # CBZ/CBNZ → NOP
        if (instr & 0xFC000000) == 0xB4000000:
            patched[i:i+4] = b'\x1f\x20\x03\xd5'  # NOP
            patches += 1
            
        # CSEL → MOV
        if (instr & 0xFFE00000) == 0x9A800000:
            patched[i:i+4] = b'\x00\x00\x02\x91'  # ADD X0, X0, #0
            patches += 1
    
    return bytes(patched)
```

### 策略2：XOR暴力破解

适用于：单字节或多字节XOR加密

```python
def try_xor_decrypt(encrypted_data):
    """尝试XOR密钥"""
    common_keys = [0x00, 0xFF, 0xAA, 0x55, 0x12, 0x34, 0x56, 0x78]
    
    for key in common_keys:
        decrypted = bytes([b ^ key for b in encrypted_data[:256]])
        
        # 检查有效头
        if decrypted[:4] == b'\x7fELF':
            return key, 'ELF'
        if decrypted[:2] == b'\x1f\x8b':
            return key, 'GZIP'
        if decrypted[:2] == b'MZ':
            return key, 'PE'
    
    return None, None
```

### 策略3：Frida运行时提取（推荐）

适用于：复杂加密、多阶段解密

```javascript
// Frida脚本：Hook解密函数并Dump内存
function hook_decrypt() {
    // Hook mmap/mprotect捕获解密后内存
    var mmap = Module.findExportByName(null, "mmap");
    Interceptor.attach(mmap, {
        onLeave: function(retval) {
            var addr = ptr(retval.toInt32());
            console.log("[*] mmap: " + addr);
        }
    });
    
    // Hook XOR指令
    var module = Process.findModuleByName("target.so");
    for (var i = 0; i < 0x100000; i += 4) {
        var instr = Memory.readU32(module.base.add(i));
        if ((instr & 0xFF000000) === 0xCA000000) {
            Interceptor.attach(module.base.add(i), {
                onEnter: function(args) {
                    console.log("[*] XOR: " + this.context.x0 + " ^ " + this.context.x1);
                }
            });
        }
    }
    
    // 延迟Dump
    setTimeout(function() {
        var module = Process.findModuleByName("target.so");
        var file = new File("/sdcard/dump.bin", "wb");
        file.write(Memory.readByteArray(module.base, module.size));
        file.close();
        console.log("[*] Dump完成");
    }, 5000);
}
```

### 策略4：服务器地址Patch

适用于：网络验证型ELF

```python
def patch_server_url(data, old_url, new_url):
    """修改硬编码的服务器地址"""
    pos = data.find(old_url.encode())
    if pos != -1:
        # 确保新URL长度不超过原URL
        padded = new_url.ljust(len(old_url), '\x00')
        data = data[:pos] + padded.encode() + data[pos+len(old_url):]
    return data
```

## 实战案例

### 案例：Jojo范围（三角洲行动辅助）

**文件特征：**
- 类型：ELF共享库（ARM64）
- 大小：3.00 MB
- 加密：自定义XOR（41个加密区域）
- 验证：卡密+设备绑定+到期检查

**分析结果：**
```
XOR指令: 17,504个
CBZ/CBNZ: 967个
ADRP: 2,529个
BL调用: 2,773个
```

**破解方法：**
1. 静态Patch：6,725个条件跳转→NOP
2. 生成Frida脚本运行时Hook
3. 绕过所有验证点

### 案例：Bin1.4.sh

**文件特征：**
- 类型：ELF共享库（ARM64）
- 大小：3.45 MB
- 加密：自定义多字节XOR
- 熵值：7.95+（高熵段）

**分析结果：**
```
高熵区域: 多个（0x100000起）
XOR密集区: 41个
未检测到: AES/RC4/标准算法
```

**破解方法：**
1. 静态Patch条件跳转
2. 生成Frida运行时提取脚本
3. 由于多字节XOR，静态解密失败

## 工具链

| 工具 | 用途 |
|------|------|
| `file` | 文件类型识别 |
| `readelf` | ELF结构分析 |
| `objdump` | 反汇编 |
| `strings` | 字符串提取 |
| `frida` | 动态Hook |
| `python3` | 自动化分析 |
| `7z` | 压缩包提取 |
| `gzip` | GZIP解压 |

## 注意事项

1. **多字节XOR** - 单字节暴力破解可能失败，需分析密钥生成逻辑
2. **运行时解密** - 部分ELF在运行时才解密，静态分析有限
3. **反调试** - 注意ptrace/TracerPid检测
4. **代码混淆** - 解密逻辑可能被混淆，需耐心分析

## 相关技能

- `elf-injection-analysis.md` - ELF注入型外挂分析
- `windows-pe-analysis.md` - Windows PE分析
- `pyinstaller-exe-reverse.md` - PyInstaller逆向
