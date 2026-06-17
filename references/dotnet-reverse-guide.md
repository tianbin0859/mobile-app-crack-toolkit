# .NET 程序破解实战指南

## 适用场景
- C# 桌面程序逆向（WinForms/WPF/Console）
- 绕过 .NET 授权验证、功能限制
- 反编译 ConfuserEx/VMProtect .NET 保护壳

## 核心工具链

| 工具 | 用途 | 下载 |
|------|------|------|
| dnSpy | .NET 反编译 + 调试 + 修改 | https://github.com/dnSpy/dnSpy |
| dnSpyEx | dnSpy 社区维护版（推荐） | https://github.com/dnSpyEx/dnSpyEx |
| ILSpy | 轻量反编译器 | https://github.com/icsharpcode/ILSpy |
| de4dot | 自动化脱壳/反混淆 | https://github.com/de4dot/de4dot |
| ConfuserExUnpacker | ConfuserEx 专用脱壳 | 社区工具 |
| Mono.Cecil | .NET IL 修改库 | NuGet |
| Harmony | 运行时方法 Hook | https://github.com/pardeike/Harmony |

## 标准流程

### 1. 识别保护壳
```bash
# 使用 Detect It Easy (DIE)
die.exe target.exe
# 输出：ConfuserEx v1.6.0, .NET Reactor, VMProtect 等

# 使用 PE-bear 查看 .NET 元数据
# 检查 mscoree.dll 导入、CLR Header
```

### 2. 自动化脱壳（de4dot）
```bash
# 基础脱壳
de4dot.exe -r target.exe -o target_cleaned.exe

# 强制深度脱壳
de4dot.exe target.exe --preserve-tokens --keep-types

# 批量处理目录
de4dot.exe -r c:\targets\ -ro c:\cleaned\
```

### 3. 手动 ConfuserEx 脱壳
```bash
# 1. 用 dnSpy 打开，找到 anti-tamper / anti-debug 方法
# 2. 右键 -> 编辑方法 -> 清空方法体（ret）
# 3. 保存模块
# 4. 用 de4dot 二次处理

# 或使用专用工具
ConfuserExUnpacker.exe target.exe
```

### 4. 反编译分析
```bash
# dnSpy 打开脱壳后的程序
# 搜索关键词：License, Check, Verify, IsRegistered, Trial, Expire
# 定位关键方法后右键 -> 编辑方法
```

### 5. 直接修改 IL 代码
```csharp
// 原代码（反编译后）
private bool CheckLicense()
{
    if (File.Exists("license.dat"))
        return VerifySignature(File.ReadAllBytes("license.dat"));
    return false;
}

// 修改为直接返回 true
private bool CheckLicense()
{
    return true;
}
```

### 6. 运行时 Hook（Harmony）
```csharp
// 创建 Harmony Patch DLL
using HarmonyLib;
using System;

[HarmonyPatch(typeof(LicenseManager), "CheckLicense")]
public class LicensePatch
{
    static bool Prefix(ref bool __result)
    {
        __result = true;  // 强制返回 true
        return false;      // 跳过原方法
    }
}

// 注入器
public class Injector
{
    public static void Main()
    {
        var harmony = new Harmony("com.crack.patch");
        harmony.PatchAll();
    }
}
```

### 7. 自动化 Python 工作流
```python
#!/usr/bin/env python3
import subprocess
import re
from pathlib import Path

class DotNetCracker:
    def __init__(self, target: str):
        self.target = Path(target)
        self.output_dir = Path("dotnet_output")
        
    def detect_protector(self) -> str:
        """检测保护壳类型"""
        result = subprocess.run(
            ["die.exe", str(self.target)],
            capture_output=True, text=True
        )
        
        protectors = [
            "ConfuserEx", ".NET Reactor", "VMProtect",
            "Obfuscar", "Dotfuscator", "SmartAssembly"
        ]
        
        for p in protectors:
            if p in result.stdout:
                return p
        return "Unknown"
    
    def deobfuscate(self) -> Path:
        """自动化脱壳"""
        protector = self.detect_protector()
        output = self.output_dir / f"{self.target.stem}_cleaned.exe"
        
        if protector == "ConfuserEx":
            # 先尝试 de4dot
            subprocess.run([
                "de4dot.exe", str(self.target),
                "-o", str(output)
            ])
        else:
            subprocess.run([
                "de4dot.exe", str(self.target),
                "--preserve-tokens", "-o", str(output)
            ])
        
        return output
    
    def find_license_checks(self, dll_path: str) -> list:
        """从反编译代码定位授权检查"""
        # 使用 ILSpy 命令行导出
        result = subprocess.run(
            ["ILSpy", str(dll_path), "--output", str(self.output_dir)],
            capture_output=True, text=True
        )
        
        keywords = [
            "License", "IsLicensed", "IsRegistered", "IsTrial",
            "Verify", "CheckActivation", "ValidateKey",
            "Expiration", "TrialDays", "MaxUsage"
        ]
        
        findings = []
        for cs_file in self.output_dir.rglob("*.cs"):
            content = cs_file.read_text()
            for kw in keywords:
                if kw in content:
                    # 提取上下文
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if kw in line:
                            findings.append({
                                'file': str(cs_file),
                                'line': i + 1,
                                'context': '\n'.join(lines[max(0,i-2):i+3])
                            })
        
        return findings
    
    def patch_method(self, dll_path: str, class_name: str, method_name: str):
        """使用 Mono.Cecil 修改方法"""
        script = f'''
using Mono.Cecil;

var assembly = AssemblyDefinition.ReadAssembly("{dll_path}");
var type = assembly.MainModule.GetType("{class_name}");
var method = type.Methods.First(m => m.Name == "{method_name}");

// 清空方法体，返回 true
var il = method.Body.GetILProcessor();
il.Clear();
il.Append(il.Create(OpCodes.Ldc_I4_1));  // true
il.Append(il.Create(OpCodes.Ret));

assembly.Write("{dll_path}.patched");
'''
        return script

if __name__ == "__main__":
    cracker = DotNetCracker("target.exe")
    # cracker.deobfuscate()
    # cracker.find_license_checks("cleaned.exe")
```

## 常见问题

### Q: de4dot 无法处理新版 ConfuserEx？
- 使用 dnSpy 手动清空 anti-tamper 方法
- 或寻找社区更新的脱壳工具

### Q: 强签名（Strong Name）验证失败？
- 用 `sn.exe -Vr *,*` 禁用验证（开发机）
- 或重新签名：`sn.exe -R assembly.dll key.snk`

### Q: 混合模式程序（C++ + C#）？
- 先用 CFF Explorer 分离 .NET 部分
- 或直接用 x64dbg 调试原生代码

## 参考项目
- dnSpyEx: https://github.com/dnSpyEx/dnSpyEx (⭐ 5.2k)
- de4dot: https://github.com/de4dot/de4dot (⭐ 3.8k)
- Harmony: https://github.com/pardeike/Harmony (⭐ 4.1k)
