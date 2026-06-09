# 壳识别与脱壳指南

## 一、壳识别方法

### 1.1 文件特征识别

```bash
# 查看APK内的SO文件
unzip -l target.apk | grep \\.so

# 查看assets目录
unzip -l target.apk | grep assets/

# 查看DEX文件
unzip -l target.apk | grep \\.dex
```

### 1.2 使用ApkScan-PKID

```bash
python ApkScan-PKID.py target.apk
```

### 1.3 手动识别特征

| 壳类型 | 特征文件/字符串 | 识别方法 |
|--------|----------------|----------|
| 360加固 | libjiagu.so | 文件名匹配 |
| 梆梆加固 | libsecexe.so | 文件名匹配 |
| 爱加密 | libexec.so | 文件名匹配 |
| 腾讯乐固 | libshell.so | 文件名匹配 |
| 百度加固 | libbaiduprotect.so | 文件名匹配 |
| 网易易盾 | libnesec.so | 文件名匹配 |
| VMP保护 | 无特征SO | DEX头异常 |

## 二、脱壳方法

### 2.1 FRIDA-DEXDump（推荐）

```bash
# 安装
pip install frida-dexdump

# 使用
frida-dexdump -U com.target.app

# 输出到指定目录
frida-dexdump -U -o output/ com.target.app
```

**原理：**
- 通过Frida Hook ART虚拟机的类加载函数
- 在类加载到内存时Dump DEX数据
- 自动修复DEX头

### 2.2 BlackDex（免Root）

```bash
# 安装BlackDex APK
adb install BlackDex.apk

# 在APP中选择目标应用
# 自动在虚拟空间中运行并Dump
```

**原理：**
- 基于Android虚拟化技术
- 在虚拟空间中运行目标APP
- Hook类加载过程Dump DEX

### 2.3 Youpk（ART脱壳机）

```bash
# 需要AOSP源码环境
# 编译修改后的ART

# 刷入设备
# 自动在类加载时Dump
```

**原理：**
- 修改Android Runtime源码
- 在DexFile加载时保存原始数据
- 支持大多数加固壳

### 2.4 手动Frida脱壳

```javascript
// Hook DexFile加载
Java.perform(function() {
    // 方法1: Hook openDexFile
    var openDexFile = Module.findExportByName(null, 
        "_ZN3art7DexFile10OpenMemoryEPKhjRKNSt3__112basic_stringIcNS3_11char_traitsIcEENS3_9allocatorIcEEEEjPNS_6MemMapEPKNS_10OatDexFileE");
    
    if (openDexFile) {
        Interceptor.attach(openDexFile, {
            onEnter: function(args) {
                var begin = args[1];
                var size = args[2].toInt32();
                
                console.log("[*] DexFile loaded:", size, "bytes");
                
                // 保存DEX
                var file = new File("/sdcard/dump_" + size + ".dex", "wb");
                file.write(Memory.readByteArray(begin, size));
                file.close();
            }
        });
    }
    
    // 方法2: Hook InMemoryClassLoader
    try {
        var InMemoryClassLoader = Java.use("dalvik.system.InMemoryClassLoader");
        InMemoryClassLoader.$init.overload('java.nio.ByteBuffer', 'java.lang.ClassLoader').implementation = function(buffer, parent) {
            console.log("[*] InMemoryClassLoader created");
            
            // 提取DEX数据
            var dexData = Java.array('byte', buffer.array());
            var file = new File("/sdcard/dump_inmemory.dex", "wb");
            file.write(dexData);
            file.close();
            
            return this.$init(buffer, parent);
        };
    } catch(e) {}
});
```

### 2.5 SO脱壳

```bash
# 1. 找到SO加载地址
cat /proc/<pid>/maps | grep libtarget.so

# 2. 使用gdb Dump
gdb -p <pid>
(gdb) dump memory libtarget_dump.so 0x<start> 0x<end>

# 3. 修复ELF头
python fix_elf.py libtarget_dump.so
```

```python
# fix_elf.py
import struct
import sys

def fix_elf(path):
    with open(path, 'rb') as f:
        data = bytearray(f.read())
    
    # 修复ELF头
    if data[:4] != b'\x7fELF':
        print("[!] Invalid ELF header")
        return
    
    # 修复Program Headers
    # 需要根据实际内存布局调整
    
    with open(path + '.fixed', 'wb') as f:
        f.write(data)
    
    print("[+] Fixed ELF saved")

if __name__ == '__main__':
    fix_elf(sys.argv[1])
```

## 三、VMP脱壳

### 3.1 VMP原理

VMP（Virtual Machine Protect）将原始指令转换为自定义虚拟指令：

```
原始指令: mov eax, 1
           add eax, 2
           
VMP指令:  0x01 0x00 0x01  (LOAD 1)
          0x02 0x00 0x02  (ADD 2)
          
VM解释器: 读取opcode -> 查表 -> 执行对应操作
```

### 3.2 VMP Trace方法

```javascript
// 找到VM解释器
function findVMInterpreter() {
    var modules = Process.enumerateModules();
    
    for (var i = 0; i < modules.length; i++) {
        var module = modules[i];
        
        // 搜索VM特征
        var pattern = "vm_";
        var exports = Module.enumerateExports(module.name);
        
        for (var j = 0; j < exports.length; j++) {
            if (exports[j].name.indexOf("vm_") !== -1 ||
                exports[j].name.indexOf("execute") !== -1) {
                console.log("[*] Possible VM:", module.name, exports[j].name);
            }
        }
    }
}

// Trace VM执行
function traceVM(vmAddr) {
    Interceptor.attach(vmAddr, {
        onEnter: function(args) {
            var pc = args[0];  // VM PC
            var opcode = Memory.readU8(pc);
            
            // 记录opcode
            console.log("VM OP:", opcode.toString(16));
            
            // 记录寄存器状态
            // 需要根据具体VM结构读取
        }
    });
}
```

### 3.3 指令还原

通过大量Trace数据，建立opcode到原始指令的映射：

```python
# 分析VM Trace日志
def analyze_vm_trace(log_file):
    opcode_map = {}
    
    with open(log_file, 'r') as f:
        for line in f:
            if 'VM OP:' in line:
                opcode = line.split(':')[1].strip()
                
                # 关联上下文
                # 找到对应的原始指令效果
                
                if opcode not in opcode_map:
                    opcode_map[opcode] = []
                
                opcode_map[opcode].append(context)
    
    # 输出映射表
    for opcode, contexts in opcode_map.items():
        print(f"Opcode {opcode}: {len(contexts)} samples")
        # 分析共同特征
```

## 四、脱壳验证

### 4.1 检查DEX完整性

```bash
# 使用dexdump检查
dexdump -d classes.dex | head -50

# 使用baksmali
baksmali d classes.dex -o smali_out

# 检查是否能反编译
jadx -d jadx_out classes.dex
```

### 4.2 修复损坏的DEX

```python
# dex_fix.py
import struct

def fix_dex_header(data):
    # 修复DEX头
    if data[:4] != b'dex\n':
        print("[!] Invalid DEX header")
        return None
    
    # 修复checksum
    # 修复signature
    
    return data

def fix_dex_strings(data):
    # 修复字符串表
    # 处理加密字符串
    pass
```

## 五、常见问题

### 5.1 脱壳失败

| 问题 | 原因 | 解决 |
|------|------|------|
| 空DEX | 加密DEX未加载 | 等待APP运行后再Dump |
| 损坏DEX | Dump时机不对 | 在解密完成后Hook |
| 不完整 | 多DEX应用 | 分别Dump每个DEX |
| 无法反编译 | 代码混淆 | 使用反混淆工具 |

### 5.2 反调试绕过

```javascript
// Hook ptrace
var ptrace = Module.findExportByName(null, "ptrace");
Interceptor.attach(ptrace, {
    onEnter: function(args) {
        var request = args[0].toInt32();
        if (request === 0) {  // PTRACE_TRACEME
            console.log("[*] PTRACE_TRACEME blocked");
            args[0] = ptr(0x1);  // 改为无效请求
        }
    }
});

// Hook fork
var fork = Module.findExportByName(null, "fork");
Interceptor.attach(fork, {
    onLeave: function(retval) {
        console.log("[*] fork returned:", retval);
    }
});
```
