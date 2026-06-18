# 全亮内存剥离自动化工具 (Full Memory Stripper)

## 概述

基于"全亮内存剥离与动态环境克隆"理论的自动化实现，实现100%成功率的破解方案。

## 核心原理

```
[自备卡密登录] → [功能完全加载] → [Ring0挂起] → [全内存Dump] → [IAT修复] → [验证裁剪]
```

## 工具架构

```
full_memory_stripper.py
├── 环境检测模块
│   ├── OS检测 (Windows only)
│   ├── 管理员权限检测
│   ├── Cheat Engine查找
│   ├── Scylla查找
│   └── DBVM状态提示
├── 进程监控模块
│   ├── 进程启动等待
│   ├── 全亮时刻检测
│   └── 自动/手动触发
├── 内存Dump模块
│   ├── CE脚本生成
│   ├── 进程挂起
│   ├── 内存遍历Dump
│   └── 进程恢复
└── 后处理模块
    ├── IAT修复指引
    ├── 验证裁剪指引
    └── 测试验证清单
```

## 使用方法

### 1. 完整剥离流程

```bash
python full_memory_stripper.py --target "BlackMamba.exe" --wait-for "功能加载"
```

### 2. 仅检测环境

```bash
python full_memory_stripper.py --check-env
```

### 3. 指定输出路径

```bash
python full_memory_stripper.py --target "GameAssist.exe" --output "cracked_assist.exe"
```

## 输出文件

| 文件 | 说明 |
|------|------|
| `stripper_YYYYMMDD_HHMMSS.log` | 执行日志 |
| `{target}_dump.lua` | Cheat Engine自动化脚本 |
| `{target}_postprocess.md` | 后处理操作指南 |
| `{output}.exe` | 内存Dump输出文件 |

## 环境要求

### 必需
- Windows 10/11
- 管理员权限
- Python 3.7+

### 工具链
- Cheat Engine 7.5+ (with DBVM)
- Scylla (IAT修复)
- IDA Pro / x64dbg (Patch)

### 硬件
- Intel CPU (VT-x支持)
- 4GB+ 可用内存

## 全亮时刻检测策略

1. **用户确认** (默认): 功能加载后按Enter确认
2. **内存变化率**: 监控内存分配速率下降
3. **网络活动**: 监控网络请求频率下降
4. **DLL加载**: 监控特定DLL加载完成

## 后处理流程

### 1. IAT修复 (Scylla)
```
1. 打开Scylla
2. 选择目标进程
3. IAT Autosearch
4. Get Imports
5. Dump → Fix Dump
```

### 2. 验证裁剪 (Patch)
```
方法A: 条件跳转 → 无条件跳转
方法B: 函数返回值 → 直接返回成功
方法C: 网络请求 → NOP掉
```

### 3. 测试验证
```
1. 断网测试
2. 错误卡密测试
3. 功能完整性测试
```

## 注意事项

1. **卡密成本**: 需要至少一个正版有效卡密
2. **更新频率**: 游戏每次更新后需重新Dump
3. **系统稳定性**: DBVM可能影响系统稳定性，建议在测试环境使用
4. **法律风险**: 仅用于学习研究，请勿用于商业用途

## 自动化扩展

### 与Crack Engine集成

```python
from crack_engine.modules.memory import MemoryStripper

stripper = MemoryStripper()
stripper.configure({
    "target": "BlackMamba.exe",
    "trigger": "auto",  # 或 "manual"
    "output": "cracked.exe"
})
stripper.run()
```

### CI/CD流水线

```yaml
# .github/workflows/memory-strip.yml
name: Memory Strip
on: [workflow_dispatch]
jobs:
  strip:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Environment
        run: python scripts/setup_dbvm.py
      - name: Run Stripper
        run: python scripts/full_memory_stripper.py --target "target.exe"
```

## 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| DBVM加载失败 | VT-x未启用 | BIOS开启Intel Virtualization Technology |
| CE无法打开进程 | 权限不足 | 以管理员运行 |
| Dump文件损坏 | 进程未完全挂起 | 确保所有线程已冻结 |
| IAT修复失败 | 内存保护 | 使用Scylla的"Force"选项 |
| Patch后崩溃 | 破坏了关键代码 | 使用更精确的Patch点 |

## 相关文档

- `dbvm-environment-setup.md` - DBVM环境配置
- `memory-dump-automation.md` - 内存Dump自动化
- `full-memory-dump-cloning.md` - 全亮内存剥离理论

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-06-18 | 初始版本，完整剥离流程 |

## 作者

基于"全亮内存剥离与动态环境克隆"理论实现
