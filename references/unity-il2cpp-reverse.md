# Unity IL2CPP逆向工具链

## 概述

Unity IL2CPP逆向工具链用于分析和破解使用IL2CPP编译的Unity游戏。

## 工具列表

| 工具 | 功能 | 路径 |
|------|------|------|
| `il2cpp_dumper.py` | 解析metadata/恢复符号/生成IDA脚本 | `scripts/il2cpp_dumper.py` |
| `unity_method_resolver.py` | 方法名还原/Frida Hook生成/Inspector配置 | `scripts/unity_method_resolver.py` |

## 核心流程

1. **Dump IL2CPP数据**：从游戏内存中提取`global-metadata.dat`和`libil2cpp.so`
2. **解析Metadata**：使用`il2cpp_dumper.py`解析metadata，恢复类名、方法名、字段名
3. **生成脚本**：自动生成IDA/Ghidra脚本辅助静态分析
4. **Hook定位**：使用`unity_method_resolver.py`定位关键方法并生成Frida Hook脚本

## 使用方法

```bash
# 解析metadata
python il2cpp_dumper.py --metadata global-metadata.dat --output ./il2cpp_output

# 生成Frida Hook
python unity_method_resolver.py --symbols il2cpp_symbols.json --target Update --output ./hook
```

## 参考项目

- Perfare/Il2CppDumper (⭐9069)
- djkaty/Il2CppInspector (⭐3011)
- SamboyCoding/Cpp2IL (⭐2443)
