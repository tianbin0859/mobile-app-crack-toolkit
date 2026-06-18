# Lua脚本提取

## 概述

Lua脚本提取工具用于从游戏和应用中提取Lua脚本。

## 工具列表

| 工具 | 功能 | 路径 |
|------|------|------|
| `lua_extractor.py` | Lua字节码提取/反编译/脚本Patch | `scripts/lua_extractor.py` |

## 核心功能

1. **Lua识别**：自动识别Lua字节码和源码
2. **APK提取**：从APK提取Lua文件
3. **二进制提取**：从二进制文件提取Lua字节码
4. **反编译**：反编译Lua字节码为源码
5. **脚本Patch**：修改Lua脚本（Patch验证、解锁功能）

## 使用场景

- 游戏Lua脚本提取
- 应用配置提取
- Lua字节码反编译
- 脚本修改

## 技术栈

- Python 3.8+
- unluac
- zipfile
