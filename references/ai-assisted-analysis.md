# AI 辅助代码分析实战指南

## 适用场景
- 自动识别保护壳类型
- 快速分析混淆代码逻辑
- 生成 Hook 脚本和 Patch 方案
- 批量处理大量样本

## 核心工具链

| 工具 | 用途 |
|------|------|
| OpenAI/Claude API | 代码分析、逻辑推理 |
| local LLM | 离线分析（隐私敏感） |
| IDA Pro + Hex-Rays | 反编译 + 伪代码 |
| Ghidra | 免费反编译 + 脚本 |
| Binary Ninja | 现代逆向平台 |
| Capstone | 反汇编引擎 |

## 标准流程

### 1. 自动识别保护壳
```python
#!/usr/bin/env python3
import hashlib
import pefile
import requests
from pathlib import Path

class ProtectorDetector:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.signatures = self._load_signatures()
        
    def _load_signatures(self) -> dict:
        """加载已知保护壳特征"""
        return {
            "UPX": {
                "sections": ["UPX0", "UPX1"],
                "strings": ["UPX!", "$Info: This file is packed with the UPX"]
            },
            "Themida": {
                "sections": [".themida", "Themida"],
                "strings": ["Themida", "Oreans Technologies"]
            },
            "VMProtect": {
                "strings": ["VMProtect", "Virtual Protect"]
            },
            "ConfuserEx": {
                "strings": ["ConfuserEx", "Ki", "Yobi"]
            },
            ".NET Reactor": {
                "strings": [".NET Reactor", "EZIRIS"]
            }
        }
    
    def analyze_pe(self, file_path: str) -> dict:
        """分析 PE 文件特征"""
        pe = pefile.PE(file_path)
        
        features = {
            "sections": [s.Name.decode().strip('\x00') for s in pe.sections],
            "imports": [entry.dll.decode() for entry in pe.DIRECTORY_ENTRY_IMPORT] if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT') else [],
            "entry_point": hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint),
            "image_base": hex(pe.OPTIONAL_HEADER.ImageBase),
            "entropy": [section.get_entropy() for section in pe.sections]
        }
        
        return features
    
    def detect_with_llm(self, file_path: str) -> str:
        """使用 LLM 识别保护壳"""
        features = self.analyze_pe(file_path)
        
        prompt = f"""分析以下 PE 文件特征，判断使用了什么保护壳/加壳工具：

节区: {features['sections']}
导入DLL: {features['imports'][:10]}
入口点: {features['entry_point']}
熵值: {features['entropy']}

只输出保护壳名称，如果没有保护壳输出 "None"。"""
        
        # 调用 LLM API
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1
            }
        )
        
        result = response.json()['choices'][0]['message']['content']
        return result.strip()
    
    def detect_local(self, file_path: str) -> str:
        """本地规则检测（无需 API）"""
        # 读取文件字符串
        with open(file_path, 'rb') as f:
            data = f.read()
            
        text = data.decode('utf-8', errors='ignore')
        
        for protector, sigs in self.signatures.items():
            for s in sigs.get("strings", []):
                if s in text:
                    return protector
                    
        # PE 节区检测
        try:
            pe = pefile.PE(file_path)
            sections = [s.Name.decode().strip('\x00') for s in pe.sections]
            for protector, sigs in self.signatures.items():
                for s in sigs.get("sections", []):
                    if s in sections:
                        return protector
        except:
            pass
            
        return "Unknown"

if __name__ == "__main__":
    detector = ProtectorDetector()
    result = detector.detect_local("target.exe")
    print(f"[+] 检测到的保护壳: {result}")
```

### 2. 自动生成 Hook 脚本
```python
class AutoHookGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    def analyze_function(self, decompiled_code: str) -> dict:
        """分析反编译代码，定位关键逻辑"""
        prompt = f"""分析以下反编译代码，找出：
1. 授权验证逻辑的位置
2. 关键变量和返回值
3. 建议的 Hook 点

代码：
{decompiled_code}

输出 JSON 格式：
{{
    "license_check_function": "函数名",
    "key_variables": ["变量名"],
    "hook_suggestion": "Hook 建议",
    "expected_return": "建议的返回值"
}}"""
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2
            }
        )
        
        import json
        result = json.loads(response.json()['choices'][0]['message']['content'])
        return result
    
    def generate_frida_script(self, analysis: dict, platform: str = "android") -> str:
        """基于分析结果生成 Frida 脚本"""
        func_name = analysis['license_check_function']
        ret_val = analysis['expected_return']
        
        if platform == "android":
            script = f"""
Java.perform(function() {{
    var targetClass = Java.use("com.example.TargetClass");
    targetClass.{func_name}.implementation = function() {{
        console.log("[+] Hooked: {func_name}");
        return {ret_val};
    }};
}});
"""
        elif platform == "ios":
            script = f"""
Interceptor.attach(Module.findExportByName(null, "{func_name}"), {{
    onLeave: function(retval) {{
        console.log("[+] Hooked: {func_name}");
        retval.replace({ret_val});
    }}
}});
"""
        return script
```

### 3. 批量样本分析
```python
class BatchAnalyzer:
    def __init__(self, detector: ProtectorDetector, hook_gen: AutoHookGenerator):
        self.detector = detector
        self.hook_gen = hook_gen
        
    def analyze_directory(self, samples_dir: str, output_dir: str = "./analysis"):
        """批量分析样本目录"""
        from pathlib import Path
        import json
        
        samples = Path(samples_dir).glob("*")
        results = []
        
        for sample in samples:
            if not sample.is_file():
                continue
                
            print(f"[+] 分析: {sample.name}")
            
            # 检测保护壳
            protector = self.detector.detect_local(str(sample))
            
            # 如果是已知保护壳，生成脱壳建议
            if protector != "Unknown":
                unpacker = self._suggest_unpacker(protector)
            else:
                unpacker = "手动分析"
            
            result = {
                "file": sample.name,
                "protector": protector,
                "unpacker": unpacker,
                "size": sample.stat().st_size
            }
            results.append(result)
            
        # 保存结果
        output = Path(output_dir)
        output.mkdir(exist_ok=True)
        with open(output / "analysis.json", "w") as f:
            json.dump(results, f, indent=2)
            
        return results
    
    def _suggest_unpacker(self, protector: str) -> str:
        """根据保护壳推荐脱壳工具"""
        mapping = {
            "UPX": "upx -d",
            "Themida": "x64dbg + ScyllaHide + Themidie",
            "VMProtect": "VMProtectUnpacker / 手动Dump",
            "ConfuserEx": "de4dot + dnSpy",
            ".NET Reactor": "de4dot + dnSpy",
            "Packman": "QuickUnpack / OEP Finder"
        }
        return mapping.get(protector, "未知工具")

if __name__ == "__main__":
    detector = ProtectorDetector()
    hook_gen = AutoHookGenerator("your-api-key")
    analyzer = BatchAnalyzer(detector, hook_gen)
    
    results = analyzer.analyze_directory("./samples")
    print(f"[+] 分析了 {len(results)} 个样本")
```

## 常见问题

### Q: API 费用过高？
- 使用本地模型（llama.cpp、ollama）
- 批量处理减少 API 调用
- 缓存常见样本结果

### Q: LLM 分析不准确？
- 提供足够上下文（多函数、调用链）
- 使用 few-shot prompting
- 结合传统规则验证

### Q: 隐私敏感样本？
- 使用本地 LLM（完全离线）
- 不上传二进制到云端
- 仅上传反编译后的伪代码

## 参考
- ollama: https://github.com/ollama/ollama (⭐ 50k+)
- llama.cpp: https://github.com/ggerganov/llama.cpp (⭐ 60k+)
- capstone: https://github.com/capstone-engine/capstone (⭐ 7k+)
