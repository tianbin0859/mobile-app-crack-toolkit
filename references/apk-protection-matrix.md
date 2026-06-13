# APK保护方案与破解方法对照表

## 加固壳

| 厂商 | SO文件 | 特征 | 脱壳工具 | 难度 |
|------|--------|------|----------|------|
| 360加固 | libjiagu.so | 类加密、SO加密 | FRIDA-DEXDump / BlackDex | ⭐⭐ |
| 梆梆加固 | libsecexe.so | SO加密、反调试 | Youpk / FUPK3 | ⭐⭐⭐ |
| 爱加密 | libexec.so | DEX加密 | BlackDex / 自定义脚本 | ⭐⭐ |
| 腾讯乐固 | libshell.so | 混合加密 | FUPK3 | ⭐⭐⭐ |
| 百度加固 | libbaiduprotect.so | VMP虚拟化 | 内存Trace | ⭐⭐⭐⭐ |
| 阿里聚安全 | libmobisec.so | 动态加载 | Hook加载点 | ⭐⭐⭐ |
| 网易易盾 | libnesec.so | 指令加密 | 自定义脚本 | ⭐⭐⭐⭐ |
| 通付盾 | libegis.so | SO加固 | 内存Dump | ⭐⭐⭐ |
| 娜迦 | libedog.so | 多维度保护 | 综合方案 | ⭐⭐⭐⭐ |
| 海云安 | libchaosvmp.so | VMP | 指令还原 | ⭐⭐⭐⭐⭐ |
| 顶象技术 | libx3g.so | 设备指纹 | 设备模拟 | ⭐⭐⭐ |
| 盛大 | libapssec.so | 代码混淆 | 反混淆 | ⭐⭐⭐ |

## 网络验证

| 验证类型 | 特征 | 绕过方法 | 难度 |
|----------|------|----------|------|
| E盾 | 设备指纹+服务端校验 | Hook设备信息+伪造响应 | ⭐⭐⭐ |
| 天盾 | 行为检测+风险评分 | 模拟正常用户行为 | ⭐⭐⭐⭐ |
| MAPO | 多维度风控 | 代理池+设备农场 | ⭐⭐⭐⭐⭐ |
| SP | 短信验证 | 接码平台/Hook短信接口 | ⭐⭐ |
| 大禹盾 | 腾讯风控 | Xposed模块绕过 | ⭐⭐⭐⭐ |
| 定制盾 | 自定义算法 | 逆向算法+伪造 | ⭐⭐⭐⭐ |

## 脚本保护

| 类型 | 文件特征 | 解密方法 | 难度 |
|------|----------|----------|------|
| Lua gold混淆 | 文件头`86 4c 55 41` | Hook luaL_loadbufferx | ⭐⭐ |
| LuaJIT | 特定字节码 | luajit-decomp | ⭐⭐⭐ |
| 自定义Lua加密 | 文件头异常 | 找解密函数 | ⭐⭐⭐ |
| 按键精灵 | .q / .lua | 文件读取Hook | ⭐⭐ |
| 懒人精灵 | .l / .lua | 内存Dump | ⭐⭐ |
| EC易语言 | .e | 反编译 | ⭐⭐⭐ |
| JavaScript | .js | WebView Hook | ⭐⭐ |

## 加解密算法

| 算法 | 特征 | 密钥提取方法 |
|------|------|-------------|
| AES-ECB | 相同明文相同密文 | Hook SecretKeySpec |
| AES-CBC | 需要IV | Hook Cipher.init |
| AES-GCM | 认证标签 | Hook Cipher.doFinal |
| RSA | 公钥加密 | Hook X509EncodedKeySpec |
| DES | 56位密钥 | Hook DESKeySpec |
| 3DES | 112/168位密钥 | Hook DESedeKeySpec |
| MD5 | 固定128位输出 | 无需密钥 |
| SHA-256 | 固定256位输出 | 无需密钥 |
| Base64 | 可打印字符 | 无需密钥 |
| XOR | 简单异或 | 暴力破解 |
| 自定义 | 无标准特征 | 逆向算法 |
