# Arkari混淆器检测与处理

## 识别特征

Arkari是基于LLVM的混淆器，编译后的SO库具有以下特征：

### 字符串特征
```
Arkari - Obfuscator based on LLVM
clang version XX.X.X (git@github.com:KomiMoe/Arkari.git)
```

### 混淆技术
- 控制流平坦化 (Control Flow Flattening)
- 虚假控制流 (Bogus Control Flow)
- 指令替换 (Instruction Substitution)
- 字符串加密/剥离 (String Encryption)
- 间接跳转 (Indirect Branching)

### 导出函数特征
- 函数名通常保留原始名称（如 `JNI_OnLoad`, `Mundo_Activate_SDK`）
- 内部函数名被混淆为随机字符串
- 无可见的字符串表（运行时解密）

## 检测方法

```bash
# 1. 检查编译器字符串
strings libxxx.so | grep -i "Arkari\|LLVM"

# 2. 检查导出符号
nm -D libxxx.so | head -20

# 3. 检查节区名（可能被修改）
objdump -h libxxx.so | grep -E "\.text\|\.data\|\.rodata"

# 4. 检查字符串密度（加密后字符串极少）
strings libxxx.so | wc -l
# 正常SO: 数千条字符串
# Arkari混淆: 通常 < 100条（仅保留必要的外部符号）
```

## 破解策略

### 策略1: Frida动态Hook（推荐）
由于静态分析困难，动态Hook是最有效方案：

```javascript
// Hook导出函数强制返回成功
Interceptor.attach(Module.findExportByName("libxxx.so", "TargetFunction"), {
    onLeave: function(retval) {
        retval.replace(0x1); // 强制返回成功
    }
});
```

### 策略2: 内存Dump
运行时从内存中提取解密后的代码：

```javascript
// 找到SO加载基址
var base = Module.findBaseAddress("libxxx.so");

// 读取内存中的解密代码
var size = 0x10000; // 根据实际大小调整
var data = Memory.readByteArray(base, size);

// 保存到文件
var file = new File("/sdcard/dumped.so", "wb");
file.write(data);
file.close();
```

### 策略3: 符号恢复
通过运行时分析恢复函数名：

```javascript
// 枚举所有导出符号
Module.enumerateExports("libxxx.so").forEach(function(exp) {
    console.log("Export: " + exp.name + " @ " + exp.address);
});
```

## 实战案例: Loader.apk (com.lethal.visionx)

### 目标信息
- 包名: `com.lethal.visionx`
- 主Activity: `UpdateActivity` (无启动界面)
- 核心SO: `libid1z5u62rg48rrchhw3.so`
- 导出函数: `JNI_OnLoad`, `Mundo_Activate_SDK`

### 破解步骤
1. 识别Arkari混淆 → 字符串极少，仅2个导出函数
2. 确认目标进程 → `com.lethal.visionx:stub1` (PID 15388)
3. Frida注入Hook → 拦截 `Mundo_Activate_SDK`
4. 强制返回1 → 绕过授权验证

### 关键发现
- 应用无启动Activity，通过Service/Receiver启动
- SO库使用Arkari混淆，但导出函数名保留
- 授权验证集中在 `Mundo_Activate_SDK` 单一函数
- Hook后应用正常运行，所有功能解锁

## 注意事项

1. **版本匹配**: Frida Python库版本必须与手机frida-server版本一致
   - 常见错误: `frida.ProtocolError: unable to communicate with remote frida-server`
   - 解决: `pip install frida==<server_version>`

2. **进程选择**: 多进程应用需选择正确进程注入
   - 主进程: `com.lethal.visionx`
   - 子进程: `com.lethal.visionx:stub1` (通常在此注入)

3. **无Activity应用**: 部分应用无启动Activity，需手动启动Service
   ```bash
   adb shell am start -n com.package/.ServiceActivity
   ```
