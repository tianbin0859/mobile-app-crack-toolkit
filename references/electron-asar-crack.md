# Electron/ASAR 破解实战指南

## 适用场景
- Electron 桌面应用（Discord、VS Code、Slack 类）
- 提取/修改打包的 JS 源码
- 绕过授权、去广告、功能解锁

## 核心工具链

| 工具 | 用途 |
|------|------|
| asar | Electron 官方打包/解包工具 | npm install -g asar |
| 7-Zip | 替代解包 | 已安装 |
| Node.js | 运行修改后的代码 | 已安装 |
| electron/asar | ASAR 库 | npm install asar |

## 标准流程

### 1. 识别 Electron 应用
```bash
# Windows
ls app/resources/app.asar       # 存在 = Electron
ls app/resources/electron.asar  # 辅助文件
strings app.exe | grep "electron"

# macOS
ls MyApp.app/Contents/Resources/app.asar

# 检查 package.json
asar extract app.asar ./asar_tmp
cat asar_tmp/package.json | grep "name\|version"
```

### 2. 解包 ASAR
```bash
# 全局安装 asar
npm install -g asar

# 解包
asar extract app.asar ./app_source

# 或 7z 直接解压（某些版本）
7z x app.asar -o./app_source/
```

### 3. 定位关键代码
```bash
# 搜索授权/验证相关代码
grep -r "license" ./app_source/ --include="*.js"
grep -r "trial" ./app_source/ --include="*.js"
grep -r "isPro\|isPremium\|isVIP" ./app_source/ --include="*.js"

# 搜索广告相关
grep -r "advertisement\|ads\|banner" ./app_source/ --include="*.js"
```

### 4. 修改源码
```javascript
// 原代码（renderer.js）
function checkLicense() {
    const license = fs.readFileSync('license.key');
    return verifyLicense(license);
}

function isPremium() {
    return checkLicense();
}

// 修改后
function checkLicense() {
    return true;  // 直接返回 true
}

function isPremium() {
    return true;  // 解锁高级功能
}
```

### 5. 重新打包
```bash
# 备份原文件
cp app.asar app.asar.bak

# 重新打包
asar pack ./app_source app.asar

# 替换原文件（Windows 需先关闭应用）
cp app.asar /path/to/app/resources/app.asar
```

### 6. 自动化 Python 脚本
```python
#!/usr/bin/env python3
import subprocess
import json
import shutil
from pathlib import Path

class ElectronCracker:
    def __init__(self, app_path: str):
        self.app_path = Path(app_path)
        self.asar_path = self._find_asar()
        self.work_dir = Path("electron_tmp")
        
    def _find_asar(self) -> Path:
        """定位 app.asar 文件"""
        candidates = [
            self.app_path / "resources" / "app.asar",
            self.app_path / "Contents" / "Resources" / "app.asar",
            self.app_path / "app.asar"
        ]
        for c in candidates:
            if c.exists():
                return c
        raise FileNotFoundError("app.asar not found")
    
    def extract(self):
        """解包 ASAR"""
        self.work_dir.mkdir(exist_ok=True)
        subprocess.run(["asar", "extract", str(self.asar_path), str(self.work_dir)], check=True)
        print(f"[+] 已解包到 {self.work_dir}")
    
    def find_license_checks(self) -> list:
        """定位授权检查代码"""
        keywords = ["license", "trial", "isPro", "isPremium", "isVIP", "isRegistered", "checkActivation"]
        findings = []
        
        for js_file in self.work_dir.rglob("*.js"):
            content = js_file.read_text()
            for kw in keywords:
                if kw in content:
                    findings.append({
                        'file': str(js_file.relative_to(self.work_dir)),
                        'keyword': kw
                    })
                    
        return findings
    
    def patch_license(self, file_path: str, method_name: str):
        """修改授权方法"""
        target = self.work_dir / file_path
        content = target.read_text()
        
        # 简单替换：return false -> return true
        # 或使用正则定位方法体
        import re
        
        pattern = rf'function\s+{method_name}\s*\([^)]*\)\s*\{{[^}}]*\}}'
        replacement = f'function {method_name}() {{ return true; }}'
        
        new_content = re.sub(pattern, replacement, content)
        target.write_text(new_content)
        
        print(f"[+] 已修改 {file_path}")
    
    def repack(self):
        """重新打包"""
        backup = self.asar_path.with_suffix('.asar.bak')
        shutil.copy2(self.asar_path, backup)
        
        subprocess.run(["asar", "pack", str(self.work_dir), str(self.asar_path)], check=True)
        print(f"[+] 已重新打包 {self.asar_path}")
    
    def cleanup(self):
        """清理临时文件"""
        shutil.rmtree(self.work_dir, ignore_errors=True)

if __name__ == "__main__":
    cracker = ElectronCracker("/path/to/app")
    cracker.extract()
    findings = cracker.find_license_checks()
    print(f"找到 {len(findings)} 个授权检查点")
    # cracker.patch_license("main.js", "isPremium")
    # cracker.repack()
    # cracker.cleanup()
```

## 常见问题

### Q: ASAR 加密或完整性校验？
- 检查 main.js 是否有 asar 完整性验证
- 修改验证逻辑或 Hook fs 模块

### Q: 代码混淆（webpack/uglify）？
- 使用 js-beautify 格式化
- 搜索关键字符串定位逻辑

### Q: 主进程和渲染进程分离？
- 主进程（main.js）：Node 环境，可修改
- 渲染进程（preload.js）：Chromium 环境

## 参考
- asar: https://github.com/electron/asar
- Electron 文档: https://www.electronjs.org/docs/latest/tutorial/application-distribution
