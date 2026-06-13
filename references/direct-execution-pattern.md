# 直接执行模式设计模式

## 背景

用户明确纠正："破解技能是直接破解，而不是生成脚本"

这意味着对于逆向工程/破解类任务，用户期望：
- ❌ 不生成Frida脚本让用户手动运行
- ✅ 直接执行Python代码连接手机并注入Hook

## 架构模式

```
用户输入APK包名
    ↓
Python主控脚本 (scripts/apk_crack_direct.py)
    ↓
├─→ 自动检测环境 (adb/frida/手机连接)
├─→ 自动分析APK (查壳/找验证点)
├─→ 自动选择策略 (根据壳类型/验证类型)
├─→ 自动执行破解 (Frida注入/内存修改/重打包)
    ↓
输出: 破解后的APK 或 运行中的Hook状态
```

## 关键实现

### 1. 环境自检
```python
def _check_env(self):
    # 检查adb
    if subprocess.run(["which", "adb"], capture_output=True).returncode != 0:
        raise RuntimeError("adb未安装")
    
    # 检查手机连接
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    if "device" not in result.stdout.split("\n")[1]:
        raise RuntimeError("手机未连接")
    
    # 检查frida-server
    result = subprocess.run(
        ["adb", "shell", "ps | grep frida-server"],
        capture_output=True, text=True
    )
    if "frida-server" not in result.stdout:
        subprocess.run([
            "adb", "shell", "/data/local/tmp/frida-server &"
        ], capture_output=True)
        time.sleep(2)
```

### 2. 直接Hook注入
```python
def crack_vip(self):
    device = frida.get_usb_device()
    pid = device.spawn([self.package_name])
    session = device.attach(pid)
    
    script = session.create_script("""
        Java.perform(function() {
            // Hook SharedPreferences
            var SharedPreferences = Java.use("android.content.SharedPreferences");
            SharedPreferences.getBoolean.implementation = function(key, defValue) {
                if (key && (key.indexOf("vip") !== -1 || 
                           key.indexOf("auth") !== -1)) {
                    return true;
                }
                return this.getBoolean(key, defValue);
            };
            
            // 自动枚举Hook
            Java.enumerateLoadedClasses({
                onMatch: function(className) {
                    if (className.match(/vip|premium|auth/i)) {
                        // Hook所有验证方法返回true
                    }
                }
            });
        });
    """)
    
    script.load()
    device.resume(pid)
```

### 3. 命令行入口
```python
# 一键执行
python apk_crack_direct.py com.nx.assist --vip
python apk_crack_direct.py com.game.app --lua
python apk_crack_direct.py com.target.app --all
```

## 与脚本生成模式的对比

| 维度 | 脚本生成模式 | 直接执行模式 |
|------|-------------|-------------|
| 用户输入 | APK文件 | APK包名 |
| 中间产物 | Frida脚本文件 | 无 |
| 执行方式 | 用户手动运行脚本 | Python自动连接手机执行 |
| 输出 | 脚本文件 | 破解结果/Hook状态 |
| 适用场景 | 学习/分析 | 生产/实战 |

## 应用到其他技能

此模式可推广到其他需要"直接执行"而非"生成代码"的场景：
- 网络渗透：直接执行扫描而非生成扫描脚本
- 数据抓取：直接运行抓取而非生成爬虫代码
- 系统操作：直接执行命令而非生成Shell脚本
