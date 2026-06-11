# Native SO库验证分析模式

## 适用场景

当APK使用原生SO库（libsdk.so / libauth.so / libverify.so 等）实现验证逻辑时，采用此分析模式。

**典型特征：**
- APK包含 `lib/arm64-v8a/libsdk.so` 或类似命名SO
- SO文件大小 > 1MB（包含验证逻辑）
- Java层仅做简单调用，核心逻辑在Native层
- 常见于：游戏辅助、工具类APP、商业软件

## 分析流程

### 1. 快速识别

```bash
# 查看APK内容
unzip -l target.apk | grep "lib.*\.so"

# 典型输出
#    5432109  lib/arm64-v8a/libsdk.so
#     123456  lib/arm64-v8a/libcocos2dlua.so
```

**判断标准：**
- 存在 `libsdk.so` / `libauth.so` / `libverify.so` → 高概率验证库
- SO大小 > 3MB → 可能包含完整验证逻辑
- 存在多个SO → 分析最大的那个（通常是主逻辑）

### 2. 字符串提取分析

```python
import re

def analyze_so_strings(so_path):
    """提取SO中的关键字符串"""
    with open(so_path, 'rb') as f:
        data = f.read()
    
    # 提取可打印字符串
    strings = re.findall(rb'[\x20-\x7e]{4,}', data)
    
    # 分类关键词
    categories = {
        'auth': [b'auth', b'verify', b'check', b'valid', b'license', b'vip'],
        'network': [b'http', b'https', b'api', b'server', b'host', b'url'],
        'crypto': [b'aes', b'rsa', b'md5', b'sha', b'encrypt', b'decrypt'],
        'time': [b'expire', b'time', b'date', b'period', b'days'],
    }
    
    results = {}
    for cat, keywords in categories.items():
        matches = [s for s in strings if any(kw in s.lower() for kw in keywords)]
        if matches:
            results[cat] = matches[:20]  # 每类最多20个
    
    return results
```

**关键字符串模式：**

| 模式 | 说明 | 破解方向 |
|------|------|----------|
| `auth` / `verify` / `check` | 验证函数名 | Hook这些函数 |
| `http://api.` / `https://` | 服务器地址 | 拦截/修改请求 |
| `expire` / `valid` | 过期检查 | 强制返回有效 |
| `license` / `vip` | 授权类型 | 修改授权状态 |

### 3. 导出函数分析

```bash
# 查看SO导出函数
readelf -s libsdk.so | grep -i "auth\|verify\|check\|valid\|init\|login"

# 或使用nm
nm -D libsdk.so | grep -i "auth\|verify\|check"
```

**常见导出函数名：**
- `Java_com_*_auth_*` - JNI验证方法
- `verify_license` / `check_auth` - 纯Native验证
- `init_sdk` / `sdk_init` - 初始化（可能含验证）
- `set_license_key` - 设置授权码

### 4. Frida Hook脚本生成

基于字符串分析结果，自动生成针对性Hook脚本：

```javascript
// 模板：SO库验证Hook
function hook_so_verify(libName) {
    console.log("[*] Hooking " + libName);
    
    var module = Process.findModuleByName(libName);
    if (!module) {
        console.log("[!] " + libName + " not found, waiting...");
        return;
    }
    
    // 策略1: Hook导出函数
    var exports = Module.enumerateExports(libName);
    exports.forEach(function(exp) {
        var name = exp.name;
        if (name.match(/verify|check|auth|valid|isVip/i)) {
            console.log("[+] Hooking export: " + name);
            Interceptor.attach(exp.address, {
                onLeave: function(retval) {
                    console.log("[+] " + name + " returned: " + retval);
                    retval.replace(1); // 强制返回true
                }
            });
        }
    });
    
    // 策略2: 内存扫描特征码
    var patterns = [
        "verify", "check_auth", "is_vip", "is_premium"
    ];
    
    patterns.forEach(function(p) {
        Memory.scan(module.base, module.size, 
            p.split('').map(c => c.charCodeAt(0).toString(16)).join(' '), {
            onMatch: function(addr, size) {
                console.log("[+] Pattern found at: " + addr);
            }
        });
    });
}

// 主入口
rpc.exports = {
    hookverify: function() {
        hook_so_verify("libsdk.so");
    }
};
```

### 5. Python自动破解工具

```python
#!/usr/bin/env python3
"""
SO库验证自动破解工具
自动连接设备 → 注入Hook → 绕过验证
"""

import frida
import sys
import time

class SOCracker:
    def __init__(self, package_name, so_name="libsdk.so"):
        self.package = package_name
        self.so_name = so_name
        self.session = None
        self.script = None
    
    def attach(self):
        """附加到目标进程"""
        device = frida.get_usb_device()
        pid = device.spawn([self.package])
        self.session = device.attach(pid)
        device.resume(pid)
        return self.session
    
    def inject_hook(self):
        """注入Hook脚本"""
        js_code = """
        function hookNative() {
            var module = Process.findModuleByName("%s");
            if (!module) {
                console.log("[!] Module not loaded yet, waiting...");
                setTimeout(hookNative, 1000);
                return;
            }
            
            console.log("[+] Module found at: " + module.base);
            
            // Hook所有可疑导出函数
            var exports = Module.enumerateExports("%s");
            var hooked = 0;
            
            exports.forEach(function(exp) {
                var name = exp.name;
                if (name.match(/verify|check|auth|valid|isVip|isPremium/i)) {
                    console.log("[+] Hooking: " + name);
                    try {
                        Interceptor.attach(exp.address, {
                            onLeave: function(retval) {
                                retval.replace(1);
                                console.log("[+] " + name + " -> forced true");
                            }
                        });
                        hooked++;
                    } catch(e) {
                        console.log("[!] Failed to hook " + name + ": " + e);
                    }
                }
            });
            
            console.log("[+] Hooked " + hooked + " functions");
        }
        
        // 延迟执行，等待SO加载
        setTimeout(hookNative, 2000);
        """ % (self.so_name, self.so_name)
        
        self.script = self.session.create_script(js_code)
        self.script.on('message', self.on_message)
        self.script.load()
    
    def on_message(self, message, data):
        """处理Frida消息"""
        if message['type'] == 'send':
            print("[Frida] " + message['payload'])
        else:
            print("[Frida] " + str(message))
    
    def crack(self):
        """执行破解"""
        print(f"[*] Starting crack for {self.package}")
        print(f"[*] Target SO: {self.so_name}")
        
        self.attach()
        self.inject_hook()
        
        print("[+] Hook injected, waiting for verification...")
        print("[*] Press Ctrl+C to stop")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Stopping...")
            self.cleanup()
    
    def cleanup(self):
        """清理资源"""
        if self.script:
            self.script.unload()
        if self.session:
            self.session.detach()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python so_cracker.py <package_name> [so_name]")
        sys.exit(1)
    
    pkg = sys.argv[1]
    so = sys.argv[2] if len(sys.argv) > 2 else "libsdk.so"
    
    cracker = SOCracker(pkg, so)
    cracker.crack()
```

## 无加固APK的SO分析模式

当APK**无常见加固保护**时（如Loader.apk案例），采用此简化流程：

### 快速判定标准

```bash
# 检查加固特征
unzip -l target.apk | grep -E "libjiagu|libmobisec|libtup|libegis|libchaosvmp|libnqshield|libexecmain|libexec"
# 无输出 = 无常见加固
```

### 简化分析流程

1. **解压APK** → 直接unzip，无需脱壳
2. **定位SO** → 找最大的/命名含auth/verify/sdk的SO
3. **字符串分析** → 用Python脚本批量提取关键词
4. **生成Hook** → 基于字符串结果自动生成Frida脚本
5. **执行破解** → Python自动连接+注入

### 与加固APK的区别

| 步骤 | 无加固APK | 加固APK |
|------|-----------|---------|
| 解压 | `unzip` 直接解压 | 需FRIDA-DEXDump脱壳 |
| SO分析 | 直接读取SO文件 | 可能加密/压缩 |
| Hook注入 | 标准Frida | 可能需绕过反Hook |
| 成功率 | 90%+ | 60-80% |
| 耗时 | 5-10分钟 | 30分钟+ |

## 实战案例：Loader.apk

**文件信息：**
- 包名：待确认（二进制manifest）
- 大小：~30MB
- 框架：Android原生 + Kotlin
- 保护：**无常见加固** ✅
- 核心库：`lib/arm64-v8a/libsdk.so` (5.4MB)

**分析结果：**

| 组件 | 发现 |
|------|------|
| libsdk.so | 包含 `auth`, `verify`, `check`, `valid`, `expire`, `http`, `api`, `server` |
| classes.dex | 使用WebView、加密算法 |
| 网络验证 | 确认存在 |

**破解策略：**

| 层级 | 方案 | 状态 |
|------|------|------|
| Java层 | Hook验证类方法 | ✅ 脚本已生成 |
| Native层 | Hook libsdk.so导出函数 | ✅ 脚本已生成 |
| 网络层 | 拦截OkHttp/HttpURLConnection | ✅ 脚本已生成 |

**生成文件：**
- `loader_crack.js` - Frida Hook脚本（Hook验证函数+拦截网络）
- `loader_auto_crack.py` - Python自动破解工具（直接执行）

## 常见SO命名规律

| 命名模式 | 用途 | 破解优先级 |
|----------|------|------------|
| `libsdk.so` | SDK核心库 | ⭐⭐⭐⭐⭐ |
| `libauth.so` | 授权验证 | ⭐⭐⭐⭐⭐ |
| `libverify.so` | 验证逻辑 | ⭐⭐⭐⭐⭐ |
| `libsecurity.so` | 安全模块 | ⭐⭐⭐⭐ |
| `libcrypto.so` | 加密算法 | ⭐⭐⭐ |
| `libnetwork.so` | 网络模块 | ⭐⭐⭐ |
| `libengine.so` | 游戏引擎 | ⭐⭐ |
| `libcocos2dlua.so` | Cocos2d-Lua | ⭐⭐ |
| `libunity.so` | Unity引擎 | ⭐ |

## 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| SO未找到 | 尚未加载 | 延迟Hook，等待加载完成 |
| Hook失败 | 函数被内联 | 尝试Hook调用点而非函数本身 |
| 验证仍生效 | 多验证点 | 检查是否有其他SO也含验证 |
| 应用崩溃 | Hook参数不匹配 | 检查函数签名，使用正确的Interceptor |
| Frida连接失败 | 设备未Root | 使用模拟器或云手机 |

## 相关参考

- `references/elf-injection-analysis.md` - ELF注入型外挂专项分析
- `references/shell-identification.md` - 壳类型识别
- `references/network-bypass-guide.md` - 网络验证绕过
