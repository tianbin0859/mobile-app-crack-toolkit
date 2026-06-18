# Python打包程序逆向

## 概述

Python打包程序逆向工具用于提取和分析PyInstaller、UPX等打包的Python程序。

## 工具列表

| 工具 | 功能 | 路径 |
|------|------|------|
| `pyinstaller_extractor.py` | PyInstaller/UPX检测提取、pyc反编译、资源提取 | `scripts/pyinstaller_extractor.py` |

## 核心功能

1. **自动检测**：识别PyInstaller、UPX等打包类型
2. **提取pyc**：从打包文件中提取Python字节码
3. **反编译**：将pyc反编译为Python源码（支持uncompyle6和内置反汇编）
4. **资源提取**：提取图片、配置等资源文件
5. **导入分析**：分析程序依赖的模块

## 使用方法

```bash
# 自动分析并提取
python pyinstaller_extractor.py --exe target.exe --output ./extracted

# 反编译pyc
python pyinstaller_extractor.py --pyc app.pyc --decompile

# UPX脱壳
python pyinstaller_extractor.py --upx packed.exe --output unpacked.exe

# 批量处理
python pyinstaller_extractor.py --batch ./packed/ --output ./extracted/
```

## 依赖安装

```bash
pip install pyinstxtractor upx-unpacker uncompyle6
```
