# 一键破解开发文档

## 项目概述

**一键破解系统**是基于"全亮内存剥离与动态环境克隆"理论的全自动化实现，实现100%成功率的破解方案。

### 核心原理

```
[自备卡密登录] → [功能完全加载] → [Ring0挂起] → [全内存Dump] → [IAT修复] → [验证裁剪] → [免费使用]
```

### 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    一键破解系统 v1.0                        │
├─────────────────────────────────────────────────────────┤
│  核心组件                                                │
│  ├── auto_crack_pipeline.py      主控流水线              │
│  ├── full_bright_detector.lua    CE全亮检测插件          │
│  ├── scylla_auto_fix.py          Scylla IAT自动修复      │
│  └── ida_auto_patch.py           IDA自动验证裁剪         │
├─────────────────────────────────────────────────────────┤
│  辅助工具                                                │
│  ├── full_memory_stripper.py     全亮内存剥离工具        │
│  └── memory_dump_automation.py   内存Dump自动化          │
├─────────────────────────────────────────────────────────┤
│  参考文档                                                │
│  ├── dbvm-environment-setup.md   DBVM环境配置            │
│  ├── memory-dump-automation.md   内存Dump工具链          │
│  └── full-memory-stripper-guide.md 剥离工具指南            │
└─────────────────────────────────────────────────────────┘
```

---

## 环境要求

### 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | Intel i5 / AMD Ryzen 5 | Intel i7 / AMD Ryzen 7 |
| 内存 | 8GB | 16GB+ |
| 硬盘 | 50GB 可用空间 | 100GB SSD |
| 虚拟化 | 支持 Intel VT-x / AMD-V | 必须支持（DBVM需要） |

### 软件要求

| 软件 | 版本 | 用途 | 下载地址 |
|------|------|------|---------|
| Windows | 10/11 64位 | 主系统 | - |
| Python | 3.8+ | 自动化脚本 | python.org |
| Cheat Engine | 7.4+ | 内存扫描与Dump | cheatengine.org |
| Scylla | x64 | IAT修复 | github.com/NtQuery/Scylla |
| IDA Pro | 7.6+ | 反汇编与Patch | hex-rays.com |
| DBVM | 最新版 | 内核调试环境 | github.com/DarkByte7/DBVM |

### Python依赖

```bash
pip install psutil requests colorama
```

---

## 安装配置

### 步骤1：安装Python依赖

```bash
pip install psutil requests colorama
```

### 步骤2：安装Cheat Engine

1. 下载 Cheat Engine 7.4+ 从官网
2. 安装到默认路径 `C:\Tools\CheatEngine`
3. 验证安装：打开CE，检查版本

### 步骤3：安装Scylla

1. 下载 Scylla x64 从 GitHub
2. 解压到 `C:\Tools\Scylla`
3. 验证安装：运行 `Scylla_x64.exe`

### 步骤4：安装IDA Pro

1. 安装 IDA Pro 7.6+
2. 安装到默认路径 `C:\Tools\IDA`
3. 验证安装：运行 `ida64.exe`

### 步骤5：配置DBVM（可选但推荐）

1. 进入BIOS开启 Intel VT-x / AMD-V
2. 关闭Windows Defender内核保护
3. 下载并配置DBVM驱动
4. 验证：运行DBVM测试程序

### 步骤6：配置一键破解系统

```bash
# 生成配置文件模板
python auto_crack_pipeline.py --generate-config
```

编辑生成的 `auto_crack_config.json`：

```json
{
  "target": {
    "process_name": "BlackMamba.exe",
    "window_title": "黑曼巴",
    "full_bright_indicators": {
      "memory_stable_threshold": 1048576,
      "stable_count": 3,
      "check_interval": 1000,
      "min_runtime": 10
    }
  },
  "paths": {
    "ce_dir": "C:\\Tools\\CheatEngine",
    "scylla_dir": "C:\\Tools\\Scylla",
    "ida_dir": "C:\\Tools\\IDA",
    "output_dir": "./output",
    "temp_dir": "./temp"
  },
  "pipeline": {
    "auto_dump": true,
    "auto_fix_iat": true,
    "auto_patch": true,
    "keep_temp_files": false
  }
}
```

---

## 使用说明

### 快速开始（一键执行）

```bash
# 完整全自动流水线
python auto_crack_pipeline.py --config auto_crack_config.json
```

### 分阶段执行（推荐调试）

#### 阶段1：监控目标进程

```bash
python auto_crack_pipeline.py --step monitor --target "BlackMamba.exe"
```

**预期输出**：
```
[*] 阶段1: 启动全亮监控...
    监控配置: ./temp/monitor_config.json
    监控线程启动...
    目标进程找到: PID 12345
    内存稳定 1/3
    内存稳定 2/3
    内存稳定 3/3
    全亮信号已发送
```

#### 阶段2：内存Dump

```bash
python auto_crack_pipeline.py --step dump --target "BlackMamba.exe"
```

**预期输出**：
```
[*] 阶段2: 执行内存Dump...
    目标PID: 12345
    输出文件: ./output/dump_12345_20240115_143022.exe
    挂起进程...
    读取内存...
    进程已恢复
    ✅ Dump标记已创建: ./output/dump_12345_20240115_143022.exe
```

#### 阶段3：IAT修复

```bash
python auto_crack_pipeline.py --step fix --dump "./output/dump_12345_20240115_143022.exe"
```

**预期输出**：
```
[*] 阶段3: 执行IAT修复...
    调用Scylla修复...
    输入: ./output/dump_12345_20240115_143022.exe
    输出: ./output/dump_12345_20240115_143022_fixed.exe
    ✅ IAT修复完成: ./output/dump_12345_20240115_143022_fixed.exe
```

#### 阶段4：验证裁剪

```bash
python auto_crack_pipeline.py --step patch --input "./output/dump_12345_20240115_143022_fixed.exe"
```

**预期输出**：
```
[*] 阶段4: 执行验证裁剪...
    调用IDA Patch...
    输入: ./output/dump_12345_20240115_143022_fixed.exe
    输出: ./output/dump_12345_20240115_143022_cracked.exe
    ✅ 验证裁剪完成: ./output/dump_12345_20240115_143022_cracked.exe
```

### 使用CE插件（高级）

1. 将 `full_bright_detector.lua` 复制到CE的 `autorun` 目录
2. 启动目标程序
3. 在CE菜单中选择：全亮检测 → 开始监控
4. 等待自动Dump完成

---

## 配置详解

### 目标配置 (`target`)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `process_name` | string | "BlackMamba.exe" | 目标进程名 |
| `window_title` | string | "" | 窗口标题（辅助检测） |
| `full_bright_indicators.memory_stable_threshold` | int | 1048576 | 内存稳定阈值（字节） |
| `full_bright_indicators.stable_count` | int | 3 | 连续稳定次数 |
| `full_bright_indicators.check_interval` | int | 1000 | 检测间隔（毫秒） |
| `full_bright_indicators.min_runtime` | int | 10 | 最小运行时间（秒） |

### 路径配置 (`paths`)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ce_dir` | string | "C:\\Tools\\CheatEngine" | Cheat Engine目录 |
| `scylla_dir` | string | "C:\\Tools\\Scylla" | Scylla目录 |
| `ida_dir` | string | "C:\\Tools\\IDA" | IDA Pro目录 |
| `output_dir` | string | "./output" | 输出目录 |
| `temp_dir` | string | "./temp" | 临时目录 |

### 流水线配置 (`pipeline`)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `auto_dump` | bool | true | 自动执行内存Dump |
| `auto_fix_iat` | bool | true | 自动修复IAT |
| `auto_patch` | bool | true | 自动裁剪验证 |
| `keep_temp_files` | bool | false | 保留临时文件 |
| `timeout.monitor` | int | 300 | 监控超时（秒） |
| `timeout.dump` | int | 60 | Dump超时（秒） |
| `timeout.fix` | int | 120 | 修复超时（秒） |
| `timeout.patch` | int | 60 | Patch超时（秒） |

### 通知配置 (`notifications`)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `sound` | bool | true | 完成时播放提示音 |
| `desktop` | bool | true | 桌面通知 |
| `webhook` | string | null | Webhook URL |

---

## 故障排查

### 问题1：目标进程未找到

**症状**：
```
[!] 目标进程未运行: BlackMamba.exe
```

**解决方案**：
1. 确认目标程序已启动
2. 检查进程名是否正确（区分大小写）
3. 使用任务管理器查看实际进程名

### 问题2：Cheat Engine未找到

**症状**：
```
[!] Cheat Engine未找到: C:	ools
cheatengine
```

**解决方案**：
1. 确认CE安装路径
2. 修改配置文件中的 `ce_dir`
3. 重新运行环境检测

### 问题3：内存Dump失败

**症状**：
```
[!] Dump失败: [Error 5] Access is denied
```

**解决方案**：
1. 以管理员身份运行Python
2. 关闭杀毒软件实时保护
3. 使用DBVM内核模式

### 问题4：IAT修复失败

**症状**：
```
[!] IAT修复失败: Scylla returned non-zero exit code
```

**解决方案**：
1. 确认目标进程仍在运行
2. 手动运行Scylla检查错误
3. 尝试不同的Dump文件

### 问题5：验证裁剪失败

**症状**：
```
[!] Patch异常: No auth functions found
```

**解决方案**：
1. 使用不同的搜索模式（`--pattern`）
2. 手动分析验证函数位置
3. 尝试不同的Patch方法（`--method`）

### 问题6：全亮检测超时

**症状**：
```
[!] 监控超时
```

**解决方案**：
1. 增加 `timeout.monitor` 配置
2. 降低 `memory_stable_threshold` 阈值
3. 减少 `stable_count` 要求

---

## 注意事项

### 安全警告

1. **法律风险**：本工具仅用于安全研究和学习，请勿用于非法用途
2. **账号风险**：使用破解工具可能导致账号被封禁
3. **系统风险**：内核操作可能导致系统不稳定

### 技术限制

1. **时效性**：游戏更新后需重新破解
2. **兼容性**：仅支持Windows x64程序
3. **稳定性**：DBVM环境可能触发反作弊

### 最佳实践

1. **备份**：操作前备份原始文件
2. **隔离**：在虚拟机中测试破解文件
3. **验证**：断网环境下测试功能完整性
4. **更新**：关注游戏更新，及时重新破解

---

## 高级用法

### 自定义全亮检测

```python
# 修改检测逻辑
pipeline.config["target"]["full_bright_indicators"] = {
    "memory_stable_threshold": 512 * 1024,  # 512KB
    "stable_count": 5,  # 连续5次稳定
    "check_interval": 500,  # 每500ms检测
    "min_runtime": 30,  # 至少运行30秒
}
```

### 自定义Patch方法

```bash
# 使用NOP方法
python ida_auto_patch.py --input "fixed.exe" --pattern "verify" --method "nop"

# 使用XOR方法
python ida_auto_patch.py --input "fixed.exe" --pattern "auth" --method "xor"
```

### 批量处理

```bash
# 批量破解多个目标
for target in "target1.exe" "target2.exe" "target3.exe"; do
    python auto_crack_pipeline.py --target "$target" --config config.json
done
```

---

## 更新日志

### v1.0.0 (2026-06-18)

- 初始版本发布
- 实现4阶段全自动流水线
- 集成CE+Scylla+IDA工具链
- 支持配置文件驱动
- 添加完整日志和报告系统

---

## 附录

### A. 常用命令速查

```bash
# 生成配置
python auto_crack_pipeline.py --generate-config

# 环境检测
python auto_crack_pipeline.py --config config.json --step monitor

# 完整流水线
python auto_crack_pipeline.py --config config.json

# 仅Dump
python auto_crack_pipeline.py --step dump --target "app.exe"

# 仅修复IAT
python auto_crack_pipeline.py --step fix --dump "dump.exe"

# 仅Patch
python auto_crack_pipeline.py --step patch --input "fixed.exe"
```

### B. 配置文件模板

```json
{
  "target": {
    "process_name": "TargetApp.exe",
    "window_title": "Target Window",
    "full_bright_indicators": {
      "memory_stable_threshold": 1048576,
      "stable_count": 3,
      "check_interval": 1000,
      "min_runtime": 10
    }
  },
  "paths": {
    "ce_dir": "C:\\Tools\\CheatEngine",
    "scylla_dir": "C:\\Tools\\Scylla",
    "ida_dir": "C:\\Tools\\IDA",
    "output_dir": "./output",
    "temp_dir": "./temp"
  },
  "pipeline": {
    "auto_dump": true,
    "auto_fix_iat": true,
    "auto_patch": true,
    "keep_temp_files": false,
    "timeout": {
      "monitor": 300,
      "dump": 60,
      "fix": 120,
      "patch": 60
    }
  },
  "notifications": {
    "sound": true,
    "desktop": true,
    "webhook": null
  }
}
```

### C. 相关资源

- [Cheat Engine官网](https://cheatengine.org)
- [Scylla GitHub](https://github.com/NtQuery/Scylla)
- [IDA Pro官网](https://hex-rays.com)
- [DBVM项目](https://github.com/DarkByte7/DBVM)

---

*文档版本: v1.0.0*
*最后更新: 2026-06-18*
*作者: Crack Engine Team*