# Rust程序特定Patch技巧

> 来源：黑曼巴6.16逆向分析（Rust二进制27种方案失败经验）
> 适用：所有Rust编译的二进制程序逆向分析

## 一、Rust二进制特征

### 1.1 识别Rust程序

```bash
# 方法1：字符串搜索
strings target.exe | grep -i "rust\|rustc\|cargo"

# 方法2：符号搜索
nm target.exe | grep -i "rust"

# 方法3：特征函数
# Rust程序通常包含以下特征函数：
# - __rust_alloc
# - __rust_dealloc
# - __rust_realloc
# - __rust_alloc_zeroed

# 方法4：运行时库
# 检查是否链接以下库：
# - std-*.dll (Rust标准库)
# - rustls-*.dll (TLS库)
# - tokio-*.dll (异步运行时)
```

### 1.2 Rust编译特征

| 特征 | 说明 | 影响 |
|------|------|------|
| 名称混淆 | 函数名被混淆为短字符串 | 难以识别功能 |
| 内联优化 | 小函数被内联 | 无法单独Hook |
|  panic处理 | 使用panic而非异常 | 需要特殊处理 |
| 所有权系统 | 严格的内存管理 | Patch时需保持所有权 |
| 生命周期 | 编译时检查 | 运行时Patch不影响 |

## 二、Patch策略

### 2.1 策略1：函数返回值修改

**目标：** 修改函数返回值，绕过验证

**适用：** 验证函数返回bool或Result

```rust
// 原始Rust代码
fn is_authorized() -> bool {
    // 验证逻辑
    return false; // 未授权
}

// Patch目标：强制返回true
```

**Patch方法：**
```python
# 使用x64dbg或Cheat Engine
# 找到函数地址
# 修改汇编代码

# 原始汇编：
# mov eax, 0  # 返回false
# ret

# Patch后：
# mov eax, 1  # 返回true
# ret

# 或者使用Frida
import frida

session = frida.attach("target.exe")
script = session.create_script("""
Interceptor.attach(ptr("0xADDRESS"), {
    onLeave: function(retval) {
        retval.replace(1);  // 强制返回true
    }
});
""")
script.load()
```

### 2.2 策略2：条件跳转修改

**目标：** 修改条件跳转，改变程序流程

**适用：** 验证后的分支判断

```rust
// 原始Rust代码
if is_authorized() {
    enable_features();
} else {
    show_error();
}

// Patch目标：跳过验证，直接执行enable_features
```

**Patch方法：**
```assembly
; 原始汇编
; call is_authorized
; test eax, eax
; jz show_error      ; 如果false，跳转到错误
; call enable_features

; Patch后
; call is_authorized
; test eax, eax
; nop                ; 移除跳转
; nop
; call enable_features
```

### 2.3 策略3：函数体替换

**目标：** 完全替换函数实现

**适用：** 复杂验证逻辑

```python
# 使用Frida完全替换函数
script = session.create_script("""
Interceptor.replace(ptr("0xADDRESS"), new NativeCallback(function() {
    return 1;  // 永远返回true
}, 'int', []));
""")
```

### 2.4 策略4：全局变量修改

**目标：** 修改全局状态变量

**适用：** 程序使用全局变量存储验证状态

```rust
// 原始Rust代码
static mut IS_VIP: bool = false;

fn check_vip() {
    if unsafe { IS_VIP } {
        // VIP功能
    }
}
```

**Patch方法：**
```javascript
// 找到全局变量地址
var is_vip_addr = Module.findExportByName(null, "IS_VIP");
// 或者通过内存搜索

// 修改全局变量
Memory.writeU8(is_vip_addr, 1);
```

### 2.5 策略5：字符串常量修改

**目标：** 修改硬编码字符串

**适用：** 服务器地址、验证密钥等

```rust
// 原始Rust代码
const SERVER_URL: &str = "https://api.example.com";
```

**Patch方法：**
```python
# 1. 搜索字符串
strings = target.search_memory("https://api.example.com")

# 2. 修改字符串
# 注意：新字符串长度必须 <= 原字符串长度
target.write_memory(strings[0], b"http://127.0.0.1\x00")

# 如果新字符串更长，需要找到更大的空间或扩展.data段
```

## 三、Rust特定技巧

### 3.1 处理Result类型

```rust
// Rust的Result类型
enum Result<T, E> {
    Ok(T),
    Err(E),
}

// 在内存中通常表示为：
// Ok:  [tag=0, value]
// Err: [tag=1, error]
```

**Patch方法：**
```javascript
// Hook返回Result的函数
Interceptor.attach(result_function, {
    onLeave: function(retval) {
        // Result在内存中的布局
        var result_ptr = retval;
        var tag = Memory.readU8(result_ptr);
        
        if (tag === 1) {  // Err
            // 修改为Ok
            Memory.writeU8(result_ptr, 0);
            // 设置Ok的值
            Memory.writePointer(result_ptr.add(8), ptr(1));
        }
    }
});
```

### 3.2 处理Option类型

```rust
// Rust的Option类型
enum Option<T> {
    Some(T),
    None,
}

// 在内存中：
// Some: [tag=0, value]
// None: [tag=1]
```

**Patch方法：**
```javascript
Interceptor.attach(option_function, {
    onLeave: function(retval) {
        var option_ptr = retval;
        var tag = Memory.readU8(option_ptr);
        
        if (tag === 1) {  // None
            // 修改为Some
            Memory.writeU8(option_ptr, 0);
            // 设置Some的值
        }
    }
});
```

### 3.3 处理panic

```rust
// Rust的panic处理
// 当遇到不可恢复错误时，程序会panic

// 黑曼巴中：当检测到Frida时，程序可能panic
```

**Patch方法：**
```javascript
// Hook panic处理函数
// Rust的panic通常调用 std::panicking::rust_panic

Interceptor.attach(Module.findExportByName(null, "rust_panic"), {
    onEnter: function(args) {
        console.log("[*] Panic intercepted, preventing exit");
        // 阻止panic执行
        // 可能需要修改程序计数器或堆栈
    }
});
```

### 3.4 处理异步代码

```rust
// Rust异步代码使用async/await
// 编译后生成状态机代码

// 黑曼巴使用tokio运行时
```

**Patch方法：**
```javascript
// 异步函数编译后变为状态机
// 需要找到状态机的入口点

// Hook tokio的运行时函数
Interceptor.attach(Module.findExportByName(null, "tokio::runtime::Runtime::block_on"), {
    onEnter: function(args) {
        console.log("[*] Async runtime intercepted");
    }
});
```

## 四、黑曼巴特定Patch点

### 4.1 已识别的Patch点

```
基于逆向分析，黑曼巴可能的Patch点：

1. 验证函数
   - 地址：需要动态分析确定
   - 功能：返回验证状态
   - Patch：强制返回已验证

2. 网络检查函数
   - 功能：检查网络连接状态
   - Patch：强制返回已连接

3. Frida检测函数
   - 功能：检测Frida存在
   - Patch：强制返回未检测到

4. 配置解析函数
   - 功能：解析服务器配置
   - Patch：修改解析结果
```

### 4.2 Patch脚本模板

```python
import frida
import sys

def main(target_process):
    session = frida.attach(target_process)
    
    script = session.create_script("""
    // 1. Hook验证函数
    var verify_addr = Module.findExportByName(null, "verify_function");
    if (verify_addr) {
        Interceptor.attach(verify_addr, {
            onLeave: function(retval) {
                console.log("[*] Verify function intercepted");
                retval.replace(1);  // 强制返回true
            }
        });
    }
    
    // 2. Hook网络检查
    var netcheck_addr = Module.findExportByName(null, "check_network");
    if (netcheck_addr) {
        Interceptor.attach(netcheck_addr, {
            onLeave: function(retval) {
                retval.replace(1);  // 强制返回已连接
            }
        });
    }
    
    // 3. Hook Frida检测
    var frida_check_addr = Module.findExportByName(null, "check_frida");
    if (frida_check_addr) {
        Interceptor.attach(frida_check_addr, {
            onLeave: function(retval) {
                retval.replace(0);  // 强制返回未检测到
            }
        });
    }
    
    console.log("[+] All hooks installed");
    """)
    
    script.load()
    print("[*] Press Ctrl+C to stop")
    sys.stdin.read()

if __name__ == "__main__":
    main("BlackMamba.exe")
```

## 五、工具推荐

### 5.1 Windows平台

| 工具 | 用途 | 场景 |
|------|------|------|
| x64dbg | 调试器 | 动态分析、Patch |
| Cheat Engine | 内存编辑 | 运行时修改 |
| IDA Pro | 静态分析 | 反编译、识别函数 |
| Ghidra | 静态分析 | 免费替代IDA |
| Frida | 动态插桩 | Hook、Patch |
| Process Hacker | 进程管理 | 内存查看 |

### 5.2 分析流程

```
1. 静态分析
   ├─ 使用IDA/Ghidra打开二进制
   ├─ 搜索字符串（"auth", "verify", "license"）
   ├─ 识别Rust运行时函数
   └─ 定位验证相关函数

2. 动态分析
   ├─ 使用x64dbg附加程序
   ├─ 在验证函数设置断点
   ├─ 观察验证流程
   └─ 确定Patch点

3. Patch执行
   ├─ 使用x64dbg修改汇编
   ├─ 或使用Frida动态Hook
   └─ 验证Patch效果

4. 持久化
   ├─ 保存修改后的二进制
   └─ 测试功能完整性
```

## 六、注意事项

### 6.1 Rust二进制Patch难点

```
1. 名称混淆
   → 函数名不可读
   → 需要通过字符串引用或调用图分析定位

2. 内联优化
   → 小函数被内联到调用者中
   → 需要Patch调用者而非被调用者

3. 所有权系统
   → Patch时需保持内存安全
   → 避免引入use-after-free或double-free

4. panic处理
   → Patch后可能触发panic
   → 需要Hook panic处理函数
```

### 6.2 安全建议

```
1. 备份原始文件
2. 逐步Patch，每次验证
3. 记录所有修改
4. 测试功能完整性
5. 准备回滚方案
```

---

> 结论：Rust二进制Patch需要理解Rust的内存模型和类型系统。通过Hook返回值、修改条件跳转、替换函数实现，可以有效绕过验证。关键是准确定位验证函数和Patch点。
