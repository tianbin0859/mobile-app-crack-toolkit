# APK 静态分析速查手册

静态分析 Android APK 的实用流程，无需运行设备即可提取关键信息。

## 适用场景

- 快速判断 APK 性质（游戏辅助/自动化工具/恶意软件）
- 提取内置脚本、资源、配置文件
- 识别加固/加壳特征
- 分析第三方 SDK 和依赖

## 基础信息提取

```bash
# 文件大小和基本信息
ls -lh app.apk
file app.apk

# 查看 ZIP 内容（不解压）
unzip -l app.apk | head -50

# 提取关键文件
unzip -o app.apk AndroidManifest.xml classes.dex META-INF/CERT.RSA -d extract/
```

## 快速定性分析

### 1. 识别 Auto.js 框架

特征字符串：
```
org.autojs.plugin.sdk
org.autojs
```

Auto.js 应用通常包含：
- `assets/*.lua` 或 `assets/*.js` 脚本
- `libassist.so`（Lua 运行时）
- `libopencv_java*.so`（图像识别）
- `libsc*.so`（ScreenshotClient 截屏）

### 2. 识别游戏自动化工具

特征组合：
```
OpenCV (libopencv_java*.so) + 截屏库 (libsc*.so) + Lua/JS 脚本
```

常见游戏脚本文件：
```
assets/script.lr        # ZIP 包，含 Lua 脚本
assets/*.lua            # 直接存放的脚本
assets/proxy.apk        # 子插件/代理
```

### 3. 识别加固/加壳

| 特征 | 说明 |
|------|------|
| `libjiagu*.so` | 360加固 |
| `libmobisec*.so` | 阿里加固 |
| `libprotect*.so` | 腾讯加固 |
| `libbaiduprotect*.so` | 百度加固 |
| `libnqshield*.so` | 网易易盾 |
| `classes.dex` 极小 | 原始 dex 被加密/隐藏 |
| 多个 `libsc*.so` | 可能是分段加载的 dex |

### 4. 提取字符串情报

```bash
# 网络相关
strings classes.dex | grep -iE "(http|api|url|server|host|token|key|secret)"

# 包名/类名
strings classes.dex | grep -iE "(com\.[a-z]|cn\.[a-z]|net\.[a-z])" | sort | uniq

# 游戏相关关键词
strings classes.dex | grep -iE "(jd|淘宝|taobao|pdd|拼多多|游戏|game|辅助|脚本|plugin)"

# 框架识别
strings classes.dex | grep -iE "(autojs|lua|unity|unreal|cocos|egret)"
```

## 资源提取

### 提取 assets

```bash
unzip -o app.apk 'assets/*' -d assets_extract/
```

### 处理加密/压缩的资源包

Auto.js 的 `script.lr` 是 ZIP 包，但文件名可能使用 GBK 编码：

```python
import zipfile

with zipfile.ZipFile('script.lr', 'r') as z:
    for name in z.namelist():
        try:
            # 尝试 GBK 解码（中文文件名）
            decoded = name.encode('cp437').decode('gbk')
            print(decoded)
        except:
            print(name)
        
        # 提取内容
        data = z.read(name)
        # 处理...
```

### 提取 so 库分析

```bash
# 列出所有 so
unzip -l app.apk | grep '\.so'

# 提取并分析
unzip -o app.apk 'lib/armeabi-v7a/*.so' -d libs/

# 检查每个 so 的特征
for f in libs/lib/armeabi-v7a/*.so; do
    echo "=== $(basename $f) ==="
    strings "$f" | grep -iE "(dex|android|lua|opencv|unity)" | head -5
done
```

## 证书分析

```bash
# 提取证书
unzip -o app.apk META-INF/CERT.RSA -d cert/

# 查看证书信息
keytool -printcert -file cert/META-INF/CERT.RSA

# 注意自签名证书 = 非官方渠道分发
```

## 常见 APK 类型速查

| 类型 | 特征文件 | 特征字符串 |
|------|----------|-----------|
| Auto.js 自动化 | `script.lr`, `libassist.so` | `org.autojs`, `lua_` |
| 游戏辅助 | `libopencv*.so`, `libsc*.so` | `ScreenshotClient`, `findImage` |
| 电商抢购 | `libjd*.so`, 京东相关类 | `com.jd`, `seckill`, `抢购` |
| 微信插件 | `libwechat*.so` | `com.tencent.mm` |
| 加固应用 | `libjiagu*.so` | 极小 classes.dex |
| 正常应用 | 标准结构 | 无异常 so |

## 分析报告模板

```markdown
## APK 分析报告

**基本信息**
- 包名：从 AndroidManifest.xml 提取
- 大小：XX MB
- 日期：XXXX-XX-XX
- 证书：自签名/官方

**技术栈**
- 框架：Auto.js / Unity / 原生
- 图像识别：OpenCV / 无
- 脚本引擎：Lua / JavaScript / 无
- 截屏方案：ScreenshotClient / MediaProjection / 无

**功能推测**
- 目标应用：京东/淘宝/游戏名称
- 自动化类型：点击/滑动/识别/协议

**风险等级**
- 加固：是/否
- 敏感权限：列表
- 网络通信：HTTP/HTTPS/自定义
```

## 注意事项

1. **中文编码问题**：ZIP 内文件名可能使用 GBK，直接用 `unzip` 会乱码，需用 Python 的 `cp437->gbk` 转换
2. **script.lr 文件**：Auto.js 的脚本包本质是 ZIP，扩展名 `.lr` 是伪装
3. **libsc*.so 系列**：ScreenshotClient 是 Android 系统截屏 API，多个版本 so 对应不同 Android API 级别
4. **proxy.apk**：可能是子插件或更新模块，需单独分析
