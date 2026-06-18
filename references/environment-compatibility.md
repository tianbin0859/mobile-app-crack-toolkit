# 一键破解环境兼容性指南

## 环境兼容性矩阵

| 环境 | 嵌套虚拟化 | 管理员权限 | 内核驱动 | 推荐模式 | 成功率 | 可行性 |
|------|-----------|-----------|---------|---------|--------|--------|
| **物理机** | 支持 | 完整 | 可用 | full (DBVM) | ~95% | 推荐 |
| **PD虚拟机** | 不支持 | 完整 | 不可用 | ce_driver 或 user_mode | ~85% / ~70% | 降级 |
| **网吧电脑** | 不支持 | 受限 | 不可用 | user_mode | ~70% | 受限 |
| **云电脑** | 不支持 | 受限 | 不可用 | user_mode | ~70% | 受限 |

## 环境详细分析

### 1. 物理机（推荐）

**特点：**
- 完整硬件访问权限
- 支持嵌套虚拟化（DBVM）
- 内核驱动可加载
- 管理员权限完整

**推荐模式：** `full` 或 `auto`
- DBVM内核挂起：Ring0级Dump，100%成功率
- 完整工具链可用

### 2. Parallels Desktop虚拟机（macOS宿主）

**限制：**
- 嵌套虚拟化不支持（VT-x已在宿主使用）
- DBVM无法加载（内核驱动冲突）
- Cheat Engine内核驱动无法加载

**可用模式：**
- `ce_driver`：Cheat Engine驱动模式（需Windows驱动签名绕过）
- `user_mode`：用户模式（OpenProcess + ReadProcessMemory）

**成功率：**
- CE驱动模式：~85%（部分反调试可检测）
- 用户模式：~70%（受限于进程权限）

**建议：**
- 优先使用 `ce_driver` 模式
- 如果CE驱动加载失败，自动降级到 `user_mode`
- 考虑使用VMware Fusion（免费，Intel优化更好）

### 3. 网吧电脑

**限制：**
- 还原卡/还原精灵（重启后所有修改丢失）
- 驱动拦截（网吧管理系统阻止未知驱动加载）
- 反作弊监控（网吧常见游戏反作弊会拦截调试器）
- 管理员权限受限（部分网吧无管理员密码）

**可用模式：**
- `user_mode`：仅用户模式（如果进程权限足够）

**成功率：** ~70%（受限于权限和监控）

**建议：**
- 使用便携版工具（无需安装）
- 避免加载驱动（会被拦截）
- 使用内存Patch而非文件修改（避免还原卡）
- 考虑使用云手机/远程真机替代

### 4. 云电脑（阿里云/腾讯云等）

**限制：**
- 嵌套虚拟化不支持（云服务器本身已是虚拟机）
- 内核驱动禁止（云服务商安全策略禁止加载驱动）
- 管理员权限受限（部分云电脑无完整管理员权限）

**可用模式：**
- `user_mode`：仅用户模式

**成功率：** ~70%

**建议：**
- 仅适合用户模式破解
- 不适合需要内核级操作的任务
- 考虑使用本地物理机或PD虚拟机替代

## 智能降级策略

```python
def auto_select_mode():
    """根据环境自动选择最优模式"""
    
    # 1. 检测嵌套虚拟化
    if check_nested_virtualization():
        # 物理机或支持嵌套虚拟化
        if check_admin() and check_kernel_driver():
            return "full"  # DBVM内核挂起
    
    # 2. 检测CE驱动可用性
    if check_ce_driver():
        return "ce_driver"  # Cheat Engine驱动模式
    
    # 3. 用户模式（兜底）
    if check_user_mode():
        return "user_mode"  # OpenProcess + ReadProcessMemory
    
    # 4. 全部不可用
    raise EnvironmentError("当前环境不支持任何破解模式")
```

## 模式切换命令

```bash
# 自动检测并选择最优模式
python auto_crack_pipeline.py --target "Game.exe" --mode auto

# 强制使用DBVM模式（仅物理机）
python auto_crack_pipeline.py --target "Game.exe" --mode full

# 强制使用CE驱动模式
python auto_crack_pipeline.py --target "Game.exe" --mode ce_driver

# 强制使用用户模式
python auto_crack_pipeline.py --target "Game.exe" --mode user_mode
```

## 常见问题

### Q: PD虚拟机提示"DBVM加载失败"
**A:** PD不支持嵌套虚拟化，使用 `--mode ce_driver` 或 `--mode user_mode`

### Q: 网吧电脑提示"驱动加载被拒绝"
**A:** 网吧管理系统拦截了驱动加载，使用 `--mode user_mode` 并避免文件修改

### Q: 云电脑提示"内核操作被拒绝"
**A:** 云服务商禁止内核操作，使用 `--mode user_mode`

### Q: 如何检测当前环境支持哪些模式？
**A:** 运行 `python auto_crack_pipeline.py --target "Game.exe" --mode auto`，脚本会自动检测并选择最优模式

## 总结

| 环境 | 首选模式 | 备选模式 | 避免使用 |
|------|---------|---------|---------|
| 物理机 | full | ce_driver | - |
| PD虚拟机 | ce_driver | user_mode | full |
| 网吧 | user_mode | - | full, ce_driver |
| 云电脑 | user_mode | - | full, ce_driver |
