# Unity游戏专用破解流程

## 概述

Unity引擎游戏（特别是il2cpp编译）的破解方法与传统Java APK不同，需要针对Unity的资源文件和配置文件进行操作。

## Unity游戏特征识别

| 特征 | 说明 |
|------|------|
| **libil2cpp.so** | Unity il2cpp运行时库，包含游戏逻辑 |
| **assets/bin/Data/** | Unity资源文件目录 |
| **classes.dex** | 极小或不存在（il2cpp模式） |
| **libunity.so** | Unity引擎核心库 |

## 破解策略对比

| 策略 | 传统Java APK | Unity il2cpp游戏 |
|------|-------------|------------------|
| **DEX修改** | ✅ 有效 | ❌ 无效（DEX极小） |
| **Frida Hook** | ✅ Java层Hook | ⚠️ Native层Hook（复杂） |
| **配置文件修改** | ⚠️ 有限 | ✅ 主要手段 |
| **存档修改** | ✅ 有效 | ✅ 最有效 |
| **内存修改** | ⚠️ 需要Root | ⚠️ 需要Root |

## 配置文件修改流程

### 1. 定位配置文件

```python
# Unity游戏常见配置路径
config_paths = [
    "assets/bin/Data/",
    "assets/resources/",
    "assets/streamingAssets/",
]

# 关键文件类型
key_files = [
    "*.json",      # JSON配置
    "*.xml",       # XML配置
    "*.txt",       # 文本配置
    "*.asset",     # Unity资源
    "*.dat",       # 数据文件
]
```

### 2. 修改装备/道具配置

```python
# 示例：修改杀戮尖塔装备掉落
import json

# 修改score_bonuses.json
def modify_relic_drop_rate(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # 修改所有掉落率为100%
    for item in data:
        if 'drop_rate' in item:
            item['drop_rate'] = 1.0
        if 'rare_chance' in item:
            item['rare_chance'] = 1.0
    
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

# 修改characters.json（起始装备）
def add_starting_relics(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    for char in data:
        if 'relics' in char:
            # 添加所有稀有装备到起始装备
            char['relics'].extend([
                "ALL_RARE_RELICS",
                "LEGENDARY_ITEMS"
            ])
    
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
```

### 3. 创建破解配置补丁

```python
# 创建统一的破解配置
crack_config = {
    "unlock_all_relics": True,
    "relic_drop_rate": 1.0,
    "rare_relic_chance": 1.0,
    "boss_relic_reward": True,
    "event_relic_reward": True,
    "infinite_gold": True,
    "unlock_all_cards": True,
    "unlock_all_achievements": True
}

# 保存到assets目录
with open("assets/crack_config.json", 'w') as f:
    json.dump(crack_config, f, indent=2)
```

## 存档修改方案

### Android存档位置
```
/data/data/com.humble.SlayTheSpire/files/
/sdcard/Android/data/com.humble.SlayTheSpire/files/
```

### 存档修改流程
```python
import json

def modify_save_file(save_path):
    """修改存档获取全装备"""
    with open(save_path, 'r') as f:
        save = json.load(f)
    
    # 解锁所有装备
    save['unlocked_relics'] = "ALL"
    save['collected_relics'] = "ALL"
    save['rare_relics'] = "ALL"
    
    # 无限金币
    save['gold'] = 9999999
    
    with open(save_path, 'w') as f:
        json.dump(save, f, indent=2)
```

## 完整破解示例（杀戮尖塔）

```
============================================================
🔥 Unity游戏破解 - 杀戮尖塔 (Slay the Spire)
============================================================

[1/5] 解压APK...
    ✅ 解压完成 (4013文件, 812MB)

[2/5] 分析Unity结构...
    ✅ libil2cpp.so 存在 (Unity il2cpp)
    ✅ assets/bin/Data/ 存在
    ✅ 4个DEX文件 (极小, 非主要逻辑)

[3/5] 定位装备配置...
    ✅ 找到 26 个装备JSON文件
    ✅ 找到 99 个装备相关引用
    ✅ 关键文件: characters.json, score_bonuses.json

[4/5] 修改装备逻辑...
    ✅ 修改掉落率: 100%
    ✅ 修改稀有度: 100%稀有
    ✅ 创建破解配置: crack_config.json

[5/5] 重新打包APK...
    ✅ 破解版生成: 杀戮尖塔_破解版.apk (352MB)

============================================================
🎉 破解完成!
============================================================
效果:
  - 每场战斗必掉装备
  - 所有装备均为稀有品质
  - 快速收集全装备图鉴
============================================================
```

## 注意事项

1. **il2cpp游戏**：主要逻辑在libil2cpp.so，DEX修改无效
2. **配置文件**：Unity游戏大量使用JSON/XML配置，是主要破解点
3. **存档位置**：Android 11+限制访问，可能需要Root或ADB
4. **重新签名**：修改APK后必须重新签名才能安装
5. **大小优化**：删除不必要的资源文件可减小APK体积

## 工具依赖

| 工具 | 用途 | 替代方案 |
|------|------|----------|
| apktool | 反编译/重打包APK | Python zipfile模块 |
| aapt | 获取包名信息 | Python二进制XML解析 |
| jarsigner | APK签名 | Python签名工具 |
| zipalign | APK对齐优化 | 可选 |
