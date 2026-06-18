# 网络协议模糊测试工具

## 概述

网络协议模糊测试工具用于自动测试协议健壮性，发现异常响应。

## 工具列表

| 工具 | 功能 | 路径 |
|------|------|------|
| `protocol_fuzzer.py` | 自动生成变异帧/多种变异策略/异常检测/测试报告 | `scripts/protocol_fuzzer.py` |

## 核心功能

1. **变异策略**：位翻转、字节翻转、算术变异、有趣值、完全随机、长度变异、校验和变异
2. **自动测试**：发送变异帧并接收响应
3. **异常检测**：检测非预期响应（如错误码变化）
4. **测试报告**：生成Markdown格式的测试报告

## 用法

```bash
# 基本模糊测试
python protocol_fuzzer.py --target 127.0.0.1:8080 --frame-size 384 --count 100

# 基于捕获数据变异
python protocol_fuzzer.py --target 127.0.0.1:8080 --base-frame capture.bin --count 50

# 自定义变异策略
python protocol_fuzzer.py --target 127.0.0.1:8080 --strategy bitflip --count 200
```

## 变异策略

- `bitflip`：位翻转
- `byteflip`：字节翻转
- `arithmetic`：算术变异
- `interesting`：有趣值
- `random`：完全随机
- `length`：长度变异
- `checksum`：校验和变异
