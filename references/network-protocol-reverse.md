# 网络协议逆向

## 概述

网络协议逆向工具用于分析和破解应用的网络通信协议。

## 工具列表

| 工具 | 功能 | 路径 |
|------|------|------|
| `network_protocol_reverse.py` | 协议识别/签名分析/Frida Hook生成 | `scripts/network_protocol_reverse.py` |

## 核心功能

1. **协议识别**：自动识别HTTP/HTTPS/WebSocket/Protobuf/自定义二进制
2. **流量分析**：解析PCAP流量文件
3. **签名分析**：检测MD5/SHA1/HMAC/mTOP等签名算法
4. **Hook生成**：生成Frida脚本拦截网络请求
5. **请求重放**：重放和伪造网络请求

## 使用场景

- API接口逆向
- 签名算法破解
- 请求伪造
- 协议分析

## 技术栈

- Python 3.8+
- scapy
- requests
- Frida
