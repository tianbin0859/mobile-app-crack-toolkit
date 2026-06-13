# 网络验证绕过指南

## 一、抓包分析

### 1.1 工具选择

| 工具 | 平台 | 特点 |
|------|------|------|
| Charles | 跨平台 | 功能全面，支持重写 |
| Fiddler | Windows | 免费，插件丰富 |
| Burp Suite | 跨平台 | 安全测试专用 |
| HttpCanary | Android | 移动端抓包 |
| Wireshark | 跨平台 | 底层协议分析 |

### 1.2 SSL Pinning绕过

**方法一：Frida脚本（推荐）**
```javascript
Java.perform(function() {
    // 通用SSL绕过
    var X509TrustManager = Java.use('javax.net.ssl.X509TrustManager');
    var SSLContext = Java.use('javax.net.ssl.SSLContext');
    
    var TrustManager = Java.registerClass({
        name: 'com.example.TrustManager',
        implements: [X509TrustManager],
        methods: {
            checkClientTrusted: function() {},
            checkServerTrusted: function() {},
            getAcceptedIssuers: function() { return []; }
        }
    });
    
    var TrustManagers = [TrustManager.$new()];
    var SSLContext_init = SSLContext.init.overload(
        '[Ljavax.net.ssl.KeyManager;', 
        '[Ljavax.net.ssl.TrustManager;', 
        'java.security.SecureRandom'
    );
    SSLContext_init.implementation = function(km, tm, random) {
        SSLContext_init.call(this, km, TrustManagers, random);
    };
    
    // OkHttp专用
    try {
        var CertificatePinner = Java.use("okhttp3.CertificatePinner");
        CertificatePinner.check.overload('java.lang.String', 'java.util.List').implementation = function() {
            console.log("[*] OkHttp certificate check bypassed");
        };
    } catch(e) {}
    
    // WebView SSL错误忽略
    try {
        var WebViewClient = Java.use("android.webkit.WebViewClient");
        WebViewClient.onReceivedSslError.implementation = function(view, handler, error) {
            handler.proceed();
        };
    } catch(e) {}
});
```

**方法二：Xposed模块**
- SSLUnpinning
- TrustMeAlready

**方法三：修改APK**
1. 反编译APK
2. 找到证书校验代码
3. 删除或修改校验逻辑
4. 重打包签名

### 1.3 代理设置

```bash
# 设置全局代理
adb shell settings put global http_proxy 192.168.1.100:8888

# 取消代理
adb shell settings put global http_proxy :0

# 针对单个APP代理（需要Root）
# 使用ProxyDroid或Postern
```

## 二、响应伪造

### 2.1 Hook网络请求库

```javascript
// OkHttp响应修改
Java.perform(function() {
    var Response = Java.use("okhttp3.Response");
    var ResponseBody = Java.use("okhttp3.ResponseBody");
    var MediaType = Java.use("okhttp3.MediaType");
    
    // 创建修改后的响应
    Response.body.implementation = function() {
        var original = this.body.value;
        var content = original.string();
        
        // 修改逻辑
        var modified = content
            .replace('"status":0', '"status":1')
            .replace('"vip":false', '"vip":true')
            .replace('"expire_time":"2024-01-01"', '"expire_time":"2099-12-31"');
        
        return ResponseBody.create(
            MediaType.parse("application/json"),
            modified
        );
    };
});
```

### 2.2 使用Charles Map Local

1. 抓取正常响应
2. 保存为本地文件
3. 修改响应内容
4. 设置Charles Map Local规则

### 2.3 中间人攻击

```python
# 使用mitmproxy编写拦截脚本
from mitmproxy import http

def response(flow: http.HTTPFlow) -> None:
    if "api.example.com" in flow.request.pretty_host:
        # 修改响应
        flow.response.text = flow.response.text.replace(
            '"is_vip":false',
            '"is_vip":true'
        )
```

## 三、设备指纹绕过

### 3.1 常见设备指纹参数

| 参数 | 获取方式 | Hook目标 |
|------|----------|----------|
| IMEI | TelephonyManager.getDeviceId() | TelephonyManager |
| IMSI | TelephonyManager.getSubscriberId() | TelephonyManager |
| MAC | WifiInfo.getMacAddress() | WifiInfo |
| Android ID | Settings.Secure.ANDROID_ID | Settings$Secure |
| Serial | Build.SERIAL | Build |
| UUID | 自定义生成 | 应用内方法 |

### 3.2 设备指纹Hook脚本

```javascript
Java.perform(function() {
    // IMEI/IMSI
    var TelephonyManager = Java.use("android.telephony.TelephonyManager");
    
    TelephonyManager.getDeviceId.overload().implementation = function() {
        return "8661740136xxxxxx";
    };
    
    TelephonyManager.getSubscriberId.implementation = function() {
        return "460001234567890";
    };
    
    // MAC地址
    var WifiInfo = Java.use("android.net.wifi.WifiInfo");
    WifiInfo.getMacAddress.implementation = function() {
        return "02:00:00:00:00:00";
    };
    
    // Android ID
    var Secure = Java.use("android.provider.Settings$Secure");
    Secure.getString.implementation = function(cr, name) {
        if (name === "android_id") {
            return "1234567890abcdef";
        }
        return this.getString(cr, name);
    };
    
    // Build信息
    var Build = Java.use("android.os.Build");
    Build.SERIAL.value = "unknown";
    
    // 随机化设备信息（每次不同）
    function randomIMEI() {
        var imei = "86";
        for (var i = 0; i < 12; i++) {
            imei += Math.floor(Math.random() * 10);
        }
        return imei;
    }
    
    // 使用随机值
    TelephonyManager.getDeviceId.overload().implementation = function() {
        return randomIMEI();
    };
});
```

## 四、风控绕过

### 4.1 行为模拟

```javascript
// 模拟正常用户点击
function simulateClick(x, y) {
    Java.perform(function() {
        var MotionEvent = Java.use("android.view.MotionEvent");
        
        var downTime = Date.now();
        var eventTime = Date.now();
        
        var downEvent = MotionEvent.obtain(downTime, eventTime, 
            0, x, y, 0);
        var upEvent = MotionEvent.obtain(downTime, eventTime + 100, 
            1, x, y, 0);
            
        // 分发事件
        var currentActivity = getCurrentActivity();
        currentActivity.dispatchTouchEvent(downEvent);
        currentActivity.dispatchTouchEvent(upEvent);
    });
}
```

### 4.2 代理池

```python
# 使用代理池轮换IP
import requests
import random

proxy_pool = [
    "http://user:pass@ip1:port",
    "http://user:pass@ip2:port",
    # ...
]

def get_proxy():
    return random.choice(proxy_pool)

def request_with_proxy(url):
    proxy = get_proxy()
    return requests.get(url, proxies={"http": proxy, "https": proxy})
```

### 4.3 设备农场

使用Android模拟器或云手机批量创建虚拟设备：
- 夜神模拟器
- 雷电模拟器
- 云手机平台

## 五、常见验证接口分析

### 5.1 卡密验证

典型流程：
1. 用户输入卡密
2. APP发送卡密到服务器
3. 服务器返回验证结果
4. APP保存验证状态

绕过方法：
- Hook验证接口，强制返回成功
- 修改本地验证状态存储
- 重放已验证的卡密响应

### 5.2 时间限制验证

典型流程：
1. 获取服务器时间
2. 计算剩余时间
3. 到期后限制功能

绕过方法：
- Hook时间获取接口
- 修改本地时间计算逻辑
- 拦截到期响应

### 5.3 设备绑定验证

典型流程：
1. 获取设备唯一标识
2. 发送到服务器绑定
3. 验证设备是否授权

绕过方法：
- Hook设备标识获取
- 使用固定设备ID
- 模拟已授权设备
