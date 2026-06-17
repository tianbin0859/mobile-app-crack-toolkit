# 网络抓包 SSL Pinning 绕过实战指南

## 适用场景
- 手游/APP 网络协议分析
- 拦截 HTTPS 请求，分析 API
- 绕过证书固定（SSL Pinning）

## 核心工具链

| 工具 | 用途 | 平台 |
|------|------|------|
| Fiddler | HTTP/HTTPS 代理 | Windows |
| Charles Proxy | 跨平台代理 | All |
| mitmproxy | 命令行代理 | All |
| frida | SSL Pinning 绕过 | All |
| Objection | 自动化 SSL Pinning 绕过 | Android/iOS |
| Android-SSL-Trust-Killer | Android 证书固定绕过 | Android |
| SSL Kill Switch 2 | iOS 证书固定绕过 | iOS |

## 标准流程

### 1. 基础代理设置
```bash
# mitmproxy 启动
mitmproxy --listen-port 8080

# 或自动保存到文件
mitmdump -w traffic.mitm

# 设备设置代理
# Android: WiFi -> 修改网络 -> 代理 -> 手动 10.0.0.1:8080
# iOS: WiFi -> 配置代理 -> 手动
```

### 2. 安装 mitmproxy 证书
```bash
# 导出证书
mitmproxy --options
# 访问 http://mitm.it 下载证书

# Android
adb push mitmproxy-ca-cert.cer /sdcard/
adb shell am start -a android.intent.action.VIEW file:///sdcard/mitmproxy-ca-cert.cer

# iOS
# 通过 Safari 访问 http://mitm.it 安装
# 设置 -> 通用 -> 关于 -> 证书信任设置 -> 启用 mitmproxy
```

### 3. 使用 Objection 自动绕过 SSL Pinning
```bash
# 安装
pip install objection

# 自动绕过（Android）
objection --gadget com.game.package explore
android sslpinning disable

# 自动绕过（iOS）
objection --gadget com.game.package explore
ios sslpinning disable
```

### 4. 使用 Frida 手动绕过（Android）
```javascript
// ssl_pinning_bypass.js
Java.perform(function() {
    // 方法1：绕过 OkHttp 证书固定
    try {
        var CertificatePinner = Java.use("okhttp3.CertificatePinner");
        CertificatePinner.check.overload('java.lang.String', 'java.util.List').implementation = function(hostname, certificates) {
            console.log("[+] OkHttp check bypassed for: " + hostname);
            return;
        };
    } catch(e) {
        console.log("[-] OkHttp not found");
    }
    
    // 方法2：绕过 X509TrustManager
    try {
        var X509TrustManager = Java.use("javax.net.ssl.X509TrustManager");
        var SSLContext = Java.use("javax.net.ssl.SSLContext");
        
        var TrustManager = Java.registerClass({
            name: "com.crack.TrustManager",
            implements: [X509TrustManager],
            methods: {
                checkClientTrusted: function(chain, authType) {},
                checkServerTrusted: function(chain, authType) {},
                getAcceptedIssuers: function() { return []; }
            }
        });
        
        var TrustManagers = [TrustManager.$new()];
        var SSLContext_init = SSLContext.init.overload(
            "[Ljavax.net.ssl.KeyManager;", 
            "[Ljavax.net.ssl.TrustManager;", 
            "java.security.SecureRandom"
        );
        
        SSLContext_init.implementation = function(km, tm, random) {
            console.log("[+] SSLContext.init() hooked");
            SSLContext_init.call(this, km, TrustManagers, random);
        };
    } catch(e) {
        console.log("[-] X509TrustManager hook failed: " + e);
    }
    
    // 方法3：绕过 WebViewClient
    try {
        var WebViewClient = Java.use("android.webkit.WebViewClient");
        WebViewClient.onReceivedSslError.implementation = function(view, handler, error) {
            console.log("[+] WebView SSL error bypassed");
            handler.proceed();
        };
    } catch(e) {
        console.log("[-] WebViewClient not found");
    }
});
```

### 5. 使用 Frida 绕过（iOS）
```javascript
// ios_ssl_bypass.js
var module = Module.findExportByName(null, "SSLHandshake");
Interceptor.attach(module, {
    onLeave: function(retval) {
        console.log("[+] SSLHandshake hooked, forcing success");
        retval.replace(0);  // errSSLWouldBlock = 0, force success
    }
});

// 绕过 AFNetworking
var AFURLConnectionOperation = ObjC.classes.AFURLConnectionOperation;
if (AFURLConnectionOperation) {
    var setAllowsInvalidSSLCertificate = AFURLConnectionOperation["- setAllowsInvalidSSLCertificate:"];
    Interceptor.attach(setAllowsInvalidSSLCertificate.implementation, {
        onEnter: function(args) {
            console.log("[+] AFNetworking SSL validation disabled");
            args[2] = ptr(1);  // YES
        }
    });
}
```

### 6. 自动化 Python 脚本
```python
#!/usr/bin/env python3
import subprocess
import frida
import sys

class SSLBypass:
    def __init__(self, package_name: str):
        self.package = package_name
        self.device = frida.get_usb_device()
        
    def bypass_android(self):
        """Android SSL Pinning 绕过"""
        script_code = '''
        Java.perform(function() {
            // OkHttp
            try {
                var CertificatePinner = Java.use("okhttp3.CertificatePinner");
                CertificatePinner.check.overload('java.lang.String', 'java.util.List').implementation = function() {
                    console.log("[+] OkHttp bypassed");
                };
            } catch(e) {}
            
            // TrustManager
            try {
                var X509TrustManager = Java.use("javax.net.ssl.X509TrustManager");
                var SSLContext = Java.use("javax.net.ssl.SSLContext");
                var TrustManager = Java.registerClass({
                    name: "com.crack.TrustManager",
                    implements: [X509TrustManager],
                    methods: {
                        checkClientTrusted: function() {},
                        checkServerTrusted: function() {},
                        getAcceptedIssuers: function() { return []; }
                    }
                });
                var TrustManagers = [TrustManager.$new()];
                SSLContext.init.overload(
                    "[Ljavax/net/ssl/KeyManager;",
                    "[Ljavax/net/ssl/TrustManager;",
                    "java/security/SecureRandom"
                ).implementation = function(km, tm, random) {
                    SSLContext.init.call(this, km, TrustManagers, random);
                };
            } catch(e) {}
            
            console.log("[+] SSL Pinning bypass active");
        });
        '''
        
        pid = self.device.spawn([self.package])
        session = self.device.attach(pid)
        script = session.create_script(script_code)
        script.load()
        self.device.resume(pid)
        
        print(f"[+] SSL Pinning bypassed for {self.package}")
        sys.stdin.read()
    
    def bypass_ios(self):
        """iOS SSL Pinning 绕过"""
        script_code = '''
        var SSLHandshake = Module.findExportByName(null, "SSLHandshake");
        Interceptor.attach(SSLHandshake, {
            onLeave: function(retval) {
                retval.replace(0);
            }
        });
        console.log("[+] iOS SSL Pinning bypass active");
        '''
        
        pid = self.device.spawn([self.package])
        session = self.device.attach(pid)
        script = session.create_script(script_code)
        script.load()
        self.device.resume(pid)
        
        print(f"[+] SSL Pinning bypassed for {self.package}")
        sys.stdin.read()

if __name__ == "__main__":
    bypass = SSLBypass("com.game.package")
    bypass.bypass_android()
```

## 常见问题

### Q: 绕过失败，应用仍检测证书？
- 使用自定义 TrustManager 的 Hook
- 检查是否有证书固定库（如 TrustKit）
- 尝试 Hook 更低层的 SSL 函数

### Q: 应用使用自研加密？
- Hook 加密/解密函数
- 分析 so 库中的加密逻辑
- 使用 frida-trace 跟踪加密调用

### Q: 有双向证书验证（mTLS）？
- 需要提取客户端证书
- 从应用资源或 KeyStore 中提取

## 参考项目
- Objection: https://github.com/sensepost/objection (⭐ 3.8k)
- frida-multiple-unpinning: https://github.com/httptoolkit/frida-android-unpinning (⭐ 1.2k)
- SSL Kill Switch 2: https://github.com/nabla-c0d3/ssl-kill-switch2 (⭐ 2.1k)
