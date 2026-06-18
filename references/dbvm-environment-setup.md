# DBVM环境检测与配置指南

## 概述

DBVM (Dark Byte Virtual Machine) 是Cheat Engine作者开发的基于Intel VT-x的Type-1.5 Hypervisor，用于在Ring0级别Dump受保护进程的完整内存镜像。

## 环境检测清单

### 硬件要求检测

```python
def check_dbvm_hardware():
    """检测DBVM硬件兼容性"""
    checks = {
        "cpu_vendor": check_cpu_vendor(),  # Intel必需
        "vmx_support": check_vmx_support(),  # VT-x必需
        "ept_support": check_ept_support(),  # EPT增强
        "unlocked_msr": check_msr_unlock(),  # MSR 0x3A解锁
        "memory": check_memory(4),  # 4GB+推荐
    }
    return checks
```

### 软件环境检测

```python
def check_dbvm_software():
    """检测DBVM软件环境"""
    checks = {
        "cheat_engine": check_ce_installed(),  # Cheat Engine 7.5+
        "dbvm_loaded": check_dbvm_loaded(),  # DBVM是否已加载
        "driver_loaded": check_dbvm_driver(),  # DBVM驱动状态
        "windows_version": check_win_version(),  # Win10/11
    }
    return checks
```

## 自动配置流程

```
检测硬件兼容性
    ↓
检测软件环境
    ↓
加载DBVM驱动
    ↓
验证DBVM状态
    ↓
准备内存Dump
```

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| VT-x未启用 | BIOS设置 | 进入BIOS开启Intel Virtualization Technology |
| DBVM加载失败 | 安全软件拦截 | 关闭Windows Defender/杀毒软件 |
| 蓝屏 | 驱动冲突 | 检查其他Hypervisor (Hyper-V/VMware) |
| 内存不足 | 系统内存不够 | 关闭其他程序，确保4GB+可用 |

## 检测脚本

```python
#!/usr/bin/env python3
"""DBVM环境检测脚本"""
import subprocess
import sys

def check_vmx():
    """检测VT-x支持"""
    try:
        result = subprocess.run(
            ['reg', 'query', 'HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment'],
            capture_output=True, text=True
        )
        return "PROCESSOR_IDENTIFIER" in result.stdout
    except:
        return False

def main():
    print("[*] DBVM环境检测")
    
    # 检测CPU
    print("[1] 检测CPU厂商...")
    if check_vmx():
        print("    ✅ Intel CPU detected")
    else:
        print("    ❌ Non-Intel CPU (DBVM requires Intel)")
        return False
    
    print("[2] 检测VT-x...")
    # 需要Windows API调用
    print("    ⚠️  请手动检查BIOS中Intel Virtualization Technology")
    
    print("[3] 检测Cheat Engine...")
    # 检查注册表或默认路径
    print("    ⚠️  请确保Cheat Engine 7.5+已安装")
    
    print("\n[*] 检测完成，请根据提示配置环境")
    return True

if __name__ == "__main__":
    main()
```

## 与Cheat Engine集成

```lua
-- DBVM内存Dump Lua脚本
function dbvm_dump_process(pid, output_path)
    -- 使用DBVM的物理内存读取功能
    local mem = getPhysicalMemoryDBVM()
    
    -- 遍历进程内存区域
    local regions = getMemoryRegions(pid)
    for _, region in ipairs(regions) do
        if region.isReadable then
            local data = readPhysicalMemory(region.start, region.size)
            writeToFile(output_path, data)
        end
    end
end
```

## 注意事项

1. **管理员权限**：DBVM需要以管理员权限运行
2. **安全软件**：需要关闭Windows Defender实时保护
3. **驱动签名**：测试模式下需要禁用驱动签名强制
4. **系统稳定性**：DBVM加载后系统稳定性可能受影响，建议在测试环境使用

## 相关工具

- Cheat Engine 7.5+ (with DBVM)
- Scylla (IAT修复)
- IDA Pro (分析Dump文件)
- x64dbg (辅助调试)
