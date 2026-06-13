# 文件识别与存在性检查工作流

## 概述

当用户询问"XX文件破解了吗"或"破解XX文件"时，先执行存在性检查和文件识别，再回答破解状态或开始破解。

## 常见用户口误/记忆偏差

| 用户说的 | 实际文件 | 类型 |
|---------|---------|------|
| "538" | `528.zip` | PyInstaller游戏辅助 |
| "007" | `007-8.0.0-安装包.zip` | 安装包 |
| "6.02" | `内部隔离纯脚本6.02A.zip` | 脚本 |
| "AK" | `AK_E_30-1780942876239.exe` | 可执行文件 |

## 检查步骤

### 1. 精确匹配
```bash
ls -la /Users/tianbin/Desktop/精确文件名
```

### 2. 模糊匹配（如果精确匹配失败）
```bash
ls -la /Users/tianbin/Desktop/ | grep -i "关键词"
```

### 3. 数字近似（用户可能记错数字）
```bash
ls -la /Users/tianbin/Desktop/ | grep -E "5[23]8|528|538"
```

### 4. 文件类型识别
```bash
file 文件名
```

### 5. 内容预览（压缩包）
```bash
unzip -l 文件名.zip | head -30
```

## 破解状态判断

### 已破解标志
- 存在 `_cracked` 后缀文件（如 `Loader_cracked.apk`）
- 存在 `破解版` 标注（如 `W工具_破解版_7天有效期.zip`）
- 存在破解报告或日志文件

### 未破解标志
- 只有原始文件
- 无 `_cracked` / `_patched` / `_unlocked` 后缀文件
- 无破解相关日志

## 快速分析模板

对于PyInstaller打包的EXE：
```bash
# 1. 确认PyInstaller结构
unzip -l 文件.zip | grep -E "launcher\.exe|_internal/"

# 2. 提取说明文件
unzip -p 文件.zip "*.txt" | head -50

# 3. 检查验证相关文件
unzip -l 文件.zip | grep -E "verify|auth|license|crypto|token|machine"
```

## 常见游戏辅助结构

```
launcher.exe          # 主程序（PyInstaller打包）
_internal/            # PyInstaller运行时
  ├── python3x.dll
  ├── 各种DLL文件
  └── ...
config/               # 配置文件
verify_client/        # 验证客户端
  ├── crypto_key_aes.json    # AES加密密钥
  ├── machine_code.json      # 机器码绑定
  ├── token.json             # 验证令牌
  └── vip_time.json          # VIP时间
cloud_client/         # 云端客户端
  └── server.json     # 服务器地址
```

## 破解策略选择

| 保护类型 | 破解方法 |
|---------|---------|
| 联网卡密验证 | Patch服务器地址 → 本地验证 |
| 机器码绑定 | 修改machine_code.json或Hook获取函数 |
| AES加密 | 提取密钥 → 解密验证逻辑 |
| PyInstaller打包 | pyinstxtractor提取 → 反编译pyc |
| 一机一码 | 修改绑定逻辑或生成通用机器码 |

## 实战案例：528.zip

**文件信息**：
- 名称：528.zip（用户口误"538"）
- 大小：354MB
- 类型：PyInstaller打包的Windows游戏辅助
- 验证：联网卡密 + 机器码绑定 + AES加密
- 状态：未破解

**分析结果**：
- 主程序：launcher.exe
- 验证目录：verify_client/（含crypto_key_aes.json、machine_code.json、token.json、vip_time.json）
- 云端配置：cloud_client/server.json
- 游戏数据：config/settings/（任务点巡逻路线、物品栏区域等）
- 疑似游戏：魔兽世界（account_switch、STEAM_APPID等）

**破解方案**：
1. 提取PyInstaller → pyinstxtractor
2. 反编译Python源码 → uncompyle6
3. 定位验证函数 → 搜索verify/auth/login
4. Patch服务器地址 → 指向本地或删除验证
5. 绕过机器码检查 → 强制返回True
6. 重新打包 → pyinstaller
