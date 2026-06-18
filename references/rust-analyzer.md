# Rust二进制分析工具

## 概述

Rust二进制分析工具用于识别和分析Rust编译的程序。

## 工具列表

| 工具 | 功能 | 路径 |
|------|------|------|
| `rust_analyzer.py` | Rust特征识别/字符串提取/跳转表分析/IDA脚本生成 | `scripts/rust_analyzer.py` |

## 核心功能

1. **Rust识别**：检测混淆区段、Rust字符串、Panic信息
2. **字符串提取**：提取ASCII/Unicode字符串，搜索认证相关
3. **跳转表分析**：分析枚举跳转表（Rust match/switch）
4. **IDA脚本**：生成IDA Python脚本辅助分析

## 用法

```bash
# 分析Rust二进制
python rust_analyzer.py --exe game.exe --analyze

# 提取字符串并搜索认证相关
python rust_analyzer.py --exe game.exe --extract-strings --search-auth

# 生成IDA脚本
python rust_analyzer.py --exe game.exe --generate-ida-script --output ./ida_script.py
```

## 依赖

- pip install pefile
