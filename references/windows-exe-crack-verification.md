# Windows EXE 破解完整性验证指南

## 使用场景

Use when: 1) 用户要求检查破解是否完整 2) 用户要求验证DLL补丁是否生效 3) DLL补丁后需要确认修改成功 4) 破解验证失败需要诊断修复 5) 需要确认备份与当前文件差异

## 核心流程

### 1. 快速验证（3步检查）

```bash
# Step 1: 检查备份目录是否存在
ls -la backup/

# Step 2: 比较文件大小（初步判断）
ls -la backup/HAP_SDK64.dll HAP_SDK64.dll
ls -la backup/SecureEngineSDK64.dll SecureEngineSDK64.dll
# 如果大小完全相同 → 补丁可能未应用

# Step 3: 字节级差异验证
python3 -c "
import sys, os
sys.path.insert(0, os.path.expanduser('~/Library/Python/3.9/lib/python/site-packages'))
import pefile

def verify_patch(dll_path, backup_path, expected_diffs):
    with open(dll_path, 'rb') as f:
        current = f.read()
    with open(backup_path, 'rb') as f:
        original = f.read()
    
    diffs = []
    for i, (c, o) in enumerate(zip(current, original)):
        if c != o:
            diffs.append((hex(i), hex(o), hex(c)))
    
    print(f'总差异字节数: {len(diffs)}')
    for addr, old, new in diffs[:10]:
        print(f'  {addr}: {old} -> {new}')
    
    # 验证预期差异
    for desc, addr, expected in expected_diffs:
        actual = current[addr]
        if actual == expected:
            print(f'  [OK] {desc}')
        else:
            print(f'  [FAIL] {desc}: expected {hex(expected)}, got {hex(actual)}')
    
    return len(diffs)

# HAP_SDK64.dll: 3个函数入口改为 mov eax, 1; ret
verify_patch('HAP_SDK64.dll', 'backup/HAP_SDK64.dll', [
    ('HAP_Login', 0x1060, 0xB8),
    ('HAP_LoginIntegrity', 0x1070, 0xB8),
    ('HAP_Heartbeat', 0x1080, 0xB8),
])

# SecureEngineSDK64.dll: SECheckRegistration改为 xor eax, eax; ret
verify_patch('SecureEngineSDK64.dll', 'backup/SecureEngineSDK64.dll', [
    ('SECheckRegistration', 0x1000, 0x33),
])
"
```

### 2. 完整验证报告生成

```python
#!/usr/bin/env python3
"""Windows EXE Crack Verification Report Generator"""
import sys, os, hashlib
sys.path.insert(0, os.path.expanduser('~/Library/Python/3.9/lib/python/site-packages'))
import pefile

def generate_verification_report(target_dir):
    report = []
    report.append("=" * 60)
    report.append("Windows EXE 破解完整性验证报告")
    report.append("=" * 60)
    
    # 检查备份
    backup_dir = os.path.join(target_dir, "backup")
    if not os.path.exists(backup_dir):
        report.append("[FAIL] 备份目录不存在!")
        return "\n".join(report)
    
    # 验证每个DLL
    dlls = ["HAP_SDK64.dll", "SecureEngineSDK64.dll"]
    for dll_name in dlls:
        current_path = os.path.join(target_dir, dll_name)
        backup_path = os.path.join(backup_dir, dll_name)
        
        if not os.path.exists(current_path):
            report.append(f"[WARN] {dll_name} 不存在")
            continue
        if not os.path.exists(backup_path):
            report.append(f"[WARN] {dll_name} 备份不存在")
            continue
        
        # 计算哈希
        with open(current_path, 'rb') as f:
            current_hash = hashlib.sha256(f.read()).hexdigest()[:16]
        with open(backup_path, 'rb') as f:
            backup_hash = hashlib.sha256(f.read()).hexdigest()[:16]
        
        report.append(f"\n[{dll_name}]")
        report.append(f"  当前文件: {current_hash}")
        report.append(f"  备份文件: {backup_hash}")
        
        if current_hash == backup_hash:
            report.append(f"  [FAIL] 文件与备份完全相同 - 补丁未应用!")
        else:
            report.append(f"  [OK] 文件已修改")
    
    report.append("\n" + "=" * 60)
    report.append("验证完成")
    return "\n".join(report)

if __name__ == "__main__":
    print(generate_verification_report("."))
```

## 常见陷阱

### 陷阱1: pefile模块安装路径问题

**现象**: `python3 -c "import pefile"` 报错 `ModuleNotFoundError`

**原因**: macOS系统Python的 `--user` 安装路径不在 `sys.path` 中

**解决**:
```python
import sys, os
sys.path.insert(0, os.path.expanduser('~/Library/Python/3.9/lib/python/site-packages'))
import pefile
```

**预防**: 所有涉及pefile的脚本必须包含此路径插入

### 陷阱2: DLL被错误破坏

**现象**: 所有函数入口变成 `c3c3c3c3c3` (连续ret指令)

**原因**: 错误的补丁脚本写入了过多字节

**修复**: 从备份恢复，重新应用正确补丁
```bash
cp backup/SecureEngineSDK64.dll SecureEngineSDK64.dll
cp backup/HAP_SDK64.dll HAP_SDK64.dll
```

### 陷阱3: 补丁后未验证

**现象**: 用户报告破解无效，但补丁已"执行"

**原因**: 补丁脚本执行了但写入位置错误

**解决**: 必须执行字节级验证，不能仅依赖脚本输出

## 补丁字节规范

### HAP_SDK64.dll 标准补丁

```python
# 3个验证函数入口改为: mov eax, 1; ret
# 字节序列: B8 01 00 00 00 C3 (6字节)
# 但通常只改前3-5字节即可
PATCH_HAP = {
    "HAP_Login":        {"offset": 0x1060, "bytes": b'\xB8\x01\x00\x00\x00\xC3'},
    "HAP_LoginIntegrity": {"offset": 0x1070, "bytes": b'\xB8\x01\x00\x00\x00\xC3'},
    "HAP_Heartbeat":    {"offset": 0x1080, "bytes": b'\xB8\x01\x00\x00\x00\xC3'},
}
```

### SecureEngineSDK64.dll 标准补丁

```python
# SECheckRegistration改为: xor eax, eax; ret
# 字节序列: 33 C0 C3 (3字节)
PATCH_SECURE = {
    "SECheckRegistration": {"offset": 0x1000, "bytes": b'\x33\xC0\xC3'},
}
```

## 验证触发条件

- 用户说"检查破解" → 执行完整验证
- 用户说"验证" → 执行快速验证
- 用户说"是否完整" → 生成验证报告
- 补丁执行后 → 自动验证（强制）

## 版本历史

| 版本 | 日期 | 更新 |
|------|------|------|
| v1.0 | 2026-06-17 | 初始版本：pefile路径陷阱、DLL破坏修复、字节级验证 |
