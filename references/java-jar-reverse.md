# Java JAR 逆向实战指南

## 适用场景
- Java 桌面程序逆向（Swing/JavaFX）
- JAR 反编译、修改、重新打包
- 绕过 ProGuard/Allatori 混淆

## 核心工具链

| 工具 | 用途 | 下载 |
|------|------|------|
| JD-GUI | 经典 Java 反编译器 | http://java-decompiler.github.io |
| CFR | 现代 Java 反编译器 | https://www.benf.org/other/cfr |
| FernFlower | IntelliJ 内置反编译器 | https://github.com/JetBrains/intellij-community/tree/master/plugins/java-decompiler/engine |
| Bytecode Viewer | 多引擎反编译 GUI | https://github.com/Konloch/bytecode-viewer |
| Recaf | 现代 Java 字节码编辑器 | https://github.com/Col-E/Recaf |
| JADX | Android + Java 反编译 | https://github.com/skylot/jadx |
| Procyon | 反编译器 | https://github.com/mstrobel/procyon |

## 标准流程

### 1. 解压 JAR
```bash
# JAR 本质是 ZIP
mkdir jar_source
cd jar_source
jar xf ../target.jar
# 或
unzip ../target.jar -d ./
```

### 2. 反编译 class 文件
```bash
# 方法1：CFR 命令行
java -jar cfr.jar target.jar --outputdir ./src

# 方法2：FernFlower
java -jar fernflower.jar target.jar ./src/

# 方法3：批量反编译目录
for f in $(find . -name "*.class"); do
    java -jar cfr.jar "$f" --outputdir ./src
done
```

### 3. 定位授权逻辑
```bash
# 搜索关键词
grep -r "license\|trial\|isRegistered\|checkActivation" ./src/ --include="*.java"

# 常见类名
LicenseManager.java
ActivationChecker.java
RegistrationDialog.java
```

### 4. 修改源码
```java
// LicenseManager.java - 原代码
public class LicenseManager {
    public boolean validateLicense(String key) {
        return serverVerify(key);
    }
    
    private boolean serverVerify(String key) {
        // 网络验证
        HttpResponse response = httpClient.post("https://api.example.com/verify", key);
        return response.isSuccess();
    }
}

// 修改后
public class LicenseManager {
    public boolean validateLicense(String key) {
        return true;  // 直接返回 true
    }
    
    private boolean serverVerify(String key) {
        return true;  // 跳过网络验证
    }
}
```

### 5. 重新编译
```bash
# 编译修改后的代码
javac -cp "lib/*:target.jar" -d ./out src/com/example/LicenseManager.java

# 更新 JAR
jar uf target.jar -C ./out com/example/LicenseManager.class

# 或重新打包完整 JAR
cd ./out
jar cvf ../target_patched.jar .
```

### 6. 使用 Recaf 直接修改字节码（无需反编译）
```bash
# 启动 Recaf
java -jar recaf.jar

# 1. File -> Load -> 选择 target.jar
# 2. 导航到目标类
# 3. 右键 -> Edit with assembler
# 4. 修改字节码指令
# 5. File -> Export
```

### 7. 自动化 Python 工作流
```python
#!/usr/bin/env python3
import subprocess
import zipfile
import shutil
from pathlib import Path

class JavaCracker:
    def __init__(self, jar_path: str):
        self.jar_path = Path(jar_path)
        self.work_dir = Path("java_tmp")
        self.src_dir = self.work_dir / "src"
        
    def extract(self):
        """解压 JAR"""
        self.work_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(self.jar_path, 'r') as z:
            z.extractall(self.work_dir)
        print(f"[+] 已解压 {self.jar_path}")
    
    def decompile(self):
        """反编译所有 class"""
        self.src_dir.mkdir(exist_ok=True)
        
        # 使用 CFR
        cfr_jar = "cfr.jar"
        cmd = [
            "java", "-jar", cfr_jar,
            str(self.jar_path),
            "--outputdir", str(self.src_dir)
        ]
        subprocess.run(cmd, check=True)
        print(f"[+] 已反编译到 {self.src_dir}")
    
    def find_license_checks(self) -> list:
        """定位授权检查"""
        keywords = ["license", "trial", "isRegistered", "checkActivation", "validateKey"]
        findings = []
        
        for java_file in self.src_dir.rglob("*.java"):
            content = java_file.read_text()
            for kw in keywords:
                if kw in content:
                    findings.append({
                        'file': str(java_file.relative_to(self.src_dir)),
                        'keyword': kw
                    })
                    
        return findings
    
    def patch_with_recaf(self, class_name: str, method_name: str):
        """生成 Recaf 修改脚本"""
        # Recaf 支持脚本化操作
        script = f'''
// Recaf script
var targetClass = classes["{class_name}"];
var method = targetClass.getMethods().stream()
    .filter(m -> m.getName().equals("{method_name}"))
    .findFirst()
    .orElse(null);

if (method != null) {{
    // 清空方法体，返回 true
    var assembler = method.getAssembler();
    assembler.clear();
    assembler.add("ICONST_1");  // true
    assembler.add("IRETURN");
    assembler.save();
    System.out.println("[+] Patched {class_name}.{method_name}");
}}
'''
        return script
    
    def repack(self, output_path: str):
        """重新打包 JAR"""
        # 复制原 JAR，替换修改的 class
        shutil.copy2(self.jar_path, output_path)
        
        with zipfile.ZipFile(output_path, 'a') as z:
            for class_file in self.work_dir.rglob("*.class"):
                arcname = str(class_file.relative_to(self.work_dir))
                z.write(class_file, arcname)
                
        print(f"[+] 已重新打包 {output_path}")

if __name__ == "__main__":
    cracker = JavaCracker("target.jar")
    cracker.extract()
    cracker.decompile()
    findings = cracker.find_license_checks()
    print(f"找到 {len(findings)} 个授权检查点")
```

## 常见问题

### Q: ProGuard 混淆类名？
- 搜索字符串常量（未被混淆）
- 分析调用图定位关键类
- 使用 JADX 的反混淆功能

### Q: 有 JNI 原生库？
- 分析 .so/.dll 文件
- 使用 IDA/Ghidra 逆向

### Q: 签名校验？
- 修改 META-INF/MANIFEST.MF
- 或使用 jarsigner 重新签名

## 参考项目
- Recaf: https://github.com/Col-E/Recaf (⭐ 5.2k)
- Bytecode Viewer: https://github.com/Konloch/bytecode-viewer (⭐ 4.1k)
- JADX: https://github.com/skylot/jadx (⭐ 42k)
