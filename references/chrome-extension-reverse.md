# Chrome 扩展逆向实战指南

## 适用场景
- 破解 Chrome 扩展付费功能
- 修改扩展行为（去广告、解锁功能）
- 逆向分析扩展通信逻辑

## 核心工具链

| 工具 | 用途 |
|------|------|
| Chrome 开发者模式 | 加载未打包扩展 | chrome://extensions |
| CRX Extractor | 在线解包 | https://crxextractor.com |
| 7-Zip | 本地解包 | 7z x extension.crx |
| Extension Source Viewer | 查看源码 | Chrome 商店 |

## 标准流程

### 1. 获取扩展源码
```bash
# 方法1：从 Chrome 商店下载 CRX
# 访问 https://clients2.google.com/service/update2/crx?response=redirect&prodversion=119.0&x=id%3DEXTENSION_ID%26installsource%3Dondemand%26uc
# 替换 EXTENSION_ID

# 方法2：从已安装扩展复制
# Windows: %LOCALAPPDATA%\Google\Chrome\User Data\Default\Extensions\<ID>\<VERSION>
# macOS: ~/Library/Application Support/Google/Chrome/Default/Extensions/<ID>/<VERSION>

# 方法3：直接解包 CRX
cp extension.crx extension.zip
unzip extension.zip -d ./extension_source/
```

### 2. 分析 manifest.json
```json
{
  "manifest_version": 3,
  "name": "Target Extension",
  "version": "1.0.0",
  "permissions": ["storage", "activeTab"],
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [{
    "matches": ["<all_urls>"],
    "js": ["content.js"]
  }],
  "action": {
    "default_popup": "popup.html"
  }
}
```

### 3. 定位授权逻辑
```bash
# 搜索付费/授权关键词
grep -r "isPremium\|isPro\|license\|trial" ./extension_source/ --include="*.js"

# 常见模式
# background.js: 处理授权验证
# popup.js: 显示付费界面
# content.js: 功能注入
```

### 4. 修改授权逻辑（MV3 示例）
```javascript
// background.js - 原代码
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "checkLicense") {
        fetch('https://api.example.com/verify', {
            method: 'POST',
            body: JSON.stringify({key: request.key})
        }).then(r => r.json()).then(data => {
            sendResponse({valid: data.valid});
        });
        return true;
    }
});

// 修改后 - 直接返回 valid
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "checkLicense") {
        sendResponse({valid: true, premium: true});
        return true;
    }
});
```

### 5. 修改功能限制
```javascript
// content.js - 原代码
if (!isPremium) {
    document.querySelectorAll('.premium-feature').forEach(el => el.remove());
}

// 修改后
// 删除所有功能限制代码
// 或改为：
const isPremium = true;  // 强制 true
```

### 6. 加载修改后的扩展
```bash
# 1. 打开 chrome://extensions
# 2. 开启"开发者模式"
# 3. 点击"加载已解压的扩展程序"
# 4. 选择 ./extension_source/ 目录

# 或使用命令行加载（开发）
chrome --load-extension=./extension_source/
```

### 7. 重新打包（可选）
```bash
# Chrome 扩展打包
chrome --pack-extension=./extension_source/ --pack-extension-key=./key.pem
# 输出 extension_source.crx
```

## MV3 特殊处理

### Service Worker 限制
- MV3 使用 Service Worker 替代 Background Page
- Service Worker 不持久运行，需用事件驱动
- 修改时注意生命周期

### 内容安全策略
```json
// manifest.json 可能有 CSP 限制
"content_security_policy": {
    "extension_pages": "script-src 'self'; object-src 'self'"
}
```

## 常见问题

### Q: 扩展 ID 变化？
- 从 Chrome 商店安装的扩展 ID 固定
- 开发者模式加载的扩展 ID 基于路径
- 保持相同路径可维持相同 ID

### Q: 扩展自动更新覆盖修改？
- 禁用自动更新：chrome://extensions -> 详情 -> 关闭"自动更新"
- 或修改版本号高于官方

### Q: 有 WASM 模块？
- WASM 可逆向为 WAT（文本格式）
- 使用 wabt 工具：wasm2wat

## 参考
- Chrome Extension 文档: https://developer.chrome.com/docs/extensions/
- CRX 格式: https://developer.chrome.com/docs/extensions/mv3/linux_hosting/#packaging
