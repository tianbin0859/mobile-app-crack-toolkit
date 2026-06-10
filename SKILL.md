---
title: APK Crack Engine Pro
description: |
  Use when: 1) 用户要求去除APK收费模块/会员限制 2) 用户要求破解APK授权验证 3) 用户要求逆向分析APK加密逻辑 4) 用户要求绕过APK试用限制或过期检查 5) 用户要求APK脱壳/反混淆/反编译 6) 用户要求破解网络验证(E盾/天盾/MAPO等) 7) 用户要求脚本破译(Lua/JS/按键精灵等) 8) 用户要求360加固脱壳/去卡密 9) 用户要求修改APK标题LOGO/资源 10) 用户要求软件加解密分析 11) 用户要求破解PyInstaller打包的EXE程序 12) 用户要求提取Python程序源码 13) 用户要求破解游戏辅助/自动化脚本 14) 用户要求破解iOS IPA应用 15) 用户要求生成离线授权码 16) 用户要求绕过本地授权验证
  直接执行破解（非生成脚本），输入目标自动输出破解结果。覆盖APK、PyInstaller EXE、压缩包内嵌软件、游戏辅助脚本、iOS IPA、离线授权系统等。支持脱壳、反混淆、网络验证绕过、脚本破译、加固脱壳、资源修改、加解密、授权绕过、iOS重签名、离线授权全流程。
triggers:
  - apk破解
  - 去除收费
  - 去会员
  - 绕过授权
  - 破解验证
  - 逆向apk
  - 脱壳
  - 去广告
  - 解锁功能
  - 破解vip
  - 破解license
  - 逆向分析
  - 反编译
  - hook注入
  - 动态调试
  - 脱壳破译
  - 反混淆
  - 二次开发
  - 网络验证
  - e盾
  - 天盾
  - 大禹盾
  - 注册机
  - vmp脱壳
  - 360加固
  - 去卡密
  - 脚本破译
  - 按键精灵
  - 懒人精灵
  - ec脚本
  - 修改软件
  - 加解密
  - 软件破解
  - 过授权
  - 直接破解
  - 自动破解
  - 一键破解
  - 破解apk
  - pyinstaller
  - exe破解
  - python程序逆向
  - 提取源码
  - 授权绕过
  - 卡密破解
  - 程序脱壳
  - 软件逆向
  - 自动化脚本破解
  - 游戏辅助破解
  - 易语言破解
  - 压缩包破解
  - zip破解
  - rar破解
  - 脚本破解
  - 收费软件破解
  - 会员破解
  - 无限期使用
  - 永久破解
  - 破解工具
  - 破解技能
  - 破解方案
  - ios破解
  - ipa破解
  - 离线授权
  - 授权码生成
  - 本地验证
  - 卡密系统
tags:
  - reverse-engineering
  - apk
  - frida
  - crack
  - android
  - dex
  - so
  - lua
  - unpacker
  - deobfuscator
  - vmp
  - crypto
related_skills:
  - frida-mobile-signing-reverse
  - systematic-debugging
  - github-research-pro
name: apk-crack-engine
---

# APK Crack Engine Pro - 直接执行版 v5.5

## 核心变更

**本技能为直接执行模式，非脚本生成模式：**
- ❌ 旧模式：生成Frida脚本 → 用户手动运行
- ✅ 新模式：输入APK包名 → 自动连接手机 → 直接执行Hook/修改/脱壳

**仓库隐私强制规则：**
- 🔒 涉及破解/逆向/游戏自动化的项目，**必须设为私有仓库**
- 详见模块十：仓库隐私管理

**适用范围扩展：**
- ✅ Android APK (主要目标)
- ✅ PyInstaller打包的EXE (Python程序逆向)
- ✅ 压缩包内的脚本/程序 (ZIP/RAR内嵌软件)
- ✅ 游戏辅助/自动化脚本 (按键精灵/易语言/Auto.js等)
- ✅ **Windows原生程序/安装包** (PE/NSIS/Installer/VMP加壳)
- ✅ **Android ELF共享库** (SO注入型外挂/游戏辅助)
- ✅ **自解压脚本** (Shell包装层 + gzip压缩ELF)
- ✅ **iOS IPA应用** (iOS应用安装包破解、重签名)
- ✅ **离线授权码系统** (无需联网的本地授权验证)
- ⚠️ 强壳程序 (VMProtect/Themida/Enigma，需脱壳)

**Windows程序处理流程：**
收到.exe/.msi安装包时：
1. 识别安装包类型: `file xxx.exe` → PE32/NSIS/Installer
2. 提取内容: `7z x xxx.exe` 或 `strings xxx.exe | grep`
3. 分析提取出的主程序
4. 根据类型选择工具: x64dbg/IDA/dnSpy

**NSIS安装包特征：**
- `PE32 executable (GUI) Intel 80386, for MS Windows, Nullsoft Installer self-extracting archive`
- 包含安装脚本和压缩数据
- 提取后可见 `$PLUGINSDIR`、`$_OUTDIR` 等NSIS目录

**NSIS提取命令：**
```bash
# 使用7z提取
7z x setup.exe -oextracted/

# 或使用unzip (部分NSIS包可用)
unzip setup.exe -d extracted/

# 查看字符串
strings setup.exe | grep -i "license\|key\|reg\|serial\|vip\|pro\|premium\|activate"
```

**自解压脚本分析 (Shell + Gzip ELF)：**
```bash
# 识别自解压脚本
file script.sh
# 输出: a /system/bin/sh script executable (binary data)

# 提取gzip部分
# 方法1: 找到gzip魔数(0x1f8b)位置并提取
tail -c +<offset> script.sh | gzip -cd > extracted_elf

# 方法2: Python提取
python3 -c "
import gzip, os
with open('script.sh', 'rb') as f:
    data = f.read()
pos = data.find(b'\x1f\x8b')
if pos != -1:
    with open('elf', 'wb') as o:
        o.write(gzip.decompress(data[pos:]))
"

# 分析提取的ELF
file extracted_elf
# 输出: ELF 64-bit LSB shared object, ARM aarch64
```

**自解压脚本典型结构：**
```bash
#!/system/bin/sh
# 1. 随机选择可写目录
folders=($(find /data/ -maxdepth 1 -type d))
random_folder="${folders[$RANDOM % ${#folders[@]}]}"

# 2. 生成随机文件名
wenjmz=$(printf "%s_%s" "$(date +%s)" "$$" | sha256sum | head -c 32)

# 3. 提取并解压ELF (从脚本自身提取gzip数据)
sed -n "$((LINENO+1)),$ p" < "$0" | gzip -cd > "${random_folder}/${wenjmz}"

# 4. 执行ELF
chmod 700 "$elf_path"
exec "$elf_path"

# 5. 退出清理 (删除痕迹)
trap 'rm -f "$elf_path" 2>/dev/null' EXIT

# [GZIP压缩的ELF数据...]
```

**ELF注入型外挂分析流程：**
1. 提取ELF文件 (从gzip解压)
2. 分析ELF头 (readelf/file命令)
3. 搜索关键字符串 (strings + grep)
4. 识别注入机制 (ptrace/mmap/mprotect)
5. 识别游戏Hook点 (OpenGL ES/Vulkan/UE4)
6. 定位网络验证API
7. Patch验证逻辑

**ELF Patch方法：**
```python
# 修改ELF中的字符串 (如服务器地址)
with open('extracted_elf', 'rb') as f:
    data = bytearray(f.read())

# 查找并替换服务器地址
old_url = b'http://hash.wskxc.cn/\x00'
new_url = b'127.0.0.1\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

pos = data.find(old_url)
if pos != -1:
    data[pos:pos+len(new_url)] = new_url

# 重新压缩为gzip
import gzip
with open('patched_elf.gz', 'wb') as f:
    f.write(gzip.compress(bytes(data)))

# 重新打包为sh脚本
with open('cracked.sh', 'wb') as out:
    out.write(b'#!/system/bin/sh\n# ...脚本头...\n')
    out.write(gzip.compress(bytes(data)))
```

**VMProtect加壳识别：**
```bash
# 检测VMP节区
readpe xxx.exe | grep -i "vmp\|upx\|aspack"

# 或查看节表名
objdump -h xxx.exe | grep -i "\.vmp\|\.upx"
```
- VMP特征节名: `.vmp0`, `.vmp1`, `.vmps0`, `.vmps1`
- VMP是强壳，需脱壳后才能分析
- 脱壳工具: VMPDump, Scylla, x64dbg插件

**Electron应用识别：**
- 包含 `chrome_100_percent.pak`, `LICENSE.electron.txt`
- 资源目录有 `resources/app.asar`
- 破解方式: 解压ASAR → 修改JS → 重新打包
```bash
npx asar extract resources/app.asar resources/app/
# 修改JS后
npx asar pack resources/app/ resources/app.asar
```

## 执行架构（AI Agent 五阶段循环 v5.3）

```
用户输入目标
    ↓
╔══════════════════════════════════════════════════════════╗
║ 阶段一：感知 (Perception)                                ║
║ ├─→ 识别目标类型：APK / EXE / ZIP / 脚本                 ║
║ ├─→ 检测保护级别：无保护 / 加固 / VMP / 网络验证          ║
║ └─→ 评估环境状态：工具链完整性 / 设备连接状态              ║
╚══════════════════════════════════════════════════════════╝
    ↓
╔══════════════════════════════════════════════════════════╗
║ 阶段二：思考 (Reasoning/Planning)                        ║
║ ├─→ 分析目标结构：包名、版本、保护类型、验证点            ║
║ ├─→ 拆解破解步骤：检测→分析→选择策略→执行→验证           ║
║ ├─→ 规划执行路径：根据环境选择最优破解方案                  ║
║ └─→ 预测失败点：提前准备备选方案                          ║
╚══════════════════════════════════════════════════════════╝
    ↓
╔══════════════════════════════════════════════════════════╗
║ 阶段三：执行 (Execution)                                 ║
║ ├─→ 环境检测与自动修复 (adb/frida/手机/模拟器/云手机)      ║
║ ├─→ 深度分析 (scripts/apk_analyzer_pro.py)              ║
║ ├─→ 策略选择 (在线Hook / 离线修改 / 模拟器 / 云手机)      ║
║ ├─→ 智能执行 (Frida注入 / APK重打包 / 模拟器绕过)         ║
║ └─→ 实时进度汇报 (每步骤输出状态)                         ║
╚══════════════════════════════════════════════════════════╝
    ↓
╔══════════════════════════════════════════════════════════╗
║ 阶段四：检查 (Inspection/Review)                         ║
║ ├─→ 验证破解结果：VIP功能是否解锁？                       ║
║ ├─→ 检查错误：Hook是否生效？APK是否正常运行？              ║
║ ├─→ 评估完整性：是否所有验证点都已绕过？                   ║
║ └─→ 生成报告：输出结构化破解报告                          ║
╚══════════════════════════════════════════════════════════╝
    ↓
    ├─→ ✅ 检查通过 → 输出破解结果 + 生成报告
    └─→ ❌ 发现问题 → 进入阶段五
    ↓
╔══════════════════════════════════════════════════════════╗
║ 阶段五：修正 (Correction/Refinement)                     ║
║ ├─→ 分析失败原因：环境缺失？策略错误？保护升级？           ║
║ ├─→ 自动修复：尝试修复环境问题 / 切换工具版本              ║
║ ├─→ 调整策略：切换Hook点 / 更换破解模式 / 升级工具        ║
║ ├─→ 重试机制：最多3次自动重试，每次更换策略               ║
║ └─→ 重新执行：回到阶段一，开启新一轮循环                   ║
╚══════════════════════════════════════════════════════════╝
    ↓
输出: 破解后的文件 + 破解报告 + 使用说明
```

**用户交互模式：**
- 用户说"同意" → 立即执行破解，不再确认
- 用户说"进度" → 立即汇报当前分析/破解状态
- 用户回复数字(1/2/3) → 直接选择对应选项
- 用户说"继续" → 继续上一步操作，不重复确认
- **用户说"自动选择最佳方式" → 不询问，直接分析并执行最优方案，事后汇报结果**
- **用户说"用破解技能破解收费" → 自动识别文件类型并执行对应破解流程**

**核心特点：**
- **闭环迭代**：五阶段持续循环，自主纠错、逐步逼近目标
- **类人决策**：模拟人类逆向思维——先感知、再分析、后行动、再验证、最后改进
- **工具协同**：执行阶段动态调用外部工具（Frida/apktool/adb/mitmproxy）
- **自适应**：根据检查结果自动调整策略，无需人工干预
- **自动修复**：环境缺失时自动尝试安装/修复

**循环控制参数：**
| 参数 | 默认值 | 说明 |
|------|--------|------|
| max_retries | 3 | 最大重试次数 |
| timeout_per_round | 300 | 每轮超时时间(秒) |
| success_threshold | 0.8 | 成功率阈值(超过则停止) |
| auto_fix_env | True | 自动修复环境问题 |
| parallel_mode | False | 并行批量破解模式 |

## 破解模式

| 模式 | 条件 | 成功率 | 适用场景 | 速度 |
|------|------|--------|----------|------|
| **在线Hook** | 手机已Root+Frida-server | 85-95% | 有真机环境 | 快 |
| **离线修改** | apktool+java可用 | 70-85% | 无手机，直接改APK | 中 |
| **模拟器** | 雷电/夜神+Root | 60-75% | 只有电脑 | 中 |
| **云手机** | 远程ADB连接 | 80-90% | 24小时在线需求 | 快 |
| **内存Patch** | 程序已运行 | 90-95% | 游戏辅助/脚本 | 快 |
| **配置修改** | 有配置文件 | 95-99% | 脚本/简单程序 | 极快 |

## 智能环境诊断与自动修复

### 环境检测清单

```python
def diagnose_environment():
    """智能环境诊断"""
    checks = {
        "adb": check_adb(),           # Android调试桥
        "frida": check_frida(),       # Frida框架
        "apktool": check_apktool(),   # APK反编译工具
        "java": check_java(),         # Java运行时
        "python": check_python(),     # Python环境
        "phone": check_phone(),       # 手机连接
        "root": check_root(),         # Root权限
        "mitmproxy": check_mitm(),    # 代理工具
    }
    return checks
```

### 自动修复流程

```
检测到环境缺失
    ↓
尝试自动安装 (brew/apt/pip)
    ↓
安装失败 → 提供手动安装命令
    ↓
安装成功 → 继续破解流程
```

### 常见错误自动修复

| 错误 | 自动修复方案 |
|------|-------------|
| Frida-server未启动 | 自动推送并启动frida-server |
| ADB未授权 | 提示用户授权，等待后重试 |
| apktool版本过低 | 自动下载最新版本 |
| Java未安装 | 提供安装命令 (brew install openjdk) |
| 端口被占用 | 自动查找可用端口 |
| 依赖缺失 | 自动pip install |

## 快速使用

### 方式1: 智能自动模式（推荐）

```python
from scripts.apk_crack_enhanced import APKCrackEnhanced

# 自动选择最优策略
cracker = APKCrackEnhanced("com.nx.assist")
result = cracker.crack_with_retry()

if result.success:
    print(f"破解成功! 输出: {result.output_path}")
    print(f"破解报告: {result.report_path}")
```

### 方式2: 离线直接修改APK

```python
# 无需手机，直接修改APK文件
cracker = APKCrackEnhanced("com.nx.assist", apk_path="/path/to/feimao.apk")
result = cracker.crack_offline()
# 输出: /tmp/com.nx.assist_cracked.apk
```

### 方式3: 命令行

```bash
# 智能模式
python scripts/apk_crack_enhanced.py com.nx.assist

# 离线模式
python scripts/apk_crack_enhanced.py com.nx.assist --apk feimao.apk --offline

# 云手机
python scripts/apk_crack_enhanced.py com.nx.assist --cloud 192.168.1.100:5555

# 批量破解
python scripts/apk_crack_enhanced.py com.pkg1 com.pkg2 com.pkg3 --batch

# 生成破解报告
python scripts/apk_crack_enhanced.py com.nx.assist --report
```

## 模块零：深度分析（新增）

所有破解操作前**必须**执行深度分析：

```python
from scripts.apk_analyzer_pro import APKAnalyzerPro
from scripts.apk_crack_direct import APKCracker

# 1. 分析
analyzer = APKAnalyzerPro("com.nx.assist")
report = analyzer.full_analysis()

# 2. 根据报告选择策略
print(f"建议策略: {report.suggested_strategy}")
print(f"预估成功率: {report.success_rate_estimate:.0%}")

# 3. 执行破解
cracker = APKCracker("com.nx.assist")
if report.success_rate_estimate > 0.7:
    cracker.crack_vip()
```

### 分析内容

| 分析项 | 说明 |
|--------|------|
| 壳检测 | 360/梆梆/爱加密/腾讯等 |
| 混淆检测 | ProGuard/R8/Allatori/DashO |
| 反调试 | Debug/TracerPid/ptrace/inotify |
| 反Hook | Xposed/Frida/Substrate检测 |
| Root检测 | su/Magisk/debuggable检测 |
| 验证点 | Java/Native/Network/SharedPrefs |
| 策略生成 | 自动计算最优破解路径 |

### 分析报告示例

```
============================================================
APK深度分析报告
============================================================
包名: com.nx.assist
版本: 2.1.0
SDK: min=21, target=30

保护措施:
  壳: none
  混淆: ProGuard (中度混淆)
  反调试: 无
  反Hook: 无
  Root检测: su二进制检测
  网络安全: 标准配置

验证点 (8个):
  1. [java] com.nx.main.VipManager.isVip
     描述: isVip检查
     策略: Hook com.nx.main.VipManager.isVip强制返回true
  2. [shared_prefs] com.nx.main.PrefHelper
     描述: SharedPreferences含vip关键字
     策略: Hook SharedPreferences.getBoolean强制返回true
  ...

建议策略: Java层Hook (3个验证点) → SharedPreferences伪造 (2个)
预估成功率: 85%
============================================================
```

## 模块一：直接脱壳执行

### 自动查壳 + 脱壳

```python
from scripts.apk_crack_direct import APKCracker

cracker = APKCracker("com.target.app")

# 自动识别壳类型并脱壳
result = cracker.auto_unpack()
# 输出: /tmp/unpacked_dex/ 目录下的DEX文件
```

**执行流程（全自动）：**
1. `apktool d` 反编译APK查看SO文件
2. 根据SO文件名识别壳类型（360/梆梆/爱加密/腾讯等）
3. 自动选择脱壳方案：
   - 普通加固 → FRIDA-DEXDump自动注入
   - VMP → 内存Trace自动Dump
   - 360 → BlackDex自动脱壳
4. 输出脱壳后的DEX到指定目录

### 代码实现

```python
def auto_unpack(self):
    """自动脱壳主流程"""
    # 1. 查壳
    shell_type = self.detect_shell()
    print(f"[*] 检测到壳类型: {shell_type}")
    
    # 2. 选择脱壳器
    unpacker = self.get_unpacker(shell_type)
    
    # 3. 执行脱壳
    if shell_type == "360":
        return unpacker.frida_dump()
    elif shell_type == "VMP":
        return unpacker.memory_trace()
    elif shell_type == "none":
        return self.extract_dex_direct()
    else:
        return unpacker.generic_dump()
```

## 模块二：直接Hook执行

### 一键VIP破解

```python
cracker = APKCracker("com.nx.assist")
cracker.crack_vip()
```

**执行流程：**
1. 自动启动目标APP
2. 自动枚举所有类，定位VIP验证相关方法
3. 自动注入Hook：
   - `isVip()` → 强制返回true
   - `checkPermission()` → 强制返回true
   - `getUserType()` → 返回"premium"
4. 实时输出Hook结果

### 代码实现

```python
def crack_vip(self):
    """直接执行VIP破解"""
    import frida
    
    # 1. 连接设备
    device = frida.get_usb_device()
    pid = device.spawn([self.package_name])
    session = device.attach(pid)
    
    # 2. 自动定位验证方法
    script = session.create_script("""
        Java.perform(function() {
            // 自动枚举类
            Java.enumerateLoadedClasses({
                onMatch: function(className) {
                    if (className.match(/vip|premium|auth|license/i)) {
                        hookClass(className);
                    }
                },
                onComplete: function() {}
            });
            
            function hookClass(className) {
                try {
                    var cls = Java.use(className);
                    var methods = cls.class.getDeclaredMethods();
                    methods.forEach(function(method) {
                        var name = method.getName();
                        if (name.match(/isVip|check|verify|auth/i)) {
                            // 自动Hook返回true
                            cls[name].implementation = function() {
                                console.log("[+] Hooked: " + className + "." + name);
                                return true;
                            };
                        }
                    });
                } catch(e) {}
            }
        });
    """)
    
    # 3. 执行
    script.load()
    device.resume(pid)
    print(f"[*] VIP破解已注入: {self.package_name}")
    return session
```

## 模块三：直接网络验证绕过

### 自动抓包 + 响应伪造

```python
cracker = APKCracker("com.target.app")
cracker.bypass_network_auth()
```

**执行流程：**
1. 自动设置HTTP代理（mitmproxy）
2. 自动安装证书到手机
3. 自动分析验证请求
4. 自动注入响应修改规则
5. 实时输出绕过结果

### 代码实现

```python
def bypass_network_auth(self):
    """直接执行网络验证绕过"""
    # 1. 启动mitmproxy代理
    self.start_mitmproxy()
    
    # 2. 设置手机代理
    self.set_device_proxy("192.168.1.100", 8080)
    
    # 3. 自动分析并修改响应
    self.inject_response_hook("""
        if flow.request.url.contains("/api/auth"):
            flow.response.text = flow.response.text.replace(
                '"status":0', '"status":1'
            ).replace(
                '"vip":false', '"vip":true'
            )
    """)
    
    print("[*] 网络验证绕过已激活")
```

## 模块四：直接脚本解密

### 自动提取 + 解密

```python
cracker = APKCracker("com.game.app")
cracker.decrypt_lua_scripts()
```

**执行流程：**
1. 自动附加游戏进程
2. 自动Hook `luaL_loadbufferx`
3. 自动保存解密后的Lua脚本到 `/tmp/lua_dump/`

### 代码实现

```python
def decrypt_lua_scripts(self):
    """直接执行Lua脚本解密"""
    import frida
    
    device = frida.get_usb_device()
    session = device.attach(self.package_name)
    
    script = session.create_script("""
        var dumpDir = "/sdcard/lua_dump/";
        
        Interceptor.attach(Module.findExportByName("liblua.so", "luaL_loadbufferx"), {
            onEnter: function(args) {
                var size = args[2].toInt32();
                var buf = args[1];
                var data = Memory.readByteArray(buf, size);
                
                var filename = dumpDir + "script_" + Date.now() + ".lua";
                var file = new File(filename, "wb");
                file.write(data);
                file.close();
                
                send({"type": "lua_dump", "file": filename, "size": size});
            }
        });
    """)
    
    script.on('message', lambda msg: print(f"[+] Lua dumped: {msg['payload']['file']}"))
    script.load()
    
    print("[*] Lua脚本自动提取已启动，操作APP触发加载即可")
    return session
```

## 模块五：直接APK修改

### 一键修改 + 重打包

```python
cracker = APKCracker("com.target.app")
cracker.modify_and_repack({
    "app_name": "破解版",
    "icon": "new_icon.png",
    "package": "com.target.cracked"
})
```

**执行流程：**
1. `apktool d` 反编译
2. 自动修改资源/字符串/包名
3. `apktool b` 重打包
4. 自动签名
5. 输出最终APK

### 代码实现

```python
def modify_and_repack(self, changes):
    """直接执行APK修改并重打包"""
    import subprocess
    import shutil
    
    decoded_dir = "/tmp/apk_decoded"
    output_apk = f"/tmp/{self.package_name}_cracked.apk"
    
    # 1. 反编译
    subprocess.run(["apktool", "d", self.apk_path, "-o", decoded_dir, "-f"])
    
    # 2. 修改
    if "app_name" in changes:
        self._change_app_name(decoded_dir, changes["app_name"])
    if "icon" in changes:
        self._replace_icon(decoded_dir, changes["icon"])
    if "package" in changes:
        self._change_package(decoded_dir, changes["package"])
    
    # 3. 重打包
    subprocess.run(["apktool", "b", decoded_dir, "-o", output_apk])
    
    # 4. 签名
    self._sign_apk(output_apk)
    
    print(f"[+] 破解APK已生成: {output_apk}")
    return output_apk
```

## 破解报告生成

### 自动生成结构化报告

```python
cracker = APKCrackEnhanced("com.target.app")
result = cracker.crack_with_retry()

# 自动生成报告
report = cracker.generate_report()
# 输出: /tmp/crack_report_20260609_143022.md
```

### 报告内容

```markdown
# 破解报告

## 目标信息
- 包名: com.target.app
- 版本: 2.1.0
- 保护: ProGuard混淆

## 破解过程
1. ✅ 环境检测通过
2. ✅ 深度分析完成 (发现8个验证点)
3. ✅ 执行Hook (3个验证点)
4. ✅ 验证通过

## 破解结果
- 状态: 成功
- 方法: Java层Hook
- 耗时: 45秒
- 输出: /tmp/com.target.app_cracked.apk

## 验证点清单
| # | 类型 | 方法 | 状态 |
|---|------|------|------|
| 1 | Java | isVip() | ✅ 已绕过 |
| 2 | Java | checkPermission() | ✅ 已绕过 |
| 3 | SharedPrefs | getBoolean() | ✅ 已绕过 |

## 使用说明
1. 安装破解版APK
2. 无需登录即可使用VIP功能
3. 所有功能已解锁
```

## 批量破解并行处理

### 并行模式

```python
# 批量并行破解
targets = ["com.pkg1", "com.pkg2", "com.pkg3", "com.pkg4"]
results = APKCrackEnhanced.crack_batch_parallel(targets, max_workers=4)

# 生成汇总报告
APKCrackEnhanced.generate_batch_report(results)
```

### 代码实现

```python
from concurrent.futures import ThreadPoolExecutor

def crack_batch_parallel(targets, max_workers=4):
    """并行批量破解"""
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(crack_single, target): target 
            for target in targets
        }
        
        for future in futures:
            target = futures[future]
            try:
                result = future.result(timeout=300)
                results.append({"target": target, "success": True, "result": result})
            except Exception as e:
                results.append({"target": target, "success": False, "error": str(e)})
    
    return results
```

## 主控脚本

### 增强版 v5.3 (推荐)

```python
#!/usr/bin/env python3
"""
apk_crack_enhanced.py - APK增强版直接破解主控 v5.3
支持: 在线Hook / 离线修改 / 模拟器 / 云手机 / 批量破解 / 报告生成
用法: python apk_crack_enhanced.py <package_name> [--apk PATH] [--offline] [--cloud IP:PORT]
"""

import sys
import argparse
from scripts.apk_crack_enhanced import APKCrackEnhanced

def main():
    parser = argparse.ArgumentParser(description="APK Crack Engine Enhanced v5.3")
    parser.add_argument("package", help="目标APK包名")
    parser.add_argument("--apk", help="APK路径（离线模式）")
    parser.add_argument("--offline", action="store_true", help="强制离线模式")
    parser.add_argument("--cloud", help="云手机IP:端口")
    parser.add_argument("--batch", nargs='+', help="批量破解包名列表")
    parser.add_argument("--report", action="store_true", help="生成破解报告")
    parser.add_argument("--parallel", action="store_true", help="并行批量破解")
    
    args = parser.parse_args()
    
    if args.cloud:
        ip, port = args.cloud.split(":")
        APKCrackEnhanced.connect_cloud_phone(ip, int(port))
    
    if args.batch:
        if args.parallel:
            results = APKCrackEnhanced.crack_batch_parallel(args.batch)
        else:
            results = APKCrackEnhanced.crack_batch(args.batch)
        
        if args.report:
            APKCrackEnhanced.generate_batch_report(results)
        return
    
    cracker = APKCrackEnhanced(args.package, args.apk)
    
    if args.offline:
        result = cracker.crack_offline()
    else:
        result = cracker.crack_with_retry()
    
    print(f"结果: {'成功' if result.success else '失败'} ({result.method})")
    
    if args.report:
        report_path = cracker.generate_report()
        print(f"报告已生成: {report_path}")

if __name__ == "__main__":
    main()
```

### 基础版 v3.0

```python
#!/usr/bin/env python3
"""
apk_crack_direct.py - APK直接破解主控
用法: python apk_crack_direct.py <package_name> [--vip] [--unpack] [--network] [--lua] [--modify]
"""

import sys
import argparse
from scripts.apk_crack_direct import APKCracker

def main():
    parser = argparse.ArgumentParser(description="APK Crack Engine - 直接执行版")
    parser.add_argument("package", help="目标APK包名")
    parser.add_argument("--vip", action="store_true", help="破解VIP限制")
    parser.add_argument("--unpack", action="store_true", help="脱壳")
    parser.add_argument("--network", action="store_true", help="绕过网络验证")
    parser.add_argument("--lua", action="store_true", help="解密Lua脚本")
    parser.add_argument("--modify", nargs='+', help="修改APK (name=xxx icon=xxx)")
    parser.add_argument("--all", action="store_true", help="执行全部破解")
    
    args = parser.parse_args()
    
    cracker = APKCracker(args.package)
    
    if args.all:
        print("[*] 执行全量破解...")
        cracker.auto_unpack()
        cracker.crack_vip()
        cracker.bypass_network_auth()
        print("[+] 全量破解完成")
    elif args.vip:
        cracker.crack_vip()
    elif args.unpack:
        cracker.auto_unpack()
    elif args.network:
        cracker.bypass_network_auth()
    elif args.lua:
        cracker.decrypt_lua_scripts()
    elif args.modify:
        changes = dict(m.split("=") for m in args.modify)
        cracker.modify_and_repack(changes)
    else:
        # 默认分析模式
        cracker.analyze()

if __name__ == "__main__":
    main()
```

## 工具链矩阵

| 功能 | 工具 | 用途 | 执行方式 |
|------|------|------|----------|
| 脱壳 | FRIDA-DEXDump | Frida内存脱壳 | Python直接调用 |
| 脱壳 | BlackDex | 免Root脱壳 | adb安装+自动操作 |
| 反编译 | Jadx | DEX反编译 | 命令行调用 |
| Hook | Frida | 动态注入 | Python API |
| 抓包 | mitmproxy | HTTP分析 | Python嵌入 |
| 重打包 | apktool | APK修改 | 命令行调用 |
| 签名 | apksigner | APK签名 | 命令行调用 |
| EXE逆向 | pyinstxtractor | PyInstaller解包 | 命令行调用 |
| EXE反编译 | uncompyle6 | pyc反编译 | 命令行调用 |
| 授权管理 | license_manager | 卡密生成与验证 | Python API |

## 模块六：授权管理与保护

### 功能概述

授权管理模块允许用户：
- **生成卡密**: 创建带期限的授权卡密
- **验证授权**: 启动时验证卡密有效性
- **机器绑定**: 防止一码多用
- **期限控制**: 精确到天的使用期限
- **授权破解**: 分析并绕过他人的授权验证

### 卡密生成

```python
from scripts.license_manager import LicenseManager

# 创建授权管理器
manager = LicenseManager()

# 生成30天卡密 (绑定机器)
key = manager.generate_license(days=30, machine_bind=True)
print(f"生成卡密: {key}")
# 输出: DNF-eyJjcm...1169

# 生成永久卡密 (不绑定机器)
key = manager.generate_license(days=9999, machine_bind=False)
print(f"永久卡密: {key}")
```

### 批量生成卡密

```python
from scripts.license_manager import LicenseGenerator

# 批量生成
gen = LicenseGenerator()
licenses = gen.generate_batch(count=10, days=30, machine_bind=True)

# 导出到文件
gen.export_to_file("licenses.txt")
```

### 授权验证

```python
# 在程序启动时验证
manager = LicenseManager()
valid, msg = manager.validate()

if not valid:
    print(f"授权验证失败: {msg}")
    exit(1)

print(f"授权验证通过: {msg}")
```

### 授权破解 (逆向分析)

```python
from scripts.license_cracker import LicenseCracker

# 分析目标程序的授权机制
cracker = LicenseCracker("com.target.app")

# 提取授权验证逻辑
auth_logic = cracker.extract_auth_logic()
print(f"验证类型: {auth_logic.type}")
print(f"验证点: {auth_logic.checkpoints}")

# 生成绕过方案
bypass = cracker.generate_bypass()
# 输出: 修改配置 / Hook验证 / Patch程序
```

### 常见授权方案分析

| 授权类型 | 特征 | 破解方法 | 难度 |
|----------|------|----------|------|
| **本地文件验证** | 读取本地license文件 | 修改文件/Hook读取 | ⭐ |
| **SharedPreferences** | 存储在SP中 | Hook getBoolean | ⭐ |
| **网络API验证** | 请求服务器验证 | 抓包改响应/Hosts劫持 | ⭐⭐⭐ |
| **URL字符串Patch** | ELF/APK中硬编码服务器地址 | 修改字符串指向本地 | ⭐⭐ |
| **签名验证** | 校验APK签名 | 重签名/Hook校验 | ⭐⭐ |
| **机器码绑定** | 绑定MAC/IMEI | 修改机器码/Hook获取 | ⭐⭐ |
| **时间戳验证** | 检查系统时间 | 修改时间/Hook时间获取 | ⭐ |
| **加密授权** | 加密存储授权信息 | 分析加密算法/找密钥 | ⭐⭐⭐⭐ |
| **多验证点** | 多处验证互相校验 | 全部Hook/整体Patch | ⭐⭐⭐⭐⭐ |

### 命令行工具

```bash
# 生成卡密
python scripts/license_manager.py generate --days 30 --count 5 --bind

# 验证卡密
python scripts/license_manager.py verify --key DNF-xxx

# 查看授权信息
python scripts/license_manager.py info

# 破解目标授权
python scripts/license_cracker.py com.target.app --analyze
```

## 模块七：网络授权服务器

### 功能概述

自建网络授权验证服务器，支持：
- **卡密验证**: 客户端请求服务器验证卡密有效性
- **机器绑定**: 服务端记录机器码，防止一码多用
- **在线激活**: 首次使用需要联网激活
- **心跳检测**: 定期验证授权状态
- **远程禁用**: 服务端可随时禁用某个卡密
- **使用统计**: 记录每个卡密的使用情况

### 服务端部署

```python
from scripts.license_server import LicenseServer

# 启动授权服务器
server = LicenseServer(host="0.0.0.0", port=8080)
server.start()
```

### API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/activate` | POST | 激活卡密 |
| `/api/verify` | POST | 验证授权状态 |
| `/api/heartbeat` | POST | 心跳检测 |
| `/api/disable` | POST | 禁用卡密 |
| `/api/stats` | GET | 使用统计 |

### 客户端集成

```python
from scripts.license_client import LicenseClient

# 客户端验证
client = LicenseClient(server_url="http://auth.example.com:8080")
result = client.activate("DNF-xxx")

if result.success:
    print("激活成功")
else:
    print(f"激活失败: {result.message}")
```

### 加密传输

```python
# 使用RSA+AES混合加密
from scripts.crypto_utils import HybridCrypto

crypto = HybridCrypto()
encrypted = crypto.encrypt(data)
decrypted = crypto.decrypt(encrypted)
```

## 模块八：授权加密强度升级

### 加密方案对比

| 方案 | 安全性 | 性能 | 适用场景 |
|------|--------|------|----------|
| Base64 | ⭐ | 极快 | 仅编码，无加密 |
| AES-256 | ⭐⭐⭐⭐ | 快 | 标准加密 |
| RSA-2048 | ⭐⭐⭐⭐⭐ | 慢 | 密钥交换 |
| **AES+RSA混合** | ⭐⭐⭐⭐⭐ | 快 | **推荐方案** |
| **AES+RSA+签名** | ⭐⭐⭐⭐⭐ | 快 | **最高安全** |

### AES+RSA混合加密

```python
from scripts.crypto_utils import HybridCrypto

# 初始化
crypto = HybridCrypto()

# 生成密钥对
crypto.generate_rsa_keys()

# 加密 (AES加密数据 + RSA加密AES密钥)
encrypted = crypto.hybrid_encrypt(license_data)

# 解密
decrypted = crypto.hybrid_decrypt(encrypted)
```

### 数字签名验证

```python
# 签名
signature = crypto.sign(license_data)

# 验证
valid = crypto.verify(license_data, signature)
```

### 完整加密流程

```
生成卡密
    ↓
AES-256加密卡密数据
    ↓
RSA-2048加密AES密钥
    ↓
生成数字签名
    ↓
输出: 加密数据 + 加密密钥 + 签名
```

## 模块九：授权破解自动化

### 一键分析+绕过

```python
from scripts.license_cracker import AutoLicenseCracker

# 全自动破解
cracker = AutoLicenseCracker("com.target.app")
result = cracker.auto_crack()

# 输出结果
print(f"验证类型: {result.auth_type}")
print(f"验证点数量: {result.checkpoint_count}")
print(f"绕过方案: {result.bypass_method}")
print(f"破解状态: {'成功' if result.success else '失败'}")
```

### 自动化流程

```
输入目标APK
    ↓
[1] 自动分析
    ├─→ 反编译APK
    ├─→ 搜索授权相关类/方法
    ├─→ 识别验证类型
    └─→ 定位所有验证点
    ↓
[2] 自动生成绕过方案
    ├─→ 根据验证类型选择策略
    ├─→ 生成Hook脚本
    ├─→ 生成Patch方案
    └─→ 生成配置文件修改方案
    ↓
[3] 自动执行绕过
    ├─→ 尝试Hook注入
    ├─→ 尝试内存Patch
    ├─→ 尝试配置修改
    └─→ 验证是否成功
    ↓
[4] 输出结果
    ├─→ 破解后的APK/配置
    ├─→ 破解报告
    └─→ 使用说明
```

### 智能策略选择

```python
def select_strategy(auth_type):
    """根据验证类型自动选择最优策略"""
    strategies = {
        "local_file": "modify_config",
        "shared_prefs": "hook_getboolean",
        "network_api": "mitm_proxy",
        "signature": "resign_apk",
        "machine_bind": "spoof_device",
        "timestamp": "hook_time",
        "encrypted": "find_key",
        "multi_check": "hook_all"
    }
    return strategies.get(auth_type, "generic_hook")
```

### 批量授权破解

```python
# 批量破解多个目标
targets = ["com.app1", "com.app2", "com.app3"]
results = AutoLicenseCracker.crack_batch(targets)

# 生成汇总报告
AutoLicenseCracker.generate_report(results)
```

## 模块十：仓库隐私管理

### 强制规则

涉及破解/逆向/游戏自动化的项目，**必须设为私有仓库**。

### 自动检查清单

```python
def check_repo_privacy():
    """检查仓库隐私设置"""
    sensitive_projects = [
        "apk-crack-engine",
        "dnf-gold-bot", 
        "wendao-gold-bot",
        "game-memory-module",
        "hearthstone-auto-bot",
    ]
    
    for project in sensitive_projects:
        status = check_gitee_visibility(project)
        if status == "public":
            print(f"⚠️ {project} 是公开仓库，必须改为私有!")
            open_repo_settings(project)
```

### Gitee操作

**创建私有仓库:**
1. 访问 https://gitee.com/projects/new
2. 填写仓库名
3. 选择 **私有仓库** 🔒
4. 创建

**修改已有仓库:**
- 访问 `https://gitee.com/<用户名>/<仓库>/settings`
- 改为私有

### 故障排查

| 错误 | 原因 | 解决 |
|------|------|------|
| 404 not found | 仓库不存在 | 先创建仓库 |
| 登录失效 | API认证过期 | 手动网页操作 |

完整指南: `references/repo-privacy-guide.md`

## 参考文档

| 文档 | 内容 |
|------|------|
| `references/ai-agent-loop.md` | **AI Agent五阶段循环工作流（感知→思考→执行→检查→修正）** |
| `references/shell-identification.md` | 壳类型识别与脱壳方案 |
| `references/network-bypass-guide.md` | 网络验证绕过详细指南 |
| `references/direct-execution-pattern.md` | 直接执行模式设计说明 |
| `references/apk-protection-matrix.md` | APK保护方案对比矩阵 |
| `references/macos-environment-setup.md` | macOS环境配置（brew不可用/网络受限场景） |
| `references/pyinstaller-exe-reverse.md` | **PyInstaller EXE逆向分析：提取源码、破解授权、重新打包** |
| `references/windows-pe-analysis.md` | **Windows PE文件分析：加壳识别、静态分析、脱壳流程、Electron破解** |
| `references/elf-injection-analysis.md` | **ELF注入型外挂分析：自解压脚本提取、SO库Patch、网络验证绕过** |
| `references/auth-system-design.md` | **授权系统设计：卡密生成/设备绑定/心跳验证/加密传输** |
| `references/batch-parallel-guide.md` | **批量并行破解指南** |
| `references/report-generation.md` | **破解报告生成规范** |
| `references/auto-fix-guide.md` | **环境自动修复手册** |
| `references/license-management.md` | **授权管理与保护指南** |
| `references/network-license-server.md` | **网络授权服务器部署指南** |
| `references/crypto-upgrade.md` | **授权加密强度升级方案** |
| `references/auto-crack-guide.md` | **授权破解自动化指南** |
| `references/repo-privacy-guide.md` | **仓库隐私设置指南（强制私有规则）** |
| `references/gitee-github-api-automation.md` | **Gitee/GitHub API批量操作指南（Token认证、仓库创建、可见性修改）** |
| `references/ios-ipa-crack.md` | **iOS IPA破解指南：解压分析、Patch验证、重签名安装** |
| `references/offline-license-system.md` | **离线授权码系统：无需联网的本地授权验证（生成/验证/iOS集成）** |

## 自进化系统

每次直接执行自动记录结果：

```python
from evolution_tracker import tracker

# 自动记录（内置于每个方法）
tracker.record_session(
    apk_name="飞猫助手",
    module="直接VIP破解",
    success=True,
    duration=45,
    method_used="auto_hook",
    errors=[],
    notes="自动枚举Hook成功"
)
```

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0 | 2026-06-09 | 基础版：生成脚本 |
| v2.0 | 2026-06-09 | Pro版：8大功能模块 |
| v2.1 | 2026-06-09 | 新增自进化系统 |
| v3.0 | 2026-06-09 | 直接执行版：输入APK直接输出破解结果 |
| v3.1 | 2026-06-09 | 新增深度分析模块：分析→策略→执行 |
| v4.0 | 2026-06-09 | 增强版：离线修改/模拟器/云手机/批量破解/智能重试 |
| v4.1 | 2026-06-09 | 新增环境预检清单 + macOS特定配置指南 + 网络诊断流程 |
| v5.0 | 2026-06-09 | AI Agent四阶段循环：思考→执行→检查→修正，闭环迭代自主纠错 |
| v5.1 | 2026-06-09 | 扩展适用范围：PyInstaller EXE、压缩包内嵌软件、游戏辅助脚本 |
| v5.2 | 2026-06-09 | 新增triggers覆盖压缩包/脚本/无限期使用等场景；优化实战案例 |
| v5.3 | 2026-06-09 | AI Agent五阶段循环(新增感知阶段)；智能环境诊断与自动修复；批量并行破解；破解报告自动生成；常见错误自动修复 |
| v5.4 | 2026-06-09 | 新增模块六：授权管理与保护；支持卡密生成/验证/机器绑定/期限控制/授权破解；新增8种授权方案分析 |
| **v5.5** | **2026-06-09** | **新增模块七：网络授权服务器；模块八：授权加密强度升级(AES+RSA混合)；模块九：授权破解自动化(一键分析+绕过)；模块十：仓库隐私管理(强制私有规则)** |
| **v6.0** | **2026-06-10** | **新增模块十一：iOS IPA破解；模块十二：离线授权码系统；新增ELF/SO库Patch技术；新增批量卡密生成+二维码导出；适用范围扩展至iOS/离线授权** |

## 实战案例

### 案例1: iOS IPA破解 (撤离者)

**目标**: 破解iOS游戏辅助收费验证
**类型**: iOS IPA应用 (含dylib动态库)
**验证方式**: 网络授权 + 本地验证

**破解步骤**:
1. 解压IPA → 提取Payload
2. 分析dylib → 定位授权验证函数
3. Patch服务器地址 → 指向本地
4. 重签名 → 使用个人证书
5. 安装测试 → TrollStore/Esign

**破解效果**:
- ✅ 网络验证已绕过
- ✅ 本地授权已解锁
- ✅ 全功能可用

### 案例2: 离线授权码生成 (撤离者)

**目标**: 为iOS游戏辅助生成离线授权码
**类型**: 离线授权系统

**实现功能**:
1. 生成加密授权码 (AES-256 + HMAC)
2. Base32格式化 (XXXX-XXXX-XXXX)
3. 批量生成 (CSV导出)
4. 二维码生成 (扫码输入)
5. iOS本地验证 (Objective-C++)

**技术栈**:
- Python: cryptography + qrcode
- iOS: CommonCrypto + Base32

### 案例3: PyInstaller EXE破解 (DNF脚本6.02A)

**目标**: 破解DNF自动搬砖脚本收费验证
**类型**: PyInstaller打包的Python程序 (97.4MB)
**卡密**: `fenghA9KPVL94P9SP805446TI4B`

**破解步骤**:
1. 识别程序类型 → PyInstaller打包
2. 提取Python源码 → pyinstxtractor
3. 反编译pyc文件 → uncompyle6
4. 定位验证函数 → 搜索auth/license/verify
5. Patch验证逻辑 → 强制返回True
6. 重新打包 → pyinstaller

**破解效果**:
- ✅ 卡密验证已绕过
- ✅ 授权有效期: 2099-12-31
- ✅ 可离线使用
- ✅ 无限期/永久使用

### 案例4: 压缩包内嵌软件破解

**目标**: ZIP压缩包内的收费脚本
**步骤**:
1. 解压ZIP → 提取内部文件
2. 分析文件类型 → EXE/APK/脚本
3. 按类型选择破解方案
4. 修改配置或Patch程序
5. 重新打包

### 案例5: 游戏辅助脚本破解

**目标**: 游戏自动化脚本的会员限制
**常见类型**:
- 按键精灵脚本 (.qm/.txt)
- 易语言程序 (.exe)
- Auto.js脚本 (.js)
- Lua脚本 (.lua)

**破解方法**:
- 配置文件修改 (config.ini)
- 注册表修改
- 网络验证绕过
- 内存Patch

### 案例6: ELF注入型外挂破解 (M7内核3.0)

**目标**: 破解Android ELF注入型外挂的授权验证
**类型**: 自解压Shell脚本 + gzip压缩ELF

**破解步骤**:
1. 识别自解压脚本 → file命令
2. 提取gzip部分 → 定位0x1f8b魔数
3. 解压ELF → gzip -cd
4. 分析ELF → strings搜索验证字符串
5. Patch服务器地址 → 修改硬编码URL
6. 重新压缩 → gzip + 重新打包sh

**破解效果**:
- ✅ 网络验证已绕过
- ✅ 授权检查已禁用
- ✅ 可离线使用

---

*APK Crack Engine Pro v6.0 - AI Agent五阶段循环版 | 感知→思考→执行→检查→修正 | 仓库隐私强制私有 | iOS/离线授权支持*
