# APK Crack Engine

专业 Android APK 逆向工程工具包 v7.0

## 功能特性

- **智能破解引擎**: 自动选择最优策略 (在线/离线/模拟器/云手机)
- **壳检测**: 支持 12 种加固壳自动识别
- **完整性校验**: 10 项自动校验, 评分 0-100
- **VIP 破解**: Frida 动态注入绕过验证
- **网络绕过**: HTTP 响应篡改
- **Lua 提取**: 内存中自动提取脚本
- **授权管理**: 卡密生成/验证/设备绑定
- **批量处理**: 支持并行破解
- **自进化**: 基于历史数据优化策略

## 安装

```bash
pip install -e .
```

## 快速使用

```bash
# 分析 APK
apk-crack analyze full com.example.app

# 离线破解
apk-crack crack offline com.example.app --apk /path/to/app.apk

# 在线 Frida 破解
apk-crack crack online com.example.app --mode vip

# 自动选择最优模式
apk-crack crack auto com.example.app

# 批量破解
apk-crack batch crack com.pkg1 com.pkg2 com.pkg3 --parallel

# 生成卡密
apk-crack license generate --days 30 --count 5

# 验证卡密
apk-crack license verify ACE-XXXX-XXXX-XXXX --device device_id
```

## 配置

复制 `.env.example` 为 `.env` 并修改配置:

```bash
cp .env.example .env
```

关键配置项:
- `ACE_LOG_LEVEL`: 日志级别
- `ACE_ADB_TIMEOUT`: ADB 超时
- `ACE_FRIDA_TIMEOUT`: Frida 超时
- `ACE_KEYSTORE_PASSWORD`: 密钥库密码 (通过环境变量)

## 项目结构

```
apk-crack-engine/
├── src/apk_crack_engine/
│   ├── cli/          # 命令行接口
│   ├── core/         # 核心模型/配置/日志
│   ├── engine/       # 破解引擎
│   ├── analysis/     # 分析模块
│   ├── patching/     # 修改模块
│   ├── hooking/      # Frida Hook
│   ├── integrity/    # 完整性校验
│   ├── license/      # 授权管理
│   ├── utils/        # 工具函数
│   └── evolution/    # 自进化系统
├── tests/            # 测试
└── docs/             # 文档
```

## 开发

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 格式化
black src/

# Lint
ruff check src/ --fix

# 类型检查
mypy src/apk_crack_engine/

# 测试
pytest -q --tb=short
```

## 生产硬化清单

- [x] 所有 HTTP/ADB 调用带 timeout (默认 10s)
- [x] 指数退避重试 (2~3次)
- [x] loguru 日志轮转 (10MB/5备份)
- [x] 密钥通过环境变量
- [x] 配置热重载 (YAML + Pydantic)
- [x] 异常隔离

## 许可证

MIT
