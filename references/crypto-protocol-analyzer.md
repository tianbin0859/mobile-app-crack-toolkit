# 加密协议自动分析工具

## 概述

加密协议自动分析工具用于自动识别加密算法、尝试解密、分析协议结构。

## 工具列表

| 工具 | 功能 | 路径 |
|------|------|------|
| `crypto_protocol_analyzer.py` | 算法识别/密钥派生/暴力破解/协议分析/响应生成 | `scripts/crypto_protocol_analyzer.py` |

## 核心功能

1. **算法检测**：自动识别AES/ChaCha20/XOR等加密算法
2. **密钥派生**：从基础密钥派生多种可能密钥（MD5/SHA1/SHA256/Base64）
3. **暴力破解**：自动尝试AES-ECB/CBC/CTR和XOR多种组合
4. **协议分析**：分析帧大小、字段偏移、固定模式
5. **响应生成**：生成伪造成功/错误响应

## 用法

```bash
# 分析加密协议
python crypto_protocol_analyzer.py --data capture.bin --frame-size 384 --analyze

# 自动尝试解密
python crypto_protocol_analyzer.py --data capture.bin --key "FDTls6gNyx7klaeNPt04k1TNO5la7bI2" --auto-brute

# 生成伪造响应
python crypto_protocol_analyzer.py --frame-size 384 --generate-response --output response.bin
```

## 依赖

- pip install pycryptodome
