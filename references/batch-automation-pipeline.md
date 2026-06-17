# 批量自动化流水线实战指南

## 适用场景
- 批量 APK 自动破解
- CI/CD 集成破解流程
- 大规模样本分析
- 自动化测试破解完整性

## 核心架构

```
GitHub Actions / Jenkins
    ↓
[下载/上传样本]
    ↓
[保护壳检测]
    ↓
[自动脱壳]
    ↓
[反编译/分析]
    ↓
[自动Patch]
    ↓
[完整性校验]
    ↓
[输出结果]
```

## GitHub Actions 工作流

### 1. 基础工作流
```yaml
# .github/workflows/crack-pipeline.yml
name: Crack Pipeline

on:
  workflow_dispatch:
    inputs:
      sample_url:
        description: '样本下载链接'
        required: true
      target_package:
        description: '目标包名'
        required: true

jobs:
  crack:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install frida-tools apktool jadx
    
    - name: Download sample
      run: |
        wget ${{ github.event.inputs.sample_url }} -O sample.apk
    
    - name: Detect protector
      run: |
        python -c "
        from crack_engine import ProtectorDetector
        d = ProtectorDetector()
        result = d.detect_apk('sample.apk')
        print(f'Protector: {result}')
        with open('detect_result.json', 'w') as f:
            import json
            json.dump(result, f)
        "
    
    - name: Auto unpack
      run: |
        python -c "
        from crack_engine import AutoUnpacker
        import json
        with open('detect_result.json') as f:
            result = json.load(f)
        u = AutoUnpacker(result['protector'])
        u.unpack('sample.apk', 'unpacked/')
        "
    
    - name: Analyze and patch
      run: |
        python -c "
        from crack_engine import LicenseFinder, Patcher
        f = LicenseFinder()
        patches = f.find('unpacked/')
        p = Patcher()
        p.apply(patches, 'unpacked/')
        "
    
    - name: Repack and verify
      run: |
        python -c "
        from crack_engine import Repacker, IntegrityChecker
        r = Repacker()
        r.repack('unpacked/', 'output.apk')
        c = IntegrityChecker()
        score = c.check('output.apk')
        print(f'Integrity Score: {score}/100')
        "
    
    - name: Upload result
      uses: actions/upload-artifact@v3
      with:
        name: cracked-apk
        path: output.apk
```

### 2. Python 流水线引擎
```python
#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class PipelineResult:
    stage: str
    success: bool
    output: str
    artifacts: List[str]

class CrackPipeline:
    def __init__(self, config_path: str = "pipeline.json"):
        self.config = json.load(open(config_path))
        self.results = []
        self.work_dir = Path("pipeline_work")
        self.work_dir.mkdir(exist_ok=True)
        
    def run(self, sample_path: str) -> List[PipelineResult]:
        """执行完整流水线"""
        stages = [
            self._stage_detect,
            self._stage_unpack,
            self._stage_analyze,
            self._stage_patch,
            self._stage_repack,
            self._stage_verify
        ]
        
        current_input = sample_path
        
        for stage in stages:
            result = stage(current_input)
            self.results.append(result)
            
            if not result.success:
                print(f"[-] 流水线中断于: {result.stage}")
                break
                
            if result.artifacts:
                current_input = result.artifacts[0]
                
        return self.results
    
    def _stage_detect(self, sample: str) -> PipelineResult:
        """阶段1: 检测保护壳"""
        try:
            from crack_engine import ProtectorDetector
            detector = ProtectorDetector()
            result = detector.detect(sample)
            
            output_file = self.work_dir / "detect_result.json"
            json.dump(result, open(output_file, 'w'))
            
            return PipelineResult(
                stage="detect",
                success=True,
                output=json.dumps(result),
                artifacts=[str(output_file)]
            )
        except Exception as e:
            return PipelineResult(
                stage="detect",
                success=False,
                output=str(e),
                artifacts=[]
            )
    
    def _stage_unpack(self, detect_result: str) -> PipelineResult:
        """阶段2: 自动脱壳"""
        try:
            result = json.load(open(detect_result))
            protector = result['protector']
            
            # 根据保护壳选择脱壳工具
            unpackers = {
                'UPX': ['upx', '-d', 'sample.exe', '-o', 'unpacked.exe'],
                'Themida': ['python', 'themidie.py', 'sample.exe'],
                'ConfuserEx': ['de4dot', 'sample.exe', '-o', 'unpacked.exe'],
                'None': ['cp', 'sample.exe', 'unpacked.exe']
            }
            
            cmd = unpackers.get(protector, unpackers['None'])
            subprocess.run(cmd, check=True, cwd=self.work_dir)
            
            return PipelineResult(
                stage="unpack",
                success=True,
                output=f"Unpacked with {protector} tool",
                artifacts=[str(self.work_dir / "unpacked.exe")]
            )
        except Exception as e:
            return PipelineResult(
                stage="unpack",
                success=False,
                output=str(e),
                artifacts=[]
            )
    
    def _stage_analyze(self, unpacked: str) -> PipelineResult:
        """阶段3: 分析授权逻辑"""
        try:
            from crack_engine import LicenseFinder
            finder = LicenseFinder()
            patches = finder.find(unpacked)
            
            output_file = self.work_dir / "patches.json"
            json.dump(patches, open(output_file, 'w'))
            
            return PipelineResult(
                stage="analyze",
                success=True,
                output=f"Found {len(patches)} patch points",
                artifacts=[str(output_file)]
            )
        except Exception as e:
            return PipelineResult(
                stage="analyze",
                success=False,
                output=str(e),
                artifacts=[]
            )
    
    def _stage_patch(self, patches_file: str) -> PipelineResult:
        """阶段4: 应用Patch"""
        try:
            patches = json.load(open(patches_file))
            
            from crack_engine import Patcher
            patcher = Patcher()
            patcher.apply(patches, str(self.work_dir / "unpacked.exe"))
            
            return PipelineResult(
                stage="patch",
                success=True,
                output=f"Applied {len(patches)} patches",
                artifacts=[str(self.work_dir / "unpacked.exe")]
            )
        except Exception as e:
            return PipelineResult(
                stage="patch",
                success=False,
                output=str(e),
                artifacts=[]
            )
    
    def _stage_repack(self, patched: str) -> PipelineResult:
        """阶段5: 重新打包"""
        try:
            output = self.work_dir / "output.exe"
            
            # 如果是 APK，需要重新签名
            if patched.endswith('.apk'):
                subprocess.run([
                    'apksigner', 'sign',
                    '--ks', 'debug.keystore',
                    '--ks-pass', 'pass:android',
                    '--in', patched,
                    '--out', str(output)
                ], check=True)
            else:
                shutil.copy2(patched, output)
            
            return PipelineResult(
                stage="repack",
                success=True,
                output="Repacked successfully",
                artifacts=[str(output)]
            )
        except Exception as e:
            return PipelineResult(
                stage="repack",
                success=False,
                output=str(e),
                artifacts=[]
            )
    
    def _stage_verify(self, output: str) -> PipelineResult:
        """阶段6: 完整性校验"""
        try:
            from crack_engine import IntegrityChecker
            checker = IntegrityChecker()
            score = checker.check(output)
            
            report = {
                'score': score,
                'grade': 'A' if score >= 90 else 'B' if score >= 70 else 'C',
                'passed': score >= 70
            }
            
            return PipelineResult(
                stage="verify",
                success=report['passed'],
                output=json.dumps(report),
                artifacts=[output]
            )
        except Exception as e:
            return PipelineResult(
                stage="verify",
                success=False,
                output=str(e),
                artifacts=[]
            )

if __name__ == "__main__":
    pipeline = CrackPipeline()
    results = pipeline.run("sample.exe")
    
    for r in results:
        status = "✓" if r.success else "✗"
        print(f"{status} {r.stage}: {r.output}")
```

## 常见问题

### Q: GitHub Actions 运行时间限制？
- 免费版 2000 分钟/月
- 大样本使用自托管 runner
- 或分阶段触发

### Q: 敏感样本隐私？
- 使用自托管 CI（本地 Jenkins）
- 不上传到公共仓库
- 加密存储样本

### Q: 流水线失败处理？
- 设置重试机制（3次）
- 人工审核失败样本
- 记录失败日志

## 参考
- GitHub Actions: https://docs.github.com/en/actions
- Jenkins: https://www.jenkins.io/
