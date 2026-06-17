# Unity IL2CPP 逆向实战指南

## 适用场景
- Unity 游戏/应用使用 IL2CPP 构建（替代 Mono 运行时）
- 需要提取 C# 脚本、修改游戏逻辑、绕过保护
- 手游逆向（Unity 占比 > 60%）

## 核心工具链

| 工具 | 用途 | 下载 |
|------|------|------|
| Il2CppDumper | 从 `global-metadata.dat` + `GameAssembly.dll` 还原 DLL | https://github.com/Perfare/Il2CppDumper |
| Il2CppInspector | 替代方案，支持更多版本 | https://github.com/djkaty/Il2CppInspector |
| frida-il2cpp-bridge | 运行时 Hook IL2CPP 方法 | https://github.com/vfsfitvnm/frida-il2cpp-bridge |
| dnSpy | 反编译还原的 DLL | https://github.com/dnSpy/dnSpy |
| AssetStudio | 提取 Unity 资源（图片、音频、模型） | https://github.com/Perfare/AssetStudio |
| frida | 动态插桩、运行时修改 | 已集成 |

## 标准流程

### 1. 识别 IL2CPP 构建
```bash
# Android APK
unzip game.apk -d game/
ls game/lib/arm64-v8a/libil2cpp.so    # 存在 = IL2CPP
ls game/assets/bin/Data/Managed/Metadata/global-metadata.dat  # 元数据文件

# Windows EXE
ls GameAssembly.dll                     # 存在 = IL2CPP
ls *_Data/il2cpp_data/Metadata/global-metadata.dat
```

### 2. 提取并还原 DLL（Android）
```bash
# 从 APK 提取关键文件
adb pull /data/app/com.game.package/lib/arm64/libil2cpp.so ./
adb pull /data/app/com.game.package/assets/bin/Data/Managed/Metadata/global-metadata.dat ./

# 使用 Il2CppDumper 还原
Il2CppDumper.exe libil2cpp.so global-metadata.dat ./output/
# 输出：dump.cs（类结构） + DummyDll（可反编译的 DLL）
```

### 3. 提取并还原 DLL（Windows）
```bash
# 定位文件
GameAssembly.dll
*_Data/il2cpp_data/Metadata/global-metadata.dat

Il2CppDumper.exe GameAssembly.dll global-metadata.dat ./output/
```

### 4. 分析还原的代码
```bash
# 用 dnSpy 打开 DummyDll
# 搜索关键类：CoinManager, PlayerData, IAPManager, AdsManager
# 定位需要修改的方法
```

### 5. 运行时 Hook（frida-il2cpp-bridge）
```javascript
// frida_script.js
import { Il2Cpp } from "frida-il2cpp-bridge";

Il2Cpp.perform(() => {
    // 定位 Assembly-CSharp.dll
    const assembly = Il2Cpp.Domain.assembly("Assembly-CSharp");
    const image = assembly.image;
    
    // 定位类
    const coinManager = image.class("CoinManager");
    
    // Hook 方法：修改金币数量
    coinManager.method("AddCoins").implementation = function (amount) {
        console.log(`[+] AddCoins called with: ${amount}`);
        // 强制增加 99999
        return this.method("AddCoins").invoke(99999);
    };
    
    // Hook 属性：直接修改金币值
    const playerData = image.class("PlayerData");
    playerData.field("<Coins>k__BackingField").value = 9999999;
});
```

### 6. 自动化 Python 脚本
```python
#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

class UnityIL2CPPAnalyzer:
    def __init__(self, target_path: str):
        self.target = Path(target_path)
        self.output_dir = Path("il2cpp_output")
        
    def extract_from_apk(self, apk_path: str):
        """从 APK 提取 IL2CPP 文件"""
        import zipfile
        with zipfile.ZipFile(apk_path, 'r') as z:
            # 提取 libil2cpp.so
            lib_path = None
            for name in z.namelist():
                if 'libil2cpp.so' in name:
                    lib_path = name
                    z.extract(name, self.output_dir)
            
            # 提取 global-metadata.dat
            meta_path = None
            for name in z.namelist():
                if 'global-metadata.dat' in name:
                    meta_path = name
                    z.extract(name, self.output_dir)
            
            return lib_path, meta_path
    
    def dump_with_il2cppdumper(self, lib_path: str, meta_path: str):
        """运行 Il2CppDumper 还原 DLL"""
        cmd = [
            "Il2CppDumper.exe",
            str(lib_path),
            str(meta_path),
            str(self.output_dir)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    
    def find_key_methods(self, dump_cs_path: str):
        """从 dump.cs 定位关键方法"""
        keywords = [
            "Coin", "Gold", "Gem", "Diamond", "Money",
            "IAP", "Purchase", "Buy", "Pay",
            "Ads", "AdManager", "Advertisement",
            "Level", "Exp", "Experience", "Unlock"
        ]
        
        findings = []
        with open(dump_cs_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                for kw in keywords:
                    if kw in line:
                        findings.append((line_num, line.strip()))
        
        return findings
    
    def generate_frida_script(self, class_name: str, method_name: str):
        """生成 frida-il2cpp-bridge 脚本"""
        script = f'''import {{ Il2Cpp }} from "frida-il2cpp-bridge";

Il2Cpp.perform(() => {{
    const assembly = Il2Cpp.Domain.assembly("Assembly-CSharp");
    const image = assembly.image;
    const targetClass = image.class("{class_name}");
    
    targetClass.method("{method_name}").implementation = function (...args) {{
        console.log("[+] Hooked: {class_name}.{method_name}");
        console.log("    Args:", args);
        const result = this.method("{method_name}").invoke(...args);
        console.log("    Result:", result);
        return result;
    }};
}});
'''
        return script

if __name__ == "__main__":
    analyzer = UnityIL2CPPAnalyzer("./target")
    # 使用示例
    # analyzer.extract_from_apk("game.apk")
    # analyzer.dump_with_il2cppdumper("libil2cpp.so", "global-metadata.dat")
```

## 常见问题

### Q: global-metadata.dat 加密/缺失？
- 使用 `frida-il2cpp-bridge` 运行时 dump
- 或尝试 `Il2CppInspector` 的自动解密

### Q: libil2cpp.so 被加壳？
- 先脱壳（UPX/Custom packer）
- 再运行 Il2CppDumper

### Q: 还原的 DLL 无法编译？
- DummyDll 仅用于分析，不可编译
- 修改需通过 frida Hook 或内存 Patch

### Q: 手游有反调试？
- 使用 `frida --no-pause` 启动
- 或配合 `magisk` + `zygisk` 隐藏 root

## 进阶技巧

1. **自动化符号还原**：结合 `il2cppdumper` + `ghidra` 脚本批量重命名函数
2. **网络协议分析**：Hook `UnityWebRequest` 类拦截 HTTP 请求
3. **存档修改**：定位 `PlayerPrefs` 或自定义存档加密逻辑
4. **IL2CPP 版本兼容**：不同 Unity 版本 metadata 格式不同，需匹配工具版本

## 参考项目
- Il2CppDumper: https://github.com/Perfare/Il2CppDumper (⭐ 7.8k)
- frida-il2cpp-bridge: https://github.com/vfsfitvnm/frida-il2cpp-bridge (⭐ 1.2k)
- Il2CppInspector: https://github.com/djkaty/Il2CppInspector (⭐ 2.1k)
