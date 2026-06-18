# 自动化Patch工具

## 概述

自动化Patch工具用于基于偏移参考自动修改二进制文件。

## 工具列表

| 工具 | 功能 | 路径 |
|------|------|------|
| `auto_patcher.py` | 自动Patch/条件跳转修改/返回值修改/备份恢复 | `scripts/auto_patcher.py` |

## 核心功能

1. **自动Patch**：基于偏移参考自动Patch跳转
2. **条件跳转修改**：JE→JMP, JNE→JMP
3. **返回值修改**：RET 0, RET 1
4. **备份恢复**：自动备份原始文件，支持恢复
5. **验证**：验证Patch有效性

## 用法

```bash
# 自动Patch（基于偏移参考）
python auto_patcher.py --exe game.exe --offset 0x123456 --patch-type jmp --backup

# 修改条件跳转
python auto_patcher.py --exe game.exe --offset 0x123456 --patch-type je2jmp --backup

# 恢复备份
python auto_patcher.py --exe game.exe --restore
```

## Patch类型

- `jmp`：短跳转
- `je2jmp`：JE→JMP
- `jne2jmp`：JNE→JMP
- `ret0`：RET 0
- `ret1`：RET 1
- `nop`：NOP填充
