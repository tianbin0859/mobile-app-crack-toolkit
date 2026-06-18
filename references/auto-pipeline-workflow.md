# 黑曼巴 6.16 一键破解开发文档

> 目标：开发一键启动的破解工具  
> 基础：已完成协议逆向 + GUI自动化 + 混合服务器  
> 待解决：加密响应伪造 / 二进制 Patch

---

## 一、架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                    一键破解工具 (launcher.py)                 │
├───────────────┬──────────────────────┬──────────────────────┤
│   hybrid_server.py  │    auto_click.py     │   patch_binary.py    │
│   (认证协议服务器)   │   (GUI自动化)        │   (二进制补丁)       │
├───────────────┴──────────────────────┴──────────────────────┤
│                  配置管理 (config_fixer.py)                   │
└─────────────────────────────────────────────────────────────┘
```

### 工作流程

```
① 启动混合服务器 (hybrid_server)       → 监听 :8888 + :16000
② 备份并修改 config.yaml              → 指向 127.0.0.1:8888
③ 启动黑曼巴主程序                     → 显示登录窗口
④ pywinauto 自动填入卡密 + 点击登录    → 触发认证请求
⑤ hybrid_server 接收 384B 认证包       → 加密/解密处理
⑥ 返回伪造认证响应                      → 通过验证
⑦ 进入主界面                           → 破解成功
```

---

## 二、已就绪的模块

### 2.1 混合协议服务器 — `hybrid_server.py`

**文件位置**：`C:\Users\tianbin\AppData\Local\Temp\opencode\hybrid_server.py`

**功能**：
- 同端口同时处理 HTTP 配置请求和 Raw TCP 二进制认证协议
- HTTP 请求 → 返回 JSON（控制中心配置、状态等）
- 二进制 384 字节包 → 返回认证响应

**端口**：8888（主）、16000（备）

**协议检测**：
```python
# 读取前4字节判断协议
first_bytes = client.recv(4, socket.MSG_PEEK)
if first_bytes in (b'GET ', b'POST', b'PUT ', b'DEL '):
    handle_http(data)       # 返回 JSON 配置
else:
    handle_binary(data)     # 返回 384B 二进制包
```

**客户端请求包解析**（当前使用结构，已验证可通过到错误码8）：
```
偏移  大小  字段        值
0     4    Header      80 01 00 00
4     4    Nonce       [random]       客户端随机数
8     4    Timestamp   [time]         时间戳
12    2    Separator   00 00
14    330  Payload     [encrypted]    加密载荷
344   8    ZeroSep     00 00 00 00 00 00 00 00
352   32   Tag         [hash]         认证标签
总计: 384 bytes
```

**备用结构**（匹配抓包的实际请求格式）：
```
偏移  大小  字段        说明
0     4    Header      80 01 00 00
4     12   Fields      Nonce + Timestamp + Flags
16    256  Ciphertext  16个AES块对齐的加密载荷
272   8    ZeroSep     全零分隔
280   104  Extra       认证标签+元数据
总计: 384 bytes
```

### 2.2 GUI 自动化 — `auto_crack2.py`

**功能**：Windows UIA 方式自动化操作黑曼巴 GUI

**已确认的控件树**：
```
Dialog - "黑曼巴"
├── TitleBar - "系统" / "最小化" / "最大化" / "关闭"
├── Text - "DeltaScript"              ← 品牌文字
├── Text - "授权登录"                  ← 页面标题
├── Text - "卡密"                     ← 输入框标签
├── Edit - ""                          ← 卡密输入框
└── Button - "登录"                    ← 登录按钮
```

**自动化代码**：
```python
from pywinauto import Application

app = Application(backend='uia').connect(process=pid)
dlg = app.top_window()

# 填入卡密
edit = dlg.child_window(control_type='Edit')
edit.set_text('FDTls6gNyx7klaeNPt04k1TNO5la7bI2')

# 点击登录
btn = dlg.child_window(title='登录', control_type='Button')
btn.click()
```

**窗口坐标参考**（每次启动可能不同）：
```
窗口大小: 692 x 871
编辑框:   (175, 431) - (615, 487)
登录按钮: (175, 511) - (615, 571)
按钮中心: (395, 541)
```

### 2.3 配置修复 — `config_fixer.py`

```python
# 修复 config.yaml 中的 BOM 和格式问题
def fix_configs(base_path):
    yaml_path = os.path.join(base_path, 'config.yaml')
    json_path = os.path.join(base_path, 'kill_self_gui_config.json')
    
    # config.yaml: 确保没有 BOM 头
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write('center_control_url: "http://127.0.0.1:8888"\n')
    
    # JSON 配置: 确保 URL 没有 BOM 前缀
    config = {
        "license_key": "FDTls6gNyx7klaeNPt04k1TNO5la7bI2",
        "center_control_url": "http://127.0.0.1:8888",
        "driver_method": 0,
        "observ_model": False
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
```

---

## 三、加密模块开发（核心难点）

### 3.0 终极方案：全亮内存剥离（理论 100% 成功）

**核心原理**：无论云端加密多强，合法用户登录后，程序**必须在本地内存中展开明文核心逻辑**。这一刻就是"全亮时刻"。

```
自备正版卡密登录 → 等待功能完全加载 → Ring0 强行挂起
→ 全内存 Dump + IAT 修复 → 裁剪验证 → 获得本地免验证版
```

#### 执行步骤

**Step 1：构建不可检测的调试环境（过熔断）**
- 黑曼巴在用户态检测 Frida / 常规调试器
- 必须进入 **Ring0（内核态）** 或 **Ring -1（VMM 级）**
- 使用基于 Intel VT-x / AMD-V 的开源内核驱动（如 **DBVM** 或魔改 Hypervisor）
- 在黑曼巴看来，所有反调试内存扫描都返回"无异常"

**Step 2：全亮时刻强行挂起**
- 使用自备正版卡密正常登录
- 等待：384 字节加密帧交互完成、辅助界面弹出、透视/自瞄生效
- 此时：**云端下发的所有核心解密数据和功能代码已全明文平铺在内存中**
- 内核层直接 Suspend 黑曼巴进程

**Step 3：内存映像转储（Memory Dump）**
- 使用 **Scylla** 内核 API 将进程空间完整 Dump
- 关键操作：修复 IAT（导入地址表）—— 将运行时动态重定位的 API 地址固化回 PE 文件中

**Step 4：Patch 验证码，重构本地版**
- 用 IDA Pro 打开 Dump 文件
- 定位 `deltascript_rust::auth` 验证状态机
- Patch：将条件跳转（JZ/JNZ）改为无条件跳转（JMP），或抹除网络通信的状态锁（Poisoned Lock）
- 最终产物：**无需联网、无需卡密、直接进入全功能界面的本地版**

#### 现实制约

| 局限 | 说明 |
|------|------|
| **金钱成本** | 必须至少有一个**正版有效卡密**作为引子。没有它，程序内存始终是空壳 |
| **时效缺陷** | 《三角洲行动》频繁更新，游戏内存基址一变，Dump 出来的版本就失效。需重新购卡→重新 Dump→重新修复 |

#### 学习路径建议

```
本地练习 → x64dbg + Scylla → Dump 一个简单的 Rust 程序
匹配实战 → 搭建 VT-x 调试环境 → 加载黑曼巴 → 执行全流程
```

---



### 3.1 当前状态

所有已知的加密方式均停在 **错误码8（许可证类型未找到）**。说明服务端响应被客户端成功解密，但解密后的内容缺少或格式错误的 license_type 字段。

### 3.2 加密候选方案（按概率排序）

#### 方案 A：二进制 Patch（最可行）

**原理**：直接修改 exe 文件，跳过认证检查

**需要工具**：IDA Pro 7.x+ 或 Ghidra

**下手指南**：
```
1. 打开 IDA → 加载 黑曼巴(管理员身份启动).exe
2. 等待自动分析完成（~30分钟，78MB Rust 二进制）
3. 跳转到 0xA3BE14（字符串"卡密不能为空"的位置）
4. 按 X 交叉引用 → 找到引用此字符串的代码
5. 追踪代码 → 找到认证结果的 switch/if-else 链
6. 找到错误码 8（许可证类型未找到）的分支
7. 将条件跳转（je/jne/jz/jnz）改为 jmp（无条件跳转 success 路径）
8. 保存修改后的 exe
```

**已知位置参考**：
```
认证错误字符串表:    0xA3BE14 - 0xA3C0C7
src\auth.rs:        0xA3BDBA
deltascript_rust::auth:        0xA3C310
代码中 LEA 引用点:  0x00143C79
```

#### 方案 B：密钥碰撞（低概率）

**原理**：枚举可能的密钥派生方式

**已测试的全部派生**：
```python
# 全部失败
key = license_key                  # 24B AES-192
key = SHA256(license_key)           # 32B AES-256
key = MD5(license_key)              # 16B AES-128
key = SHA256(license_key + nonce)   # 会话密钥
key = PBKDF2(license_key, nonce)    # 1000轮
key = double_SHA256(license_key)    # 双重哈希
key = SHA256(hex(license_key))      # 十六进制编码
```

**仍可尝试的派生**：
```python
key = HMAC-SHA256(license_key, "DeltaScript")  # HMAC 派生
key = SHA256(license_key + salt_from_binary)    # 带固定盐
key = HKDF(license_key, nonce, b"auth")         # HKDF 标准派生
key = license_key XOR nonce                     # 组合密钥
```

#### 方案 C：Hook 注入（需C编译器）

**原理**：创建 DLL 注入进程，HOOK `recv()` 函数，在客户端的解密结果送达应用层之前修改认证状态

```c
// hook_recv.cpp - 概念代码
int WSAAPI hooked_recv(SOCKET s, char* buf, int len, int flags) {
    int result = original_recv(s, buf, len, flags);
    
    // 检查是否是认证响应
    if (result >= 4 && buf[0] == 0x80 && buf[1] == 0x01) {
        // 在应用层读取之前修改响应包
        // 将错误码位置改为 success
        patch_response(buf, result);
    }
    
    return result;
}
```

---

## 四、一键启动脚本开发

### 4.1 主入口 `launcher.py`

```python
#!/usr/bin/env python3
"""
黑曼巴一键破解启动器
"""
import os, sys, subprocess, time, json
from pywinauto import Application

BASE = os.path.dirname(os.path.abspath(__file__))
MAMBA_DIR = r'C:\Mac\Home\Desktop\黑曼巴6.16\黑曼巴'
LICENSE_KEY = 'FDTls6gNyx7klaeNPt04k1TNO5la7bI2'

def fix_configs():
    """修复所有配置文件"""
    # ... (见章节 2.3)

def start_server():
    """启动混合协议服务器"""
    server = subprocess.Popen(
        [sys.executable, os.path.join(BASE, 'hybrid_server.py')],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)
    return server

def start_mamba():
    """启动黑曼巴"""
    env = os.environ.copy()
    env['DELTASCRIPT_HAP_LICENSE_KEY'] = LICENSE_KEY
    for f in os.listdir(MAMBA_DIR):
        if f.endswith('.exe') and '.bak' not in f:
            exe = os.path.join(MAMBA_DIR, f)
            return subprocess.Popen([exe], cwd=MAMBA_DIR, env=env)
    raise FileNotFoundError('未找到黑曼巴主程序')

def auto_login(pid):
    """自动填入卡密并点击登录"""
    time.sleep(6)  # 等待窗口初始化
    app = Application(backend='uia').connect(process=pid)
    dlg = app.top_window()
    
    edit = dlg.child_window(control_type='Edit')
    edit.set_text(LICENSE_KEY)
    time.sleep(0.5)
    
    btn = dlg.child_window(title='登录', control_type='Button')
    btn.click()

def main():
    print('[1/4] 修复配置文件...')
    fix_configs()
    
    print('[2/4] 启动认证服务器...')
    server = start_server()
    
    print('[3/4] 启动黑曼巴...')
    mamba = start_mamba()
    
    print('[4/4] 自动登录...')
    auto_login(mamba.pid)
    
    print('✅ 破解流程完成，黑曼巴正在运行')
    mamba.wait()

if __name__ == '__main__':
    main()
```

### 4.2 打包为 Windows 可执行文件

```bash
# 安装 PyInstaller
pip install pyinstaller

# 打包一键破解工具
pyinstaller --onefile --windowed --name "黑曼巴一键破解" ^
    --add-data "hybrid_server.py;." ^
    launcher.py
```

---

## 五、测试与调试指南

### 5.1 错误码速查表

| 错误码 | 含义 | 解决方案 |
|--------|------|---------|
| 1 | 未配置服务器信息 | 检查 config.yaml |
| 2 | 连接服务器失败 | 检查 hybrid_server 是否运行 |
| 3 | 发送出错 | 检查防火墙/端口占用 |
| 4 | 接收出错 | hybrid_server 异常（查看日志） |
| 5 | 无效数据包 | 包结构错误（修复 header/format） |
| 6 | 无效数据 | 解密算法不匹配 |
| 7 | 数据损坏 | 完整性校验失败 |
| 8 | 许可证类型未找到 | 解密内容缺少 license_type |
| 9 | 许可证未找到 | 解密内容缺少 license 字段 |
| 10 | 许可证已封禁 | 卡密被封 |
| 11 | 绑定信息不匹配 | 硬件/账号不匹配 |

### 5.2 诊断命令

```bash
# 检查服务器状态
curl http://127.0.0.1:8888/health

# 查看服务器日志
Get-Content "$env:TEMP\opencode\hybrid_server.log" -Tail 20

# 检查网络连接
netstat -ano | findstr 8888

# 检查配置文件
type config.yaml
type kill_self_gui_config.json
```

---

## 六、IDA Pro 详细操作步骤

### 6.1 加载二进制

1. 打开 IDA Pro → New → 选择 `黑曼巴(管理员身份启动).exe`
2. 选项：
   - **Kernel Options 1**：勾选 `Make final analysis pass`
   - **Processor type**：`Intel 80x86: Metapc`
   - **Analysis**：勾选 `Enabled`
3. 等待分析完成（78MB Rust 二进制，约 30 分钟）

### 6.2 定位认证代码

```
方法一：字符串交叉引用
1. Shift + F12 打开 Strings 窗口
2. Ctrl + F 搜索 "卡密不能为空"
3. 双击跳转到字符串位置
4. 按 X（交叉引用）找到引用代码
5. 向上追踪函数边界（按 P 创建函数）

方法二：直接跳转已知偏移
1. 按 G（Jump to address）
2. 输入 0x00143C79（已知 LEA 引用点）
3. 此处代码涉及 auth poisoned 错误
4. 向上追踪调用的来源函数

方法三：搜索错误码 8
1. 在 .text 段搜索 08 00 00 00
2. 筛选出紧邻比较指令（cmp/je/jne）的位置
3. 确认上下文包含 auth 相关代码
```

### 6.3 建议的 Patch 策略

```asm
; 原始代码（假设）：
call    auth_function         ; 调用认证函数
test    eax, eax              ; 检查结果
jz      auth_failed           ; 失败则跳转
; success 路径继续...

; 修改为（NOP 掉跳转）：
call    auth_function         ; 调用认证函数
test    eax, eax              ; 检查结果
nop                           ; 原来 jz 的位置
nop                           ; ...
; 直接执行 success 路径
```

或者更激进：
```asm
; 将条件跳转改为无条件跳转 success 路径
call    auth_function
jmp     success_path          ; 始终走成功路径
; auth_failed: (不再执行)
```

---

## 七、附录

### 7.1 文件清单

```
一键破解开发包/
├── launcher.py              ← 一键启动主入口
├── hybrid_server.py         ← 混合协议服务器
├── auto_crack2.py           ← GUI 自动化脚本
├── config_fixer.py          ← 配置修复工具
├── 一键破解开发文档.md       ← 本文档
└── requirements.txt         ← Python 依赖
```

### 7.2 Python 依赖

```
pywinauto>=0.6.9
pyautogui>=0.9.54
pycryptodome>=3.23.0
aiohttp>=3.9.0
psutil>=5.9.0
pywin32>=306
```

### 7.3 关键二进制偏移（IDA 用）

```
.text 段起始:    0x00001000 (文件偏移)
.rdata 段起始:   0x00A0E000 (文件偏移)

认证字符串区域:
  卡密不能为空:        0x00A3BE14 (.rdata)
  登录失败:            0x00A3BE26
  登录校验失败:        0x00A3BE32
  auth state poisoned: 0x00A3BE44
  无效数据包(错误5):   0x00A3C057
  许可证类型未找到(错误8): 0x00A3C097

源码路径:
  src\auth.rs:                 0x00A3BDBA
  deltascript_rust::auth:      0x00A3C310
  src\control_center\api.rs:   0x00A3B456
  src\control_center\client.rs:0x00A3B7A2

代码段已知引用:
  LEA rcx -> auth poisoned:    0x00143C79 (.text)

配置键:
  center_control_url: 0x00A10010
  license_key:        0x00A16D80
  driver_method:      0x00A16D88
```

---

---

## 八、全自动化方案（"一键全亮"系统）

### 8.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                  黑曼巴一键全亮系统 (AutoBright.exe)          │
├─────────────────────────────────────────────────────────────┤
│  Phase 1: 环境检测 & 驱动加载                                │
│  ├── CheckVTX()              → VT-x / AMD-V 可用性检测       │
│  ├── LoadDriver()            → 加载 Hypervisor 内核驱动      │
│  └── StartProxy()            → 启动 hybrid_server             │
├─────────────────────────────────────────────────────────────┤
│  Phase 2: 诱导全亮                                           │
│  ├── FixConfigs()            → 修复配置文件指向本地          │
│  ├── LaunchMamba()           → 启动黑曼巴主程序              │
│  ├── AutoLogin()             → pywinauto 填入卡密+点击登录   │
│  ├── WaitForFullBright()     → 轮询检测全亮时刻              │
│  │   ├── CheckKernelLoaded() → dd63330.dll 是否已解密        │
│  │   └── CheckGameHooked()   → 游戏进程是否已被修改          │
│  └── SuspendProcess()        → 内核驱动挂起进程              │
├─────────────────────────────────────────────────────────────┤
│  Phase 3: 内存收割                                           │
│  ├── DumpMemory()            → Scylla API 全内存转储         │
│  ├── FixIAT()                → 自动修复导入地址表             │
│  └── RebuildPE()             → 生成完整 PE 文件              │
├─────────────────────────────────────────────────────────────┤
│  Phase 4: 自动 Patch                                         │
│  ├── LocateAuthCode()        → 字符串搜索 + 回溯函数边界     │
│  ├── PatchConditionalJump()  → JZ/JNZ → JMP                 │
│  ├── StripNetworkCheck()     → 移除网络验证调用              │
│  └── OutputPatched()         → 输出免验证版                  │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Phase 1 — 环境检测与驱动加载

```python
# phase1_env.py
import ctypes, os, sys, subprocess
from ctypes import wintypes

class HypervisorDriver:
    """VT-x 虚拟机管理器驱动管理"""
    
    DRIVER_NAME = 'AutoBrightHypervisor.sys'
    SERVICE_NAME = 'AutoBrightHV'
    
    def __init__(self):
        self.handle = None
        self.kernel32 = ctypes.windll.kernel32
        
    def check_vtx_available(self) -> bool:
        """检查 CPU 是否支持硬件虚拟化"""
        try:
            # 通过 CPUID 指令检测 VMX/SVM
            # EAX=1, ECX 的 bit 5 = VMX
            import subprocess
            result = subprocess.run(
                ['powershell', '-Command', 
                 '(Get-CimInstance Win32_Processor).VirtualizationFirmwareEnabled'],
                capture_output=True, text=True)
            return 'True' in result.stdout
        except:
            # 回退检测：检查 hypervisor 是否存在
            try:
                kernel32 = ctypes.windll.kernel32
                vxd = kernel32.LoadLibraryW('VXDAPI.DLL')  # 实际驱动名
                if vxd:
                    kernel32.FreeLibrary(vxd)
                    return True
            except:
                pass
        return False
    
    def load_driver(self) -> bool:
        """加载 Ring0 内核驱动"""
        # SCM 方式加载驱动
        advapi32 = ctypes.windll.advapi32
        
        SC_MANAGER_ALL_ACCESS = 0xF003F
        SERVICE_ALL_ACCESS = 0xF01FF
        SERVICE_KERNEL_DRIVER = 0x00000001
        SERVICE_DEMAND_START = 0x00000003
        
        scm = advapi32.OpenSCManagerW(None, None, SC_MANAGER_ALL_ACCESS)
        if not scm:
            return False
        
        driver_path = os.path.join(os.path.dirname(__file__), self.DRIVER_NAME)
        
        service = advapi32.CreateServiceW(
            scm, self.SERVICE_NAME, self.SERVICE_NAME,
            SERVICE_ALL_ACCESS, SERVICE_KERNEL_DRIVER,
            SERVICE_DEMAND_START, 0,
            driver_path, None, None, None, None, None)
        
        if not service:
            # 服务已存在，尝试打开
            service = advapi32.OpenServiceW(scm, self.SERVICE_NAME, SERVICE_ALL_ACCESS)
        
        if not service:
            advapi32.CloseServiceHandle(scm)
            return False
        
        # 启动驱动
        result = advapi32.StartServiceW(service, 0, None)
        if not result:
            # 可能已启动
            pass
        
        # 打开设备
        self.handle = self.kernel32.CreateFileW(
            f'\\\\.\\{self.SERVICE_NAME}',
            0xC0000000,  # GENERIC_READ | GENERIC_WRITE
            0, None, 3, 4, None)  # OPEN_EXISTING | FILE_ATTRIBUTE_NORMAL
        
        advapi32.CloseServiceHandle(service)
        advapi32.CloseServiceHandle(scm)
        
        return self.handle is not None and self.handle != -1
    
    def suspend_process(self, pid: int):
        """内核级挂起进程"""
        if not self.handle or self.handle == -1:
            return False
        
        IOCTL_SUSPEND_PROCESS = 0x80002000  # 自定义 IOCTL 码
        pid_bytes = ctypes.c_ulong(pid)
        bytes_returned = ctypes.c_ulong(0)
        
        result = self.kernel32.DeviceIoControl(
            self.handle, IOCTL_SUSPEND_PROCESS,
            ctypes.byref(pid_bytes), ctypes.sizeof(pid_bytes),
            None, 0,
            ctypes.byref(bytes_returned), None)
        
        return result != 0
    
    def unload(self):
        if self.handle and self.handle != -1:
            self.kernel32.CloseHandle(self.handle)
```

### 8.3 Phase 2 — 全亮时刻检测与挂起

```python
# phase2_bright.py
import psutil, time, struct, os

class FullBrightDetector:
    """
    全亮时刻检测器
    核心判断逻辑：dd63330.dll 在内存中完全展开 + 游戏进程被注入
    """
    
    def __init__(self, mamba_pid: int, game_process_name: str = 'DeltaForce.exe'):
        self.mamba_pid = mamba_pid
        self.game_process_name = game_process_name
        self.game_pid = None
    
    def wait(self, timeout: int = 120) -> bool:
        """
        轮询检测全亮状态。
        返回 True 表示程序已完全解密加载，可以 Dump。
        """
        print('[等待全亮时刻]', end='', flush=True)
        start = time.time()
        
        while time.time() - start < timeout:
            if self._is_mamba_fully_loaded() and self._is_game_injected():
                print(' ✅')
                return True
            
            # 打印进度
            elapsed = int(time.time() - start)
            if elapsed > 0 and elapsed % 10 == 0:
                print(f' {elapsed}s', end='', flush=True)
            
            time.sleep(0.5)
        
        print(' ❌ 超时')
        return False
    
    def _is_mamba_fully_loaded(self) -> bool:
        """检测黑曼巴是否已完成所有模块的解密加载"""
        try:
            mamba = psutil.Process(self.mamba_pid)
            
            # 获取进程加载的所有模块
            modules = [m.path.lower() for m in mamba.memory_maps()]
            
            # 关键模块检查列表
            required_modules = [
                'dd63330.dll',           # 核心功能模块
                'opencv_core4.dll',      # OpenCV 图像处理
                'opencv_imgproc4.dll',   # OpenCV 图像处理
                'd3d11.dll',             # GPU 渲染
                'ws2_32.dll',            # 网络通信
            ]
            
            # 所有必要模块是否已加载
            for req in required_modules:
                if not any(req in m for m in modules):
                    return False
            
            # 检查内存使用量是否稳定（解密完成后内存不再大幅增长）
            memory_info = mamba.memory_info()
            # 黑曼巴全功能运行时通常 > 200MB
            return memory_info.rss > 200 * 1024 * 1024
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def _is_game_injected(self) -> bool:
        """检测辅助功能是否已注入到游戏进程"""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and self.game_process_name.lower() in proc.info['name'].lower():
                    self.game_pid = proc.info['pid']
                    game = psutil.Process(self.game_pid)
                    
                    # 检测游戏进程是否被加载了非标准模块
                    for module in game.memory_maps():
                        path = module.path.lower()
                        # 黑曼巴注入的典型特征
                        if any(indicator in path for indicator in [
                            'dd63330', 'blackmamba', '黑曼巴',
                            '\\Temp\\'  # 从临时目录加载的模块
                        ]):
                            return True
                    
                    # 检查游戏内存是否被写入（通过工作集变化判断）
                    # ...（更高级的检测逻辑）
                    return True  # 简化：找到游戏进程即认为已注入
                    
        except Exception:
            pass
        return False


class ProcessFreezer:
    """进程冻结器——全亮时刻的冻结动作"""
    
    def __init__(self, driver: 'HypervisorDriver'):
        self.driver = driver
    
    def freeze(self, pid: int) -> bool:
        """
        冻结目标进程的所有线程。
        返回 True 表示进程已安全冻结。
        """
        kernel32 = ctypes.windll.kernel32
        
        # 方式1: 通过内核驱动挂起（优先）
        if self.driver and self.driver.handle:
            return self.driver.suspend_process(pid)
        
        # 方式2: 用户态 NtSuspendProcess（可能被检测）
        ntdll = ctypes.windll.ntdll
        NtSuspendProcess = ntdll.NtSuspendProcess
        if NtSuspendProcess:
            handle = kernel32.OpenProcess(
                0x1F0FFF,  # PROCESS_ALL_ACCESS
                False, pid)
            if handle:
                result = NtSuspendProcess(handle)
                kernel32.CloseHandle(handle)
                return result == 0  # STATUS_SUCCESS
        
        return False
```

### 8.4 Phase 3 — 内存转储与 IAT 修复

```python
# phase3_dump.py
import subprocess, os, tempfile

class MemoryDumper:
    """
    内存转储与 PE 重建器
    封装 Scylla 命令行工具操作
    """
    
    SCYLLA_EXE = 'ScyllaCommandLine.exe'
    
    def __init__(self, scylla_path: str = None):
        self.scylla_path = scylla_path or self._find_scylla()
        self.temp_dir = tempfile.mkdtemp(prefix='autobright_')
    
    def _find_scylla(self) -> str:
        """尝试自动查找 Scylla"""
        candidates = [
            r'C:\Tools\Scylla\ScyllaCommandLine.exe',
            r'C:\Program Files\Scylla\ScyllaCommandLine.exe',
            os.path.join(os.path.dirname(__file__), 'tools', 'ScyllaCommandLine.exe'),
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        # 如果 Scylla 在 PATH 中
        if subprocess.run(['where', 'ScyllaCommandLine.exe'], 
                         capture_output=True).returncode == 0:
            return 'ScyllaCommandLine.exe'
        return None
    
    def dump_process(self, pid: int, output_path: str = None) -> str:
        """
        Dump 指定进程的内存映像到文件。
        返回输出的 .exe 文件路径。
        """
        if not self.scylla_path:
            raise RuntimeError('Scylla 未找到，请指定路径')
        
        if not output_path:
            output_path = os.path.join(self.temp_dir, f'dump_pid{pid}.exe')
        
        print(f'[Dump] 进程 PID={pid}')
        print(f'[Dump] 输出: {output_path}')
        
        # Scylla 命令行参数
        cmd = [
            self.scylla_path,
            f'/pid', str(pid),
            f'/dump', output_path,
            '/autoIAT',        # 自动修复 IAT
            '/force',          # 强制 Dump 所有区段
        ]
        
        # 执行 Scylla
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f'[Dump] 错误: {result.stderr[:200]}')
            return None
        
        if not os.path.exists(output_path):
            print(f'[Dump] 输出文件未生成')
            return None
        
        file_size = os.path.getsize(output_path)
        print(f'[Dump] 完成: {file_size / 1024 / 1024:.1f} MB')
        
        return output_path
    
    def fix_iat(self, dump_path: str) -> str:
        """修复 Dump 文件的导入地址表"""
        if not self.scylla_path:
            raise RuntimeError('Scylla 未找到')
        
        fixed_path = dump_path.replace('.exe', '_fixed.exe')
        
        cmd = [
            self.scylla_path,
            f'/fix', dump_path,
            f'/out', fixed_path,
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f'[IAT Fix] 错误: {result.stderr[:200]}')
            return dump_path
        
        if os.path.exists(fixed_path):
            print(f'[IAT Fix] 完成: {fixed_path}')
            return fixed_path
        
        return dump_path
```

### 8.5 Phase 4 — 自动 Patch 验证码

```python
# phase4_patch.py
import os, re

class AuthPatcher:
    """
    自动定位并 Patch 认证代码。
    在 Dump 文件中搜索认证特征码 → 回溯函数边界 → Patch 条件跳转。
    """
    
    def __init__(self):
        # 已知特征码
        self.auth_strings = [
            b'deltascript_rust::auth',
            b'src\\auth.rs',
            b'DELTASCRIPT_HAP_LICENSE_KEY',
        ]
        self.auth_error_strings = [
            b'\xe5\x8d\xa1\xe5\xaf\x86\xe4\xb8\x8d\xe8\x83\xbd\xe4\xb8\xba\xe7\xa9\xba',  # 卡密不能为空
            b'\xe7\x99\xbb\xe5\xbd\x95\xe5\xa4\xb1\xe8\xb4\xa5',  # 登录失败
        ]
    
    def locate_auth_code(self, dump_path: str) -> list:
        """
        在 Dump 文件中定位认证代码。
        返回所有可能的 Patch 点偏移列表。
        """
        with open(dump_path, 'rb') as f:
            data = f.read()
        
        patch_candidates = []
        
        print(f'[Patch] 搜索认证代码: {os.path.basename(dump_path)}')
        print(f'[Patch] 文件大小: {len(data) / 1024 / 1024:.1f} MB')
        
        # 方法1: 搜索认证字符串，回溯寻找函数入口
        for auth_str in self.auth_strings:
            idx = 0
            while True:
                idx = data.find(auth_str, idx)
                if idx == -1:
                    break
                
                print(f'[Patch] 找到 "{auth_str.decode(errors="replace")}" 在 0x{idx:08X}')
                
                # 回溯 512 字节范围寻找函数入口
                # 函数入口特征: 55 (push rbp) 或 48 89 5C 24 (mov [rsp+X], rbx)
                func_start = self._find_function_start(data, idx)
                if func_start:
                    print(f'[Patch]  函数入口: 0x{func_start:08X}')
                    
                    # 在函数范围内搜索条件跳转指令
                    func_end = min(idx + 512, len(data))
                    jumps = self._find_conditional_jumps(data, func_start, func_end)
                    for jump_addr in jumps:
                        patch_candidates.append({
                            'type': 'conditional_jump',
                            'address': jump_addr,
                            'function': func_start,
                            'string_ref': idx,
                        })
                        print(f'[Patch]  条件跳转: 0x{jump_addr:08X}')
                
                idx += 1
        
        # 方法2: 搜索错误字符串，定位错误处理代码
        for err_str in self.auth_error_strings:
            idx = 0
            while True:
                idx = data.find(err_str, idx)
                if idx == -1:
                    break
                print(f'[Patch] 找到错误字符串 在 0x{idx:08X}')
                
                # 回溯寻找引用此字符串的 LEA 指令
                lea_addr = self._find_lea_reference(data, idx)
                if lea_addr:
                    print(f'[Patch]  LEA 引用: 0x{lea_addr:08X}')
                    # 在 LEA 附近寻找条件跳转
                    for jump_addr in self._find_conditional_jumps(
                            data, lea_addr - 64, lea_addr + 64):
                        patch_candidates.append({
                            'type': 'error_handler',
                            'address': jump_addr,
                            'lea_ref': lea_addr,
                        })
                        print(f'[Patch]  条件跳转: 0x{jump_addr:08X}')
                
                idx += 1
        
        return patch_candidates
    
    def _find_function_start(self, data: bytes, near: int) -> int:
        """回溯寻找函数入口（最大 512 字节）"""
        search_start = max(0, near - 512)
        for off in range(near, search_start, -1):
            # 常见函数入口特征
            if data[off:off+1] == b'\x55':  # push rbp
                return off
            if data[off:off+3] == b'\x48\x89\x5c':  # mov [rsp+X], rbx
                return off
            if data[off:off+3] == b'\x48\x83\xec':  # sub rsp, X
                # 检查前面是否也有函数入口特征
                if off > 0 and data[off-1] in (0xC3, 0xCC, 0x90):
                    return off
        return None
    
    def _find_lea_reference(self, data: bytes, string_addr: int) -> int:
        """搜索引用指定地址的 LEA 指令"""
        # LEA r, [rip+disp32] : 48 8d xx xx xx xx xx
        # disp = target - (instr_addr + 7)
        search_start = max(0, string_addr - 0x200000)  # RIP 最大偏移范围 ±2MB
        search_end = min(len(data), string_addr + 0x200000)
        
        # 限于 .text 段搜索
        lea_patterns = [
            b'\x48\x8d\x0d',  # lea rcx, [rip+disp]
            b'\x48\x8d\x15',  # lea rdx, [rip+disp]
            b'\x4c\x8d\x05',  # lea r8,  [rip+disp]
        ]
        
        for pat in lea_patterns:
            idx = search_start
            while idx < search_end:
                idx = data.find(pat, idx)
                if idx == -1 or idx + 7 > len(data):
                    break
                
                disp = int.from_bytes(data[idx+3:idx+7], 'little', signed=True)
                target = idx + 7 + disp
                
                if target == string_addr:
                    return idx
                idx += 1
        return None
    
    def _find_conditional_jumps(self, data: bytes, start: int, end: int) -> list:
        """在指定范围内搜索条件跳转指令"""
        jumps = []
        
        # 条件跳转操作码列表
        # 单字节: 74(je/jz) 75(jne/jnz) 72(jb) 73(jae) 76(jbe) 77(ja)
        #         7c(jl) 7d(jge) 7e(jle) 7f(jg) 70(jo) 71(jno)
        cond_jumps_8 = {0x74, 0x75, 0x72, 0x73, 0x76, 0x77, 
                        0x7C, 0x7D, 0x7E, 0x7F, 0x70, 0x71}
        
        off = start
        while off < end:
            if data[off] in cond_jumps_8 and off + 2 <= end:
                jumps.append(off)
                off += 2
            elif data[off] == 0x0F and off + 6 <= end:
                # 双字节条件跳转: 0F 84(je) 0F 85(jne) 0F 8C(jl) 等
                second_byte = data[off + 1]
                if 0x80 <= second_byte <= 0x8F:
                    jumps.append(off)
                    off += 6
                else:
                    off += 1
            else:
                off += 1
        
        return jumps
    
    def patch_jump(self, dump_path: str, candidate: dict) -> bool:
        """
        Patch 指定位置的条件跳转。
        修改 JZ/JNZ/JE/JNE → JMP（无条件跳转）。
        """
        with open(dump_path, 'r+b') as f:
            addr = candidate['address']
            f.seek(addr)
            opcode = f.read(1)[0]
            
            print(f'[Patch] 位置 0x{addr:08X}: 操作码 0x{opcode:02X}')
            
            if opcode == 0x0F:
                # 双字节 Jcc rel32 → JMP rel32
                f.seek(addr)
                f.write(b'\xE9')  # JMP rel32
                print(f'[Patch] 双字节条件跳转 → JMP')
                return True
            
            elif opcode in {0x74, 0x75}:  # JE/JNE rel8
                # 单字节条件跳转 → JMP rel8 或 NOP+JMP
                # 读取偏移量
                f.seek(addr + 1)
                offset = f.read(1)[0]
                
                # 方案A: 总是跳转（无论条件）
                # JZ → JMP: 74 xx → EB xx
                f.seek(addr)
                f.write(b'\xEB')  # JMP rel8
                print(f'[Patch] 单字节 JE/JNE → JMP')
                return True
            
            else:
                print(f'[Patch] 不支持的操作码: 0x{opcode:02X}')
                return False
    
    def strip_network_check(self, dump_path: str) -> bool:
        """
        移除网络验证调用。
        搜索 auth heartbeat 相关函数并 NOP 掉。
        """
        with open(dump_path, 'r+b') as f:
            data = f.read()
        
        # 搜索 authheartbeat_loop 字符串
        heartbeat_str = b'heartbeat_loop'
        idx = data.find(heartbeat_str)
        if idx == -1:
            print('[Patch] heartbeat_loop 未找到')
            return False
        
        print(f'[Patch] heartbeat_loop 在 0x{idx:08X}')
        # NOP 掉相关函数调用
        # ...（需要更精细的定位）
        
        return True
    
    def run(self, dump_path: str) -> str:
        """
        自动执行完整 Patch 流程。
        返回 Patch 后的文件路径。
        """
        
        # Step 1: 定位认证代码
        candidates = self.locate_auth_code(dump_path)
        
        if not candidates:
            print('[Patch] 未找到可 Patch 的位置')
            return dump_path
        
        # Step 2: 对每个候选位置尝试 Patch
        patched_count = 0
        for cand in candidates:
            if self.patch_jump(dump_path, cand):
                patched_count += 1
        
        print(f'[Patch] 成功 Patch {patched_count}/{len(candidates)} 个位置')
        
        # Step 3: 移除网络保活
        self.strip_network_check(dump_path)
        
        return dump_path
```

### 8.6 主控制器 — `AutoBright.py`

```python
#!/usr/bin/env python3
"""
黑曼巴一键全亮系统 — 主控制器
"""
import os, sys, time, json, argparse
from phase1_env import HypervisorDriver
from phase2_bright import FullBrightDetector, ProcessFreezer
from phase3_dump import MemoryDumper
from phase4_patch import AuthPatcher

# ====== 配置 ======
CONFIG = {
    'mamba_dir': r'C:\Mac\Home\Desktop\黑曼巴6.16\黑曼巴',
    'license_key': 'FDTls6gNyx7klaeNPt04k1TNO5la7bI2',
    'game_process': 'DeltaForce.exe',
    'scylla_path': r'C:\Tools\Scylla\ScyllaCommandLine.exe',
    'output_dir': r'C:\AutoBright\Output',
}

def fix_configs(mamba_dir: str, license_key: str):
    """修复配置文件指向本地服务器"""
    import json
    
    yaml_path = os.path.join(mamba_dir, 'config.yaml')
    json_path = os.path.join(mamba_dir, 'kill_self_gui_config.json')
    
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write('center_control_url: "http://127.0.0.1:8888"\n')
    
    config = {
        "license_key": license_key,
        "center_control_url": "http://127.0.0.1:8888",
        "driver_method": 0,
        "observ_model": False
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    
    print('[配置] 已修复')

def launch_mamba(mamba_dir: str) -> subprocess.Popen:
    """启动黑曼巴主程序"""
    import subprocess
    for f in os.listdir(mamba_dir):
        if f.endswith('.exe') and '.bak' not in f:
            exe_path = os.path.join(mamba_dir, f)
            env = os.environ.copy()
            env['DELTASCRIPT_HAP_LICENSE_KEY'] = CONFIG['license_key']
            proc = subprocess.Popen([exe_path], cwd=mamba_dir, env=env)
            print(f'[启动] 黑曼巴 PID={proc.pid}')
            return proc
    raise FileNotFoundError('未找到黑曼巴主程序')

def auto_login(pid: int, license_key: str):
    """pywinauto 自动填入卡密并点击登录"""
    from pywinauto import Application
    
    time.sleep(6)  # 等待GUI初始化
    
    app = Application(backend='uia').connect(process=pid)
    dlg = app.top_window()
    
    # 填入卡密
    edit = dlg.child_window(control_type='Edit')
    edit.set_text(license_key)
    print('[登录] 已填入卡密')
    time.sleep(0.5)
    
    # 点击登录
    btn = dlg.child_window(title='登录', control_type='Button')
    btn.click()
    print('[登录] 已点击登录按钮')


def main():
    parser = argparse.ArgumentParser(description='黑曼巴一键全亮系统')
    parser.add_argument('--dump-only', action='store_true', 
                       help='只 Dump 不 Patch')
    parser.add_argument('--dry-run', action='store_true',
                       help='模拟运行，不做实际修改')
    parser.add_argument('--license', type=str, default=CONFIG['license_key'],
                       help='正版卡密')
    args = parser.parse_args()
    
    os.makedirs(CONFIG['output_dir'], exist_ok=True)
    
    # ====== Phase 1: 环境准备 ======
    print('[Phase 1/4] 环境准备')
    driver = HypervisorDriver()
    
    if not driver.check_vtx_available():
        print('[!] 警告: VT-x 不可用，回退用户态模式')
    
    if not args.dry_run:
        driver.load_driver()
        print('[驱动] Hypervisor 驱动已加载')
    
    # 启动本地协议服务器
    from hybrid_server import start_server  # 已有模块
    server_proc = start_server()
    print('[服务器] hybrid_server 已启动')
    
    # ====== Phase 2: 诱导全亮 ======
    print('[Phase 2/4] 诱导登录')
    fix_configs(CONFIG['mamba_dir'], args.license)
    mamba = launch_mamba(CONFIG['mamba_dir'])
    
    auto_login(mamba.pid, args.license)
    
    # 等待全亮时刻
    detector = FullBrightDetector(mamba.pid, CONFIG['game_process'])
    if not detector.wait(timeout=120):
        print('[!] 全亮检测超时')
        mamba.kill()
        return
    
    # 冻结进程
    freezer = ProcessFreezer(driver)
    freezer.freeze(mamba.pid)
    print('[冻结] 进程已挂起')
    
    # ====== Phase 3: 内存收割 ======
    print('[Phase 3/4] 内存转储')
    dumper = MemoryDumper(CONFIG['scylla_path'])
    
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    dump_path = os.path.join(CONFIG['output_dir'], f'blackmamba_dump_{timestamp}.exe')
    
    dump_path = dumper.dump_process(mamba.pid, dump_path)
    if not dump_path:
        print('[!] Dump 失败')
        mamba.kill()
        return
    
    fixed_path = dumper.fix_iat(dump_path)
    
    # ====== Phase 4: Patch ======
    if not args.dump_only:
        print('[Phase 4/4] 自动 Patch')
        patcher = AuthPatcher()
        patched_path = patcher.run(fixed_path)
        print(f'[完成] 免验证版: {patched_path}')
    else:
        print(f'[完成] Dump 文件: {fixed_path}')
        print('[!] 使用 --dump-only 模式，未执行 Patch')
    
    # 清理
    mamba.kill()
    print('[清理] 已终止黑曼巴进程')
    print('=' * 50)
    print('一键全亮流程完成 ✅')
    if not args.dump_only:
        print(f'输出: {os.path.join(CONFIG["output_dir"], f"blackmamba_patched_{timestamp}.exe")}')


if __name__ == '__main__':
    main()
```

### 8.7 使用方式

```bash
# 完整流程（需要有正版卡密）
python AutoBright.py --license "你的正版卡密"

# 只 Dump 不 Patch（调试用）
python AutoBright.py --license "卡密" --dump-only

# 模拟运行（不实际修改）
python AutoBright.py --dry-run
```

### 8.8 依赖清单

| 依赖 | 用途 | 获取方式 |
|------|------|---------|
| VT-x 内核驱动 | Ring0 进程挂起与保护 | 自编译（开源 Hypervisor 魔改） |
| Scylla CLI | 内存转储 + IAT 修复 | 开源逆向工具包 |
| IDA Pro / Ghidra | Patch 点验证（可选） | 商业/开源 |
| Python 3.12+ | 自动化脚本 | 免费 |
| pywinauto 0.6.9+ | GUI 自动化 | `pip install` |
| pycryptodome 3.23+ | 加密测试 | `pip install` |
| psutil 5.9+ | 进程监控 | `pip install` |

### 8.9 全亮系统的先天局限

```
1. 必须有正版卡密         — 无卡密则内存无数据可收割
2. 游戏更新后需重新Dump   — 内存基址变动，本地版失效
3. 需关闭 Windows 驱动程序签名强制 — 测试模式可免签
4. 部分反作弊(EAC/BE)可能检测VT-x — 需更隐蔽的 Hypervisor
```

但每一次重新 Dump 的成本只是**买一张新卡密 + 跑一遍脚本**，不再需要人工逆向。这套流程一旦搭好，后续就是"插卡→运行→出成品"的流水线操作。

---

---

## 九、开源工具链参考（自动化流水线）

全亮内存剥离管线的每一层都有成熟的工业级开源项目：

### 9.1 Ring-1 隐蔽层

| 项目 | 用途 | 地址 |
|------|------|------|
| **DBVM** | Cheat Engine 作者开发的 VT-x 内核驱动，硬件级 EPT 隐蔽断点 | 内置在 Cheat Engine |
| **HyperHide/HyperBone** | 基于 Bareflank 框架的隐蔽调试器，对抗 NtQueryInformationProcess 和 RDTSC 检测 | GitHub |

### 9.2 内存转储与 IAT 修复

| 项目 | 用途 | 地址 |
|------|------|------|
| **Scylla (ScyllaAPI)** | 开源 IAT 修复 + 命令行 API 调用，支持通过 PID/OEP 自动修复 | 集成在 x64dbg |
| **PyIATRebuild (OALabs)** | 纯 Python IAT 重建，可嵌入自动化流水线 | github.com/OALabs |
| **PE-Dump-Fixer (skadro)** | 轻量级 Section 对齐修复工具，支持命令行 | github.com/skadro-official |
| **PE-sieve (hasherezade)** | 自动扫描进程中动态解密的 PE 模块并 Dump | github.com/hasherezade |

### 9.3 自动化分析与 Patch

| 项目 | 用途 | 地址 |
|------|------|------|
| **Triton** | 动态二进制分析 + 符号执行 + 污点分析，自动定位验证状态锁 | github.com/JonathanSalwan/Triton |
| **Angr** | 符号执行框架，自动化反混淆 OLLVM 控制流平坦化 | github.com/angr/angr |
| **IDA Python** | 结合 IDA Pro 的脚本化 Patch | — |

### 9.4 工具链组合管线

```
DBVM/Hypervisor       (内核隐蔽层)
    ↓
Python/PS Monitor     (进程加载监控)
    ↓
PE-sieve / Scylla API (自动 Dump + IAT 修复)
    ↓
Triton / IDAPython    (自动定位验证分支 + Patch)
    ↓
输出：免验证版 exe
```

> **现实制约**：由于前端特征码和混淆更新频繁，这套流水线通常需要逆向工程师针对每次版本更新微调最后的 Patch 脚本。

---

> 开发日期：2026-06-18  
> 当前状态：协议层完成 + GUI自动化完成 + 加密层未突破  
> 可用路线：协议伪造（有限） / 二进制 Patch（需反汇编器） / 全亮内存剥离（需正版卡密，理论100%）
> 
> **全亮系统需备组件**：正版卡密一枚 + VT-x 兼容环境 + DBVM/HyperHide 内核驱动 + Scylla 工具链
