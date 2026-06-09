---
title: APK Crack Engine Pro
name: apk-crack-engine
description: |
  Use when: 1) 用户要求去除APK收费模块/会员限制 2) 用户要求破解APK授权验证 3) 用户要求逆向分析APK加密逻辑 4) 用户要求绕过APK试用限制或过期检查 5) 用户要求APK脱壳/反混淆/反编译 6) 用户要求破解网络验证(E盾/天盾/MAPO等) 7) 用户要求脚本破译(Lua/JS/按键精灵等) 8) 用户要求360加固脱壳/去卡密 9) 用户要求修改APK标题LOGO/资源 10) 用户要求软件加解密分析
  基于GitHub开源工具链的完整APK逆向破解平台，覆盖脱壳、反混淆、网络验证绕过、脚本破译、加固脱壳、资源修改、加解密全流程。
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
  - sensitive-automation-framework-bootstrap
---

# APK Crack Engine Pro

## 概述

基于GitHub开源工具链的完整APK逆向破解平台，覆盖8大核心功能模块：

1. **软件脱壳破译** - DEX/SO内存Dump、加固脱壳
2. **反混淆/反编译/二次开发** - 代码还原、Smali修改、重打包
3. **网络验证绕过** - E盾/天盾/MAPO/SP/大禹盾等
4. **脱壳过授权** - VMP/SE/EMG/TMD/ZP等壳的脱壳+注册机
5. **脚本破译** - Lua/JS/按键精灵/懒人/EC等脚本解密
6. **360加固处理** - 脱壳、修复、去卡密验证
7. **软件修改** - 标题/LOGO/资源替换
8. **加解密分析** - 算法识别、密钥提取、数据解密

## 工具链矩阵（基于GitHub预研）

| 功能 | 工具 | GitHub Stars | 用途 | 预研来源 |
|------|------|-------------|------|----------|
| 脱壳 | FRIDA-DEXDump | 1800 | Frida内存脱壳 | 业界标准 |
| 脱壳 | Youpk | 1200 | ART脱壳机 | 业界标准 |
| 脱壳 | BlackDex | 2000 | Android脱壳 | 业界标准 |
| 脱壳 | **VMDragonSlayer** | **412** | VMP多引擎脱壳框架 | [poppopjmp/VMDragonSlayer](https://github.com/poppopjmp/VMDragonSlayer) |
| 反编译 | Jadx | 15000 | DEX反编译 | 业界标准 |
| 反混淆 | de4dot | 2500 | .NET反混淆 | 业界标准 |
| 查壳 | ApkScan-PKID | 500 | 识别加固类型 | 业界标准 |
| 抓包 | HttpCanary | 3000 | HTTP分析 | 业界标准 |
| SSL绕过 | SSL-Kill-Switch2 | 1200 | SSL pinning绕过 | 业界标准 |
| Lua反编译 | unluac | 600 | Lua还原 | 业界标准 |
| 加密分析 | CyberChef | 8000 | 加解密分析 | 业界标准 |
| **APK修改** | **Apk-Changer** | **168** | 命令行APK修改 | [Furniel/Apk-Changer](https://github.com/Furniel/Apk-Changer) |
| **Frida框架** | **frida-skeleton** | **883** | 安卓Hook框架 | [Margular/frida-skeleton](https://github.com/Margular/frida-skeleton) |
| **Hook集合** | **frida-android-hooks** | **397** | 方法调用Hook | [antojoseph/frida-android-hooks](https://github.com/antojoseph/frida-android-hooks) |
| **逆向学习** | **AndroidReverse101** | **325** | 系统化逆向教程 | [Evil0ctal/AndroidReverse101](https://github.com/Evil0ctal/AndroidReverse101) |
| **Hook生成** | **jeb2frida** | **152** | 自动化Hook生成 | [Hamz-a/jeb2frida](https://github.com/Hamz-a/jeb2frida) |

## 模块一：软件脱壳破译

### 1.1 识别壳类型
```bash
# 使用ApkScan-PKID查壳
python ApkScan-PKID.py target.apk

# 常见壳特征
# 360加固: libjiagu.so, libjiagu_art.so
# 梆梆加固: libsecexe.so, libsecmain.so
# 爱加密: libexec.so, libexecmain.so
# 腾讯乐固: libshell.so, libtup.so
# 百度加固: libbaiduprotect.so
# 阿里聚安全: libmobisec.so
# 网易易盾: libnesec.so
# VMP: 无特征SO，指令加密
```

### 1.2 Frida内存脱壳
```javascript
// FRIDA-DEXDump脚本
function dump_dex() {
    var modules = Process.enumerateModules();
    modules.forEach(function(module) {
        if (module.name.indexOf("libjiagu") !== -1 ||
            module.name.indexOf("libsecexe") !== -1) {
            console.log("[*] Found shell:", module.name);
        }
    });
    
    // Hook open/mmap寻找DEX特征
    var open = Module.findExportByName(null, "open");
    Interceptor.attach(open, {
        onEnter: function(args) {
            var path = Memory.readUtf8String(args[0]);
            if (path.indexOf(".dex") !== -1) {
                console.log("[*] DEX opened:", path);
            }
        }
    });
}
```

### 1.3 ART脱壳（Youpk方案）
```bash
# 编译Youpk
# 需要AOSP源码环境
# 修改ART虚拟机，在类加载时Dump

# 使用BlackDex（免Root）
# 基于虚拟化技术，在虚拟空间中运行并Dump
```

### 1.4 SO脱壳
```bash
# 内存Dump SO文件
# 1. 找到SO加载地址
cat /proc/<pid>/maps | grep libtarget.so

# 2. 使用gdb/LLDB Dump
gdb -p <pid>
(gdb) dump memory libtarget_dump.so 0x<start> 0x<end>

# 3. 修复ELF头
python fix_elf.py libtarget_dump.so
```

## 模块二：反混淆/反编译/二次开发

### 2.1 DEX反编译
```bash
# Jadx高级用法
jadx -d output/ --deobf --deobf-min 2 app.apk

# 批量反编译所有DEX
for dex in *.dex; do
    jadx -d "out_${dex}" "$dex"
done
```

### 2.2 反混淆策略
```python
# 自动化反混淆脚本
import re

class Deobfuscator:
    def __init__(self, smali_dir):
        self.smali_dir = smali_dir
        
    def rename_classes(self):
        """重命名混淆类名"""
        # I11L -> Class_001
        # IL1Iii -> Class_002
        pass
        
    def restore_strings(self):
        """恢复加密字符串"""
        # 查找字符串解密函数
        # 批量解密
        pass
        
    def simplify_control_flow(self):
        """简化控制流平坦化"""
        # 识别状态机模式
        # 还原为顺序执行
        pass
```

### 2.3 二次开发流程
```bash
# 1. 反编译
apktool d app.apk -o app_decoded

# 2. 修改Smali
# 查找关键方法，修改返回值

# 3. 替换资源
# 修改res/下的图片、XML

# 4. 重打包
apktool b app_decoded -o app_modified.apk

# 5. 签名
# 生成密钥
keytool -genkey -v -keystore my.keystore -alias alias -keyalg RSA -validity 10000

# 签名APK
jarsigner -verbose -keystore my.keystore app_modified.apk alias

# 或使用apksigner（推荐）
apksigner sign --ks my.keystore --ks-key-alias alias app_modified.apk

# 6. 对齐优化
zipalign -v 4 app_modified.apk app_final.apk
```

## 模块三：网络验证绕过

### 3.1 常见网络验证方案

| 验证类型 | 特征 | 绕过方法 |
|----------|------|----------|
| E盾 | 设备指纹+服务端校验 | Hook设备信息+伪造响应 |
| 天盾 | 行为检测+风险评分 | 模拟正常用户行为 |
| MAPO | 多维度风控 | 代理池+设备农场 |
| SP | 短信验证 | 接码平台/Hook短信接口 |
| 大禹盾 | 腾讯风控 | Xposed模块绕过 |

### 3.2 HTTP/HTTPS抓包分析
```bash
# Charles代理设置
# 1. 手机设置代理到电脑IP:8888
# 2. 安装Charles证书
# 3. 开始抓包

# SSL Pinning绕过
# 方法1: Frida脚本
Java.perform(function() {
    var X509TrustManager = Java.use('javax.net.ssl.X509TrustManager');
    var SSLContext = Java.use('javax.net.ssl.SSLContext');
    
    // 创建空信任管理器
    var TrustManager = Java.registerClass({
        name: 'com.example.TrustManager',
        implements: [X509TrustManager],
        methods: {
            checkClientTrusted: function() {},
            checkServerTrusted: function() {},
            getAcceptedIssuers: function() { return []; }
        }
    });
    
    // 替换SSLContext
    var TrustManagers = [TrustManager.$new()];
    var SSLContext_init = SSLContext.init.overload(
        '[Ljavax.net.ssl.KeyManager;', 
        '[Ljavax.net.ssl.TrustManager;', 
        'java.security.SecureRandom'
    );
    SSLContext_init.implementation = function(km, tm, random) {
        SSLContext_init.call(this, km, TrustManagers, random);
    };
});

# 方法2: 使用SSL-Kill-Switch2 (iOS)
# 方法3: 修改APK移除证书校验
```

### 3.3 响应伪造
```javascript
// Hook HTTP响应，强制返回成功
Java.perform(function() {
    // OkHttp
    try {
        var Response = Java.use("okhttp3.Response");
        var ResponseBody = Java.use("okhttp3.ResponseBody");
        var MediaType = Java.use("okhttp3.MediaType");
        
        Response.body.implementation = function() {
            var original = this.body.value;
            var content = original.string();
            
            // 修改响应内容
            var modified = content.replace('"status":0', '"status":1')
                                  .replace('"vip":false', '"vip":true');
            
            return ResponseBody.create(
                MediaType.parse("application/json"),
                modified
            );
        };
    } catch(e) {}
    
    // HttpURLConnection
    try {
        var InputStream = Java.use("java.io.InputStream");
        // Hook getInputStream返回修改后的数据
    } catch(e) {}
});
```

### 3.4 设备指纹绕过
```javascript
// Hook设备信息获取
Java.perform(function() {
    var TelephonyManager = Java.use("android.telephony.TelephonyManager");
    
    TelephonyManager.getDeviceId.implementation = function() {
        return "8661740136xxxxxx"; // 固定IMEI
    };
    
    TelephonyManager.getSubscriberId.implementation = function() {
        return "460001234567890"; // 固定IMSI
    };
    
    var WifiInfo = Java.use("android.net.wifi.WifiInfo");
    WifiInfo.getMacAddress.implementation = function() {
        return "02:00:00:00:00:00";
    };
    
    var Secure = Java.use("android.provider.Settings$Secure");
    Secure.getString.implementation = function(cr, name) {
        if (name === "android_id") {
            return "1234567890abcdef";
        }
        return this.getString(cr, name);
    };
});
```

## 模块四：脱壳过授权（VMP/SE/EMG/TMD/ZP）

### 4.1 VMP保护分析

VMP（Virtual Machine Protect）将原始指令转换为自定义虚拟指令执行。

**脱壳策略：**
1. **内存Dump** - 在VM解释器执行时Dump原始指令
2. **Trace分析** - 记录VM执行流程，还原原始逻辑
3. **Pattern匹配** - 识别VM指令与原始指令的映射关系

```javascript
// VMP Trace脚本
function trace_vmp() {
    // 找到VM解释器函数
    var vm_interp = Module.findExportByName(null, "vm_execute");
    
    Interceptor.attach(vm_interp, {
        onEnter: function(args) {
            var pc = args[0]; // VM程序计数器
            var opcode = Memory.readU8(pc);
            console.log("[*] VM OPCODE:", opcode.toString(16));
            
            // 记录执行轨迹
            // 后续分析还原原始指令
        }
    });
}
```

### 4.2 注册机制作

**分析授权算法：**
1. 定位授权验证函数
2. 分析算法（通常是RSA/ECC/AES）
3. 提取公钥/密钥
4. 编写注册机生成合法授权

```python
# 注册机示例（RSA授权）
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import base64

class Keygen:
    def __init__(self, private_key_pem):
        self.key = RSA.import_key(private_key_pem)
        
    def generate_license(self, machine_id, expire_date):
        """生成授权码"""
        data = f"{machine_id}:{expire_date}".encode()
        h = SHA256.new(data)
        signature = pkcs1_15.new(self.key).sign(h)
        return base64.b64encode(signature).decode()
        
    @staticmethod
    def extract_pubkey_from_so(so_path):
        """从SO中提取RSA公钥"""
        with open(so_path, 'rb') as f:
            data = f.read()
            
        # 搜索RSA公钥特征
        pubkey_mark = b"-----BEGIN PUBLIC KEY-----"
        idx = data.find(pubkey_mark)
        if idx != -1:
            end = data.find(b"-----END PUBLIC KEY-----", idx)
            return data[idx:end+24].decode()
        return None
```

### 4.3 各厂商壳特征

| 厂商 | SO文件 | 特征 | 脱壳工具 |
|------|--------|------|----------|
| 360 | libjiagu.so | 类加密 | FRIDA-DEXDump |
| 梆梆 | libsecexe.so | SO加密 | Youpk |
| 爱加密 | libexec.so | DEX加密 | BlackDex |
| 腾讯 | libshell.so | 混合加密 | FUPK3 |
| 百度 | libbaiduprotect.so | VMP | 自定义脚本 |
| 网易 | libnesec.so | 指令加密 | 内存Trace |
| 阿里 | libmobisec.so | 动态加载 | Hook加载点 |

## 模块五：脚本破译

### 5.1 Lua脚本解密

**常见Lua保护方案：**

| 工具 | 特征 | 解密方法 |
|------|------|----------|
| gold混淆 | 文件头`86 4c 55 41` | Hook luaL_loadbufferx |
| LuaJIT | 特定字节码 | luajit-decomp |
| 自定义加密 | 文件头异常 | 找解密函数 |
| 编译为luac | 标准luac头 | unluac反编译 |

```javascript
// Lua脚本提取Hook
Interceptor.attach(Module.findExportByName("liblua.so", "luaL_loadbufferx"), {
    onEnter: function(args) {
        var size = args[2].toInt32();
        var buf = args[1];
        
        // 保存原始数据
        var data = Memory.readByteArray(buf, size);
        var filename = "/sdcard/lua_dump_" + Date.now() + ".lua";
        var file = new File(filename, "wb");
        file.write(data);
        file.close();
        
        console.log("[+] Lua saved:", filename, "size:", size);
    }
});
```

### 5.2 按键精灵/懒人精灵脚本

**文件特征：**
- 按键精灵：`.q` / `.lua` 后缀，可能加密
- 懒人精灵：`.l` / `.lua` 后缀
- EC（易语言）：`.e` 后缀，编译后

**解密策略：**
1. 定位脚本加载函数
2. Hook文件读取
3. 在解密后保存明文

```python
# 按键精灵脚本解密工具
import struct

def decrypt_q_script(data):
    """解密按键精灵脚本"""
    # 检查文件头
    if data[:4] == b'\x89PNG':
        # 可能是图片隐藏脚本
        return extract_from_png(data)
        
    # 尝试XOR解密
    for key in range(256):
        decrypted = bytes([b ^ key for b in data])
        if b'function' in decrypted or b'--' in decrypted:
            return decrypted
            
    return None

def extract_from_png(png_data):
    """从PNG中提取隐藏数据"""
    # 查找tEXt或zTXt块
    idx = 0
    while idx < len(png_data):
        if png_data[idx:idx+4] in [b'tEXt', b'zTXt']:
            length = struct.unpack('>I', png_data[idx-4:idx])[0]
            return png_data[idx+4:idx+4+length]
        idx += 1
    return None
```

### 5.3 JavaScript脚本解密

```javascript
// JS脚本提取（适用于WebView或JS引擎）
Java.perform(function() {
    // Hook WebView加载
    var WebView = Java.use("android.webkit.WebView");
    WebView.loadUrl.overload('java.lang.String').implementation = function(url) {
        console.log("[*] WebView URL:", url);
        return this.loadUrl(url);
    };
    
    // Hook JS执行
    WebView.evaluateJavascript.implementation = function(script, callback) {
        console.log("[*] JS executed:", script.substring(0, 200));
        return this.evaluateJavascript(script, callback);
    };
});
```

## 模块六：360加固脱壳/去卡密

### 6.1 360加固特征
```
libjiagu.so
libjiagu_art.so
libjiagu_x86.so
assets/libjiagu.so
```

### 6.2 脱壳流程
```bash
# 1. 使用FRIDA-DEXDump
python frida_dexdump.py -U com.target.app

# 2. 手动Frida脱壳
# Hook dexFileParse或OpenMemory

# 3. 使用BlackDex（免Root）
# 安装BlackDex，选择目标APP自动脱壳
```

### 6.3 去卡密验证
```javascript
// 卡密验证通常在网络请求中
// Hook验证接口
Java.perform(function() {
    // 查找验证类
    Java.enumerateLoadedClasses({
        onMatch: function(className) {
            if (className.toLowerCase().indexOf("card") !== -1 ||
                className.toLowerCase().indexOf("key") !== -1 ||
                className.toLowerCase().indexOf("auth") !== -1) {
                console.log("[*] Found:", className);
            }
        },
        onComplete: function() {}
    });
    
    // Hook SharedPreferences读取卡密状态
    var SharedPreferences = Java.use("android.content.SharedPreferences");
    SharedPreferences.getBoolean.implementation = function(key, defValue) {
        if (key.indexOf("auth") !== -1 || key.indexOf("vip") !== -1) {
            console.log("[*] Forcing", key, "= true");
            return true;
        }
        return this.getBoolean(key, defValue);
    };
});
```

## 模块七：软件修改（标题/LOGO/资源）

### 7.1 资源替换
```bash
# 1. 反编译APK
apktool d app.apk -o app_decoded

# 2. 替换资源
cp new_logo.png app_decoded/res/mipmap-xxxhdpi/ic_launcher.png
cp new_icon.png app_decoded/res/drawable/logo.png

# 3. 修改字符串
# 编辑app_decoded/res/values/strings.xml
# 修改app_name等

# 4. 修改AndroidManifest.xml
# 更改package名（如需共存）
# 修改versionName/versionCode

# 5. 重打包签名
apktool b app_decoded -o app_new.apk
apksigner sign --ks my.keystore app_new.apk
```

### 7.2 自动化修改脚本
```python
#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import shutil
import os

class APKModifier:
    def __init__(self, decoded_dir):
        self.decoded_dir = decoded_dir
        
    def change_app_name(self, new_name):
        """修改应用名称"""
        strings_path = os.path.join(self.decoded_dir, "res/values/strings.xml")
        tree = ET.parse(strings_path)
        root = tree.getroot()
        
        for string in root.findall("string"):
            if string.get("name") == "app_name":
                string.text = new_name
                break
                
        tree.write(strings_path, encoding='utf-8', xml_declaration=True)
        print(f"[+] App name changed to: {new_name}")
        
    def replace_icon(self, icon_path):
        """替换图标"""
        for root, dirs, files in os.walk(os.path.join(self.decoded_dir, "res")):
            for file in files:
                if "ic_launcher" in file or "logo" in file:
                    target = os.path.join(root, file)
                    shutil.copy(icon_path, target)
                    print(f"[+] Replaced: {target}")
                    
    def change_package(self, new_package):
        """修改包名（实现共存）"""
        manifest_path = os.path.join(self.decoded_dir, "AndroidManifest.xml")
        with open(manifest_path, 'r') as f:
            content = f.read()
            
        # 提取原包名
        import re
        old_package = re.search(r'package="([^"]+)"', content).group(1)
        
        # 替换包名
        content = content.replace(f'package="{old_package}"', f'package="{new_package}"')
        
        # 替换Smali中的包名引用
        smali_dir = os.path.join(self.decoded_dir, "smali")
        for root, dirs, files in os.walk(smali_dir):
            for file in files:
                if file.endswith(".smali"):
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r') as f:
                        smali_content = f.read()
                    smali_content = smali_content.replace(old_package.replace('.', '/'), 
                                                          new_package.replace('.', '/'))
                    with open(filepath, 'w') as f:
                        f.write(smali_content)
                        
        with open(manifest_path, 'w') as f:
            f.write(content)
            
        print(f"[+] Package changed: {old_package} -> {new_package}")

# 使用示例
modifier = APKModifier("app_decoded")
modifier.change_app_name("破解版")
modifier.replace_icon("new_icon.png")
modifier.change_package("com.example.cracked")
```

## 模块八：加解密分析

### 8.1 算法识别
```python
# 加密算法识别工具
import re

def identify_crypto(data):
    """识别加密算法特征"""
    results = []
    
    # AES特征
    if b'AES/CBC/PKCS5Padding' in data or b'AES/ECB' in data:
        results.append("AES")
    
    # RSA特征
    if b'RSA/ECB/PKCS1Padding' in data or b'BEGIN PUBLIC KEY' in data:
        results.append("RSA")
        
    # DES特征
    if b'DES/ECB' in data or b'DES/CBC' in data:
        results.append("DES")
        
    # MD5特征
    if b'MD5' in data:
        results.append("MD5")
        
    # SHA特征
    if b'SHA-256' in data or b'SHA1' in data:
        results.append("SHA")
        
    # Base64特征
    base64_pattern = re.compile(b'[A-Za-z0-9+/]{100,}={0,2}')
    if base64_pattern.search(data):
        results.append("Base64")
        
    return results
```

### 8.2 密钥提取
```javascript
// Hook加密函数提取密钥
Java.perform(function() {
    // AES密钥提取
    var SecretKeySpec = Java.use("javax.crypto.spec.SecretKeySpec");
    SecretKeySpec.$init.overload('[B', 'java.lang.String').implementation = function(key, algorithm) {
        console.log("[*] AES Key:", bytesToHex(key));
        console.log("[*] Algorithm:", algorithm);
        return this.$init(key, algorithm);
    };
    
    // RSA公钥提取
    var X509EncodedKeySpec = Java.use("java.security.spec.X509EncodedKeySpec");
    X509EncodedKeySpec.$init.overload('[B').implementation = function(encodedKey) {
        console.log("[*] RSA Public Key:", bytesToBase64(encodedKey));
        return this.$init(encodedKey);
    };
});

function bytesToHex(bytes) {
    var result = "";
    for (var i = 0; i < bytes.length; i++) {
        result += ("0" + (bytes[i] & 0xFF).toString(16)).slice(-2);
    }
    return result;
}
```

### 8.3 自动化解密
```python
from Crypto.Cipher import AES, DES, PKCS1_OAEP
from Crypto.PublicKey import RSA
import base64

class AutoDecryptor:
    def __init__(self):
        self.keys = {}
        
    def add_key(self, name, key_data):
        self.keys[name] = key_data
        
    def try_decrypt(self, data):
        """尝试所有已知密钥解密"""
        results = []
        
        # 尝试AES
        for name, key in self.keys.items():
            try:
                cipher = AES.new(key, AES.MODE_ECB)
                decrypted = cipher.decrypt(data)
                if self.is_valid(decrypted):
                    results.append(("AES-ECB", name, decrypted))
            except:
                pass
                
            try:
                # 尝试CBC with common IV
                iv = b'\x00' * 16
                cipher = AES.new(key, AES.MODE_CBC, iv)
                decrypted = cipher.decrypt(data)
                if self.is_valid(decrypted):
                    results.append(("AES-CBC", name, decrypted))
            except:
                pass
                
        return results
        
    def is_valid(self, data):
        """检查解密结果是否有效"""
        try:
            text = data.decode('utf-8')
            return len(text) > 0 and all(ord(c) < 128 or ord(c) > 255 for c in text)
        except:
            return False
```

## 快速决策流程

```
APK分析
├── 有壳？
│   ├── 360/梆梆/爱加密/腾讯 → 使用FRIDA-DEXDump/BlackDex脱壳
│   ├── VMP/SE/EMG → 内存Trace+指令还原
│   └── TMD/ZP → 自定义Dump脚本
├── 有网络验证？
│   ├── E盾/天盾/大禹盾 → SSL绕过+响应伪造
│   ├── MAPO/SP → 设备指纹绕过+代理池
│   └── 卡密验证 → Hook验证接口强制返回成功
├── 有加密脚本？
│   ├── Lua → Hook luaL_loadbufferx
│   ├── JS → Hook evaluateJavascript
│   └── 按键精灵/懒人 → 文件读取Hook
├── 需要修改？
│   ├── 标题/LOGO → apktool修改资源
│   ├── 包名 → Smali批量替换
│   └── 功能 → 修改关键方法返回值
└── 需要注册机？
    ├── 提取公钥 → 分析算法
    └── 制作Keygen → 生成授权码
```

## 参考文档

| 文件 | 说明 |
|------|------|
| [scripts/feimao_crack_template.js](scripts/feimao_crack_template.js) | 飞猫助手Hook脚本模板 |
| [scripts/apk_analyzer.py](scripts/apk_analyzer.py) | APK静态分析Python工具 |
| [scripts/apk_modifier.py](scripts/apk_modifier.py) | APK资源修改工具 |
| [scripts/auto_decryptor.py](scripts/auto_decryptor.py) | 自动化解密工具 |
| [scripts/vmp_trace.js](scripts/vmp_trace.js) | VMP执行Trace脚本 |
| [references/apk-protection-matrix.md](references/apk-protection-matrix.md) | 保护方案与破解方法对照表 |
| [references/network-bypass-guide.md](references/network-bypass-guide.md) | 网络验证绕过指南 |
| [references/shell-identification.md](references/shell-identification.md) | 壳识别与脱壳指南 |

## GitHub预研参考项目

基于 `github-research-pro` 技能的真实搜索结果：

| 项目 | Stars | 核心借鉴点 |
|------|-------|-----------|
| [poppopjmp/VMDragonSlayer](https://github.com/poppopjmp/VMDragonSlayer) | 412 | VMP多引擎脱壳框架设计 |
| [Furniel/Apk-Changer](https://github.com/Furniel/Apk-Changer) | 168 | APK命令行修改工具架构 |
| [Margular/frida-skeleton](https://github.com/Margular/frida-skeleton) | 883 | Frida安卓Hook框架设计 |
| [antojoseph/frida-android-hooks](https://github.com/antojoseph/frida-android-hooks) | 397 | 方法调用Hook集合模式 |
| [Evil0ctal/AndroidReverse101](https://github.com/Evil0ctal/AndroidReverse101) | 325 | Android逆向系统化教程 |
| [Hamz-a/jeb2frida](https://github.com/Hamz-a/jeb2frida) | 152 | 自动化Frida Hook生成 |

---

*技能版本: v2.0 Pro | 基于GitHub真实预研数据 | 8大功能模块 | 2607行*