# Java字节码逆向

## 概述

Java字节码逆向工具用于分析和破解Java程序（JAR、DEX、APK）。

## 工具列表

| 工具 | 功能 | 路径 |
|------|------|------|
| `java_bytecode_reverse.py` | JAR/DEX分析/类提取/字节码Patch | `scripts/java_bytecode_reverse.py` |

## 核心功能

1. **程序识别**：自动识别JAR/APK/DEX格式
2. **类提取**：提取所有类名和方法名
3. **反编译**：反编译字节码为Java源码
4. **字节码Patch**：修改方法返回固定值
5. **重新打包**：修改后重新打包JAR

## 使用场景

- Java桌面程序破解
- Android APK分析
- DEX文件逆向
- 字节码Patch

## 技术栈

- Python 3.8+
- javalang
- zipfile
