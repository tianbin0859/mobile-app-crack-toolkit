# .NET逆向工具

## 概述

.NET逆向工具用于分析和破解.NET Framework、.NET Core、Unity Mono程序。

## 工具列表

| 工具 | 功能 | 路径 |
|------|------|------|
| `dotnet_reverse.py` | .NET程序识别/IL提取/反编译/Patch | `scripts/dotnet_reverse.py` |

## 核心功能

1. **程序识别**：自动识别.NET版本、Unity Mono、混淆类型
2. **IL提取**：从DLL/EXE提取IL字节码
3. **反编译**：使用ILSpy/dnSpy反编译为C#源码
4. **字节码Patch**：修改IL指令（Patch验证、解锁功能）
5. **重新打包**：修改后重新编译为DLL

## 使用场景

- Unity Mono游戏破解
- .NET桌面程序逆向
- UWP应用分析
- 混淆程序还原

## 技术栈

- Python 3.8+
- pythonnet
- dnlib
- ILSpy/dnSpy
