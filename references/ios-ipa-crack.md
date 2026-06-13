# iOS IPA 破解指南

## 适用范围

- iOS应用安装包 (.ipa)
- 包含Mach-O可执行文件
- 包含动态库 (.dylib)
- 需要重签名安装

## IPA结构

```
Payload/
└── AppName.app/
    ├── Info.plist          # 应用配置
    ├── AppName             # Mach-O可执行文件
    ├── *.dylib             # 动态库
    ├── _CodeSignature/     # 签名文件
    └── *.framework/        # 框架
```

## 破解流程

### 1. 解压IPA

```bash
unzip app.ipa -d extracted/
```

### 2. 分析可执行文件

```bash
# 查看文件类型
file Payload/AppName.app/AppName
# 输出: Mach-O 64-bit executable arm64

# 查看动态库
file Payload/AppName.app/*.dylib
# 输出: Mach-O 64-bit dynamically linked shared library arm64
```

### 3. 提取字符串

```python
# 搜索关键字符串
strings Payload/AppName.app/AppName | grep -i "auth\|license\|vip\|verify"
strings Payload/AppName.app/*.dylib | grep -i "auth\|license\|vip\|verify"
```

### 4. Patch验证逻辑

**修改服务器地址**:
```python
with open('Payload/AppName.app/AppName', 'rb') as f:
    data = bytearray(f.read())

# 替换服务器地址
old_url = b'http://auth.server.com/\x00'
new_url = b'127.0.0.1\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

pos = data.find(old_url)
if pos != -1:
    data[pos:pos+len(new_url)] = new_url

with open('Payload/AppName.app/AppName', 'wb') as f:
    f.write(data)
```

### 5. 重签名

```bash
# 使用ios-deploy或Xcode重签名
# 或使用Esign/轻松签等工具

# 生成新签名
 codesign -f -s "iPhone Developer" Payload/AppName.app/

# 重新打包
zip -r cracked.ipa Payload/
```

## 安装方法

| 方法 | 条件 | 有效期 |
|------|------|--------|
| TrollStore | iOS 14.0-17.0 | 永久 |
| Esign/轻松签 | 个人证书 | 1年 |
| AltStore | 免费开发者 | 7天 |
| Xcode | 开发者账号 | 7天/1年 |

## 常见验证点

| 验证类型 | 位置 | 破解方法 |
|----------|------|----------|
| 网络验证 | dylib/可执行文件 | Patch服务器地址 |
| 本地授权 | Info.plist | 修改配置 |
| 签名验证 | _CodeSignature | 重签名 |
| 设备绑定 | Keychain | Hook或修改 |

## 工具链

| 工具 | 用途 |
|------|------|
| otool | Mach-O分析 |
| ldid | 伪签名 |
| codesign | 正式签名 |
| Frida | 动态Hook |
| objection | 运行时分析 |
