# VMP增强分析

## 概述

VMP增强分析工具用于分析和绕过VMProtect保护的程序。

## 工具列表

| 工具 | 功能 | 路径 |
|------|------|------|
| `vmp_enhancer.py` | VM Handler识别、API跟踪、IAT修复、脚本生成 | `scripts/vmp_enhancer.py` |

## 核心功能

1. **VMP检测**：自动检测VMProtect保护特征
2. **VM Handler分析**：识别和分类虚拟指令Handler
3. **API跟踪**：跟踪VirtualAlloc、VirtualProtect等关键API调用
4. **IAT修复**：修复导入地址表，恢复原始API调用
5. **脚本生成**：自动生成Frida和x64dbg分析脚本

## 使用方法

```bash
# 检测VMP保护
python vmp_enhancer.py --exe protected.exe --analyze

# 内存Dump + IAT修复
python vmp_enhancer.py --dump memory.dmp --fix-iat

# 分析VM Handler
python vmp_enhancer.py --dump memory.dmp --analyze-handlers

# 生成分析脚本
python vmp_enhancer.py --exe protected.exe --generate-scripts
```

## 技术细节

### VMP特征检测
- 特征签名：`VMProtect`、`VMP`
- Section名：`.vmp0`、`.vmp1`、`.vmp2`

### VM Handler类型
- PUSH/POP：寄存器操作
- MOV：数据移动
- ADD/SUB：算术运算
- JMP/CALL/RET：控制流

### IAT修复流程
1. 查找IAT位置（通过kernel32.dll字符串定位）
2. 填充常见API地址
3. 保存修复后的Dump文件
