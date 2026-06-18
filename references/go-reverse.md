# Go二进制逆向

## 概述

Go二进制逆向工具用于分析和破解Go编译的程序。

## 工具列表

| 工具 | 功能 | 路径 |
|------|------|------|
| `go_reverse.py` | Go符号表恢复/函数名提取/Goroutine分析 | `scripts/go_reverse.py` |

## 核心功能

1. **Go识别**：检测Go编译特征和版本
2. **符号恢复**：从pclntab恢复函数名
3. **字符串提取**：提取Go字符串和常量
4. **Goroutine分析**：分析协程和Channel
5. **脚本生成**：生成IDA/Ghidra脚本

## 使用场景

- Go编译的后端服务逆向
- Go编写的工具分析
- Go恶意软件分析
- Go程序Patch

## 技术栈

- Python 3.8+
- Go二进制分析
- IDA/Ghidra
