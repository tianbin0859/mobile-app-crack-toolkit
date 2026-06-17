# HAP SDK 网络验证绕过指南

> 针对 HAP (Huawei Application Protection) SDK 的网络授权验证绕过

## HAP SDK 特征识别

### 文件特征

```
目标程序目录中查找:
- HAP.dll / HAP64.dll
- SecureEngineSDK.dll / SecureEngineSDK64.dll
- 配置文件: hap_config.ini / license.dat

字符串搜索:
- "HAP_"
- "hap."
- "license"
- "auth"
- "verify"
- "check"
```

### API 特征

```c
// HAP SDK 典型 API
HAP_Initialize          // 初始化
HAP_VerifyLicense       // 验证许可证
HAP_CheckAuth           // 检查授权
HAP_GetUserInfo         // 获取用户信息
HAP_GetLicenseStatus    // 获取许可证状态
HAP_ActivateLicense     // 激活许可证
HAP_DeactivateLicense   // 反激活
HAP_Heartbeat           // 心跳检测
```

## 验证流程分析

### 典型验证流程

```
程序启动
    ↓
HAP_Initialize()
    ↓
读取本地 license.dat
    ↓
HAP_VerifyLicense(key)
    ├─→ 本地验证 (签名检查/有效期)
    └─→ 网络验证 (连接服务器)
        ↓
    验证结果
    ├─→ 成功: 继续启动
    └─→ 失败: 显示错误/退出
        ↓
运行中
    ↓
HAP_Heartbeat()  // 定期心跳
    ├─→ 成功: 继续运行
    └─→ 失败: 提示授权失效
```

## 绕过策略

### 策略1: API Hook (推荐)

**使用 MinHook 库：**

```cpp
// hap_bypass.cpp
#include <windows.h>
#include <MinHook.h>

#pragma comment(lib, "libMinHook-x64-v141-mt.lib")

// 原始函数指针
typedef int (*HAP_VerifyLicense_t)(const char* license_key);
typedef int (*HAP_CheckAuth_t)();
typedef int (*HAP_Heartbeat_t)();
typedef int (*HAP_GetLicenseStatus_t)(int* status);

HAP_VerifyLicense_t orig_VerifyLicense = NULL;
HAP_CheckAuth_t orig_CheckAuth = NULL;
HAP_Heartbeat_t orig_Heartbeat = NULL;
HAP_GetLicenseStatus_t orig_GetLicenseStatus = NULL;

// Hook 函数
int hooked_HAP_VerifyLicense(const char* license_key) {
    // 强制返回验证成功
    return 0; // 0 = HAP_SUCCESS
}

int hooked_HAP_CheckAuth() {
    return 0; // 已授权
}

int hooked_HAP_Heartbeat() {
    return 0; // 心跳正常
}

int hooked_HAP_GetLicenseStatus(int* status) {
    if (status) *status = 1; // LICENSE_VALID
    return 0;
}

// DLL 入口
BOOL APIENTRY DllMain(HMODULE hModule, DWORD reason, LPVOID lpReserved) {
    if (reason == DLL_PROCESS_ATTACH) {
        MH_Initialize();
        
        // 获取 HAP DLL 模块
        HMODULE hHAP = GetModuleHandleA("HAP64.dll");
        if (!hHAP) hHAP = GetModuleHandleA("HAP.dll");
        
        if (hHAP) {
            // Hook HAP_VerifyLicense
            MH_CreateHook(
                GetProcAddress(hHAP, "HAP_VerifyLicense"),
                hooked_HAP_VerifyLicense,
                (LPVOID*)&orig_VerifyLicense
            );
            
            // Hook HAP_CheckAuth
            MH_CreateHook(
                GetProcAddress(hHAP, "HAP_CheckAuth"),
                hooked_HAP_CheckAuth,
                (LPVOID*)&orig_CheckAuth
            );
            
            // Hook HAP_Heartbeat
            MH_CreateHook(
                GetProcAddress(hHAP, "HAP_Heartbeat"),
                hooked_HAP_Heartbeat,
                (LPVOID*)&orig_Heartbeat
            );
            
            // Hook HAP_GetLicenseStatus
            MH_CreateHook(
                GetProcAddress(hHAP, "HAP_GetLicenseStatus"),
                hooked_HAP_GetLicenseStatus,
                (LPVOID*)&orig_GetLicenseStatus
            );
            
            MH_EnableHook(MH_ALL_HOOKS);
        }
    }
    return TRUE;
}
```

**编译为 DLL 注入器：**
```bash
# 使用 Visual Studio 或 MinGW
cl.exe /LD hap_bypass.cpp /Fe:hap_bypass.dll

# 注入到目标进程
# 方法1: 使用 DLL 注入器
inject.exe "MC副机6.7.exe" hap_bypass.dll

# 方法2: 修改 PE 导入表，添加 DLL
```

### 策略2: 内存 Patch

**使用 Python + pymem：**

```python
import pymem
import re

def patch_hap_verify(process_name="MC副机6.7.exe"):
    """Patch HAP 验证函数返回成功"""
    
    # 附加到进程
    pm = pymem.Pymem(process_name)
    
    # 获取 HAP 模块基址
    hap_module = None
    for module in pm.list_modules():
        if "hap" in module.name.lower():
            hap_module = module
            break
    
    if not hap_module:
        print("[-] HAP DLL 未加载")
        return False
    
    print(f"[*] HAP 模块: {hap_module.name} @ 0x{hap_module.lpBaseOfDll:X}")
    
    # 读取模块内存
    module_size = hap_module.SizeOfImage
    module_data = pm.read_bytes(hap_module.lpBaseOfDll, module_size)
    
    # 搜索 HAP_VerifyLicense 导出
    # 方法: 通过 IAT 或 EAT 找到函数地址
    # 简化: 搜索特征码
    
    # 常见验证函数特征 (x64):
    # push rbp
    # mov rbp, rsp
    # sub rsp, 0xXX
    # ... 验证逻辑 ...
    # mov eax, 1  (失败)
    # leave
    # ret
    
    # 搜索 mov eax, 1; leave; ret 模式
    pattern = b"\xB8\x01\x00\x00\x00\xC9\xC3"
    matches = []
    start = 0
    while True:
        pos = module_data.find(pattern, start)
        if pos == -1:
            break
        matches.append(hap_module.lpBaseOfDll + pos)
        start = pos + 1
    
    print(f"[*] 找到 {len(matches)} 个可能的验证返回点")
    
    # Patch 所有匹配点
    for addr in matches:
        # 改为 mov eax, 0; leave; ret
        patch = b"\xB8\x00\x00\x00\x00\xC9\xC3"
        pm.write_bytes(addr, patch, len(patch))
        print(f"[+] Patched @ 0x{addr:X}")
    
    return True

if __name__ == "__main__":
    patch_hap_verify()
```

### 策略3: 网络层拦截

**使用 Fiddler/Charles + Hosts：**

```
1. 分析 HAP 验证请求:
   - 使用 Wireshark 抓包
   - 或使用 Fiddler 代理

2. 识别验证服务器域名/IP:
   - 例: auth.hapserver.com
   - 例: 123.456.789.012

3. 修改 Hosts 文件:
   127.0.0.1  auth.hapserver.com
   127.0.0.1  verify.hapserver.com

4. 启动本地假服务器响应验证:
   
   Python Flask 示例:
```

```python
# fake_hap_server.py
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/verify', methods=['POST'])
def verify():
    """返回验证成功"""
    return jsonify({
        "status": 0,
        "message": "success",
        "license_status": "valid",
        "expire_date": "2099-12-31",
        "features": ["all"]
    })

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    """返回心跳正常"""
    return jsonify({
        "status": 0,
        "message": "alive"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
```

### 策略4: 配置修改

**修改本地 license.dat：**

```python
import struct
import json

def analyze_license_file(path="license.dat"):
    """分析 license.dat 文件结构"""
    with open(path, 'rb') as f:
        data = f.read()
    
    # 检查文件头
    print(f"文件大小: {len(data)} bytes")
    print(f"前16字节: {data[:16].hex()}")
    
    # 尝试识别格式
    if data[:4] == b"\x7B\x22":  # JSON 开头
        print("格式: JSON")
        try:
            obj = json.loads(data)
            print(json.dumps(obj, indent=2))
        except:
            pass
    elif data[:2] == b"MZ":  # PE 文件
        print("格式: PE (可能是加密/打包的)")
    else:
        print("格式: 二进制/加密")
        # 检查是否是简单 XOR 加密
        for key in range(256):
            decrypted = bytes([b ^ key for b in data[:100]])
            if b'{"' in decrypted or b'expire' in decrypted:
                print(f"可能的 XOR key: {key}")
                print(f"解密样本: {decrypted[:50]}")

if __name__ == "__main__":
    analyze_license_file()
```

## 多验证点处理

### 常见多验证点组合

```
HAP SDK 通常使用多层验证:

层1: 启动验证
  ├─→ HAP_Initialize
  └─→ HAP_VerifyLicense

层2: 功能验证
  ├─→ HAP_CheckAuth (每次调用功能时)
  └─→ HAP_GetLicenseStatus

层3: 心跳验证
  └─→ HAP_Heartbeat (每5-30分钟)

层4: 关键操作验证
  └─→ HAP_VerifyLicense (特定操作前)
```

### 完整绕过方案

```cpp
// 必须 Hook 所有验证点
// 任何一层验证失败都会导致程序退出或功能受限

// Hook 列表:
// 1. HAP_Initialize        → 返回成功
// 2. HAP_VerifyLicense       → 返回成功
// 3. HAP_CheckAuth           → 返回已授权
// 4. HAP_GetLicenseStatus    → 返回有效
// 5. HAP_Heartbeat           → 返回正常
// 6. HAP_GetUserInfo         → 返回 VIP 用户信息
// 7. HAP_ActivateLicense     → 返回激活成功
```

## 验证绕过检测

### 如何确认绕过成功

```
1. 程序正常启动，无授权错误提示
2. 所有功能可用，无功能限制
3. 无定期弹窗要求输入卡密
4. 网络流量中无验证请求
5. 程序运行超过心跳周期不退出
```

### 绕过失败迹象

```
1. 程序启动后几秒/几分钟崩溃
2. 功能部分可用，部分提示未授权
3. 定期弹出授权窗口
4. 网络流量中仍有验证请求
5. 运行一段时间后自动退出
```

## 工具推荐

| 工具 | 用途 | 下载 |
|------|------|------|
| API Monitor | 监控 API 调用 | http://www.rohitab.com/apimonitor |
| Wireshark | 网络抓包 | https://www.wireshark.org |
| Fiddler | HTTP 代理 | https://www.telerik.com/fiddler |
| Process Hacker | 进程分析 | https://processhacker.sourceforge.io |
| x64dbg | 调试器 | https://x64dbg.com |
| ReClass.NET | 内存分析 | https://github.com/ReClassNET/ReClass.NET |

## 实战案例: MC副机6.7

### 目标信息
- 程序: MC副机6.7.exe
- 保护: Themida + SecureEngine + HAP SDK
- 验证: 网络授权 + 本地验证

### 破解步骤
```
1. 脱壳 (Themidie + ScyllaHide)
   → 得到脱壳后的 MC副机6.7_dump.exe

2. 分析 HAP 验证
   → 发现 HAP64.dll
   → 导出: HAP_VerifyLicense, HAP_CheckAuth, HAP_Heartbeat

3. 编写 DLL 注入器
   → hap_bypass.dll
   → Hook 所有 HAP API 返回成功

4. 测试运行
   → 启动 MC副机6.7_dump.exe
   → 注入 hap_bypass.dll
   → 验证所有功能正常

5. 打包输出
   → 提供 DLL 注入器 + 使用说明
   → 或 Patch 后的独立 EXE
```

## 参考

- `references/themida-unpacking-guide.md` - Themida 脱壳指南
- `references/windows-debugger-setup.md` - Windows 调试器配置
- `references/windows-pe-analysis.md` - PE 文件分析
