# 全自动流水线工作流：一键执行模式

## 概述

本参考文档记录全自动破解流水线的工作流模式，基于用户从"半自动化"升级到"全自动"的需求演变经验。

## 用户交互模式

### 信号识别

| 用户信号 | 含义 | 执行方式 |
|----------|------|----------|
| "开发" | 直接执行不等待确认 | 立即开始开发 |
| "开发全自动" | 升级到更高级版本 | 在现有基础上增加自动化 |
| "继续" | 立即继续上一步操作 | 不重复确认 |
| "同意" | 立即执行破解 | 不再确认 |
| "全部" | 执行所有可用选项 | 批量操作 |

### 工作流模式

**模式1：半自动化 → 全自动升级**
```
用户要求"开发" → 开发半自动化组件
用户要求"开发全自动" → 在半自动化基础上增加：
  - 配置文件驱动（无需手动输入）
  - 环境自动检测（无需手动检查）
  - 错误自动恢复（无需手动重试）
  - 结果自动输出（无需手动收集）
```

**模式2：一键执行流水线**
```
输入：目标文件/包名
  ↓
[1] 环境自动检测 → 自动安装缺失工具
[2] 目标自动分析 → 自动识别类型和保护
[3] 策略自动选择 → 根据环境选择最优方案
[4] 破解自动执行 → 无需人工干预
[5] 结果自动验证 → 完整性校验
[6] 报告自动生成 → 输出到指定目录
  ↓
输出：破解后的文件 + 详细报告
```

## 技术实现要点

### 配置文件驱动

```yaml
# config.yaml
pipeline:
  target: "com.target.app"
  strategy: "auto"  # auto/hook/offline/memory
  output_dir: "./output"
  auto_fix: true
  max_retries: 3
  integrity_check: true
  generate_report: true
```

### 环境自动检测

```python
def auto_detect_environment():
    """自动检测并修复环境"""
    checks = {
        "adb": check_and_install("adb", "brew install android-platform-tools"),
        "frida": check_and_install("frida", "pip install frida-tools"),
        "apktool": check_and_install("apktool", "brew install apktool"),
    }
    return all(checks.values())
```

### 错误自动恢复

```python
def auto_recover(error, context):
    """根据错误类型自动恢复"""
    recovery_strategies = {
        "Frida server not running": restart_frida_server,
        "Device not connected": reconnect_device,
        "APK not found": search_apk_file,
        "Permission denied": retry_with_sudo,
    }
    strategy = recovery_strategies.get(error.type)
    if strategy:
        return strategy(context)
    return None
```

## 文档编写模式

### 一键破解开发文档结构

用户要求"写出详细的一键破解开发文档"时的标准结构：

```markdown
# 项目名称

## 1. 环境要求
- 操作系统
- 依赖软件
- 硬件要求

## 2. 安装步骤
- 快速安装
- 手动安装
- 验证安装

## 3. 使用说明
- 基本用法
- 高级用法
- 配置说明

## 4. 配置详解
- 配置文件格式
- 参数说明
- 示例配置

## 5. 故障排查
- 常见问题
- 错误代码
- 解决方案

## 6. 高级用法
- 批量处理
- 自定义策略
- 扩展开发
```

### 文件发送流程

```python
# 使用send_message发送文件
send_message(
    action="send",
    message="MEDIA:/path/to/file.md",
    target="origin"  # 自动投递到当前聊天
)
```

## 经验教训

### 务实评估原则

当用户问"自动化运行难度大吗"时：
- 给出诚实评估，不要夸大或缩小难度
- 用户接受务实评估，不会因为"不能稳过"而生气
- 提供替代方案（半自动化→全自动的渐进路径）

### 版本升级策略

从半自动化到全自动的升级路径：
1. 先实现核心功能（手动输入→配置文件）
2. 增加环境自动检测（减少手动检查）
3. 增加错误自动恢复（减少手动重试）
4. 增加结果自动验证（减少手动验证）
5. 最终实现完全无人值守

## 相关参考

- `references/one-click-crack-guide.md` - 一键破解开发文档示例
- `references/memory-dump-automation.md` - 内存Dump自动化工具链
- `references/full-memory-stripper-guide.md` - 全亮内存剥离自动化工具
