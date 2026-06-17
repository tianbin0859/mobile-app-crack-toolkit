# 内存修改器框架实战指南

## 适用场景
- 单机游戏实时修改（血量、金币、坐标）
- 基址扫描、指针链追踪
- 内存锁定（ freeze value ）
- 类似 Cheat Engine 功能，但自动化

## 核心工具链

| 工具 | 用途 | 平台 |
|------|------|------|
| pymem | Python 内存读写 | Windows |
| ReadWriteMemory | 跨进程内存操作 | Windows |
| scanmem | Linux 内存扫描 | Linux |
| GameConqueror | scanmem GUI | Linux |
| frida | 跨平台内存操作 | All |
| cheat-engine | 参考实现 | Windows |

## 标准流程

### 1. 基础内存扫描（Python）
```python
import pymem
import re

class MemoryScanner:
    def __init__(self, process_name: str):
        self.pm = pymem.Pymem(process_name)
        self.process = self.pm.process_handle
        
    def scan_int(self, value: int, value_type="int"):
        """扫描整数值"""
        results = []
        
        # 遍历所有内存区域
        for mbi in pymem.memory.list_memory_regions(self.process):
            if not mbi.State & pymem.ressources.MEM_COMMIT:
                continue
            if not mbi.Protect & (pymem.ressources.PAGE_READWRITE | pymem.ressources.PAGE_EXECUTE_READWRITE):
                continue
                
            try:
                memory = pymem.memory.read_bytes(self.process, mbi.BaseAddress, mbi.RegionSize)
                
                # 4字节整数扫描
                if value_type == "int":
                    for i in range(0, len(memory) - 4, 4):
                        if int.from_bytes(memory[i:i+4], 'little') == value:
                            results.append(mbi.BaseAddress + i)
                            
            except:
                continue
                
        return results
    
    def scan_float(self, value: float):
        """扫描浮点数"""
        import struct
        target_bytes = struct.pack('<f', value)
        
        results = []
        for mbi in pymem.memory.list_memory_regions(self.process):
            if not mbi.State & pymem.ressources.MEM_COMMIT:
                continue
                
            try:
                memory = pymem.memory.read_bytes(self.process, mbi.BaseAddress, mbi.RegionSize)
                for i in range(len(memory) - 4):
                    if memory[i:i+4] == target_bytes:
                        results.append(mbi.BaseAddress + i)
            except:
                continue
                
        return results
    
    def write_int(self, address: int, value: int):
        """写入整数"""
        pymem.memory.write_int(self.process, address, value)
        
    def write_float(self, address: int, value: float):
        """写入浮点数"""
        import struct
        bytes_value = struct.pack('<f', value)
        pymem.memory.write_bytes(self.process, address, bytes_value, 4)
        
    def freeze_value(self, address: int, value, value_type="int", interval=0.1):
        """锁定数值（后台线程）"""
        import threading
        import time
        
        def _freeze():
            while self._freeze_running:
                if value_type == "int":
                    self.write_int(address, value)
                elif value_type == "float":
                    self.write_float(address, value)
                time.sleep(interval)
                
        self._freeze_running = True
        thread = threading.Thread(target=_freeze, daemon=True)
        thread.start()
        return thread
    
    def unfreeze(self):
        """解除锁定"""
        self._freeze_running = False
```

### 2. 指针链扫描（多级指针）
```python
class PointerChainScanner:
    def __init__(self, pm: pymem.Pymem):
        self.pm = pm
        
    def find_pointer_chain(self, base_address: int, target_address: int, max_depth=5, max_offset=0x2000):
        """
        从基址扫描到目标地址的指针链
        例如：[[base+0x10]+0x20]+0x8 = target
        """
        chains = []
        
        def _scan_recursive(current_addr, depth, current_chain):
            if depth == 0:
                if current_addr == target_address:
                    chains.append(current_chain[:])
                return
                
            # 读取当前地址作为指针
            try:
                ptr = pymem.memory.read_int(self.pm.process_handle, current_addr)
            except:
                return
                
            # 扫描偏移
            for offset in range(0, max_offset, 4):
                try:
                    next_addr = ptr + offset
                    next_ptr = pymem.memory.read_int(self.pm.process_handle, next_addr)
                    
                    current_chain.append(offset)
                    _scan_recursive(next_ptr, depth - 1, current_chain)
                    current_chain.pop()
                    
                except:
                    continue
                    
        # 从基址开始
        base_ptr = pymem.memory.read_int(self.pm.process_handle, base_address)
        _scan_recursive(base_ptr, max_depth, [])
        
        return chains
```

### 3. AOB 扫描（Array of Bytes）
```python
    def aob_scan(self, pattern: str):
        """
        特征码扫描
        pattern: "48 89 5C 24 ?? 48 89 74 24 ?? 57 48 83 EC 20"
        ?? = wildcard
        """
        bytes_pattern = []
        for byte_str in pattern.split():
            if byte_str == "??":
                bytes_pattern.append(None)
            else:
                bytes_pattern.append(int(byte_str, 16))
                
        results = []
        for mbi in pymem.memory.list_memory_regions(self.pm.process_handle):
            if not mbi.State & pymem.ressources.MEM_COMMIT:
                continue
                
            try:
                memory = pymem.memory.read_bytes(self.pm.process_handle, mbi.BaseAddress, mbi.RegionSize)
                
                for i in range(len(memory) - len(bytes_pattern)):
                    match = True
                    for j, byte in enumerate(bytes_pattern):
                        if byte is not None and memory[i+j] != byte:
                            match = False
                            break
                            
                    if match:
                        results.append(mbi.BaseAddress + i)
                        
            except:
                continue
                
        return results
```

### 4. 完整修改器类
```python
class GameModifier:
    def __init__(self, process_name: str):
        self.pm = pymem.Pymem(process_name)
        self.scanner = MemoryScanner(process_name)
        self.pointers = {}
        
    def find_and_lock(self, initial_value, target_value, value_type="int"):
        """
        完整流程：扫描 -> 过滤 -> 修改 -> 锁定
        """
        # 1. 首次扫描
        print(f"[+] 扫描初始值: {initial_value}")
        addresses = self.scanner.scan_int(initial_value, value_type)
        print(f"    找到 {len(addresses)} 个结果")
        
        # 2. 等待值变化，二次扫描
        input("改变游戏中的数值，然后按回车...")
        
        # 3. 过滤
        filtered = []
        for addr in addresses:
            try:
                current = pymem.memory.read_int(self.pm.process_handle, addr)
                if current == target_value:
                    filtered.append(addr)
            except:
                continue
                
        print(f"[+] 过滤后: {len(filtered)} 个结果")
        
        # 4. 修改并锁定
        if filtered:
            target_addr = filtered[0]
            self.scanner.write_int(target_addr, 999999)
            self.scanner.freeze_value(target_addr, 999999, value_type)
            print(f"[+] 已锁定地址: 0x{target_addr:X}")
            return target_addr
            
        return None
```

## 常见问题

### Q: 游戏有反作弊（EAC/BE）？
- 内存扫描对内核级反作弊无效
- 仅适用于单机游戏或无保护游戏
- 考虑用 frida + 反调试绕过

### Q: 数值加密/混淆？
- 搜索 XOR 加密后的值
- 或 Hook 加密/解密函数

### Q: 64位程序？
- 使用 8 字节扫描（long）
- 指针也是 8 字节

## 参考项目
- pymem: https://github.com/srounet/pymem (⭐ 1.2k)
- scanmem: https://github.com/scanmem/scanmem (⭐ 1.8k)
- Cheat Engine: https://github.com/cheat-engine/cheat-engine (⭐ 18k)
