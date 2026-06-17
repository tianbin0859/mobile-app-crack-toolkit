import re, json, os
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

class ObfuscationType(Enum):
    CONTROL_FLOW = "control_flow"  # 控制流扁平化
    STRING = "string"  # 字符串加密
    RENAME = "rename"  # 标识符重命名
    REFLECTION = "reflection"  # 反射替换
    DYNAMIC = "dynamic"  # 动态加载
    JNI = "jni"  # JNI隐藏
    PACKER = "packer"  # 加壳

@dataclass
class StringEntry:
    encrypted: str
    decrypted: str
    method: str  # 解密方法
    offset: int

@dataclass
class ControlFlowBlock:
    id: int
    instructions: List[str]
    successors: List[int]
    predecessors: List[int]
    is_dispatcher: bool = False

@dataclass
class DeobfuscationReport:
    apk_path: str
    obfuscation_types: List[ObfuscationType]
    strings_recovered: List[StringEntry]
    control_flow_restored: List[ControlFlowBlock]
    classes_deobfuscated: List[str]
    success_rate: float

class DeobfuscationEngine:
    """反混淆增强引擎 - 控制流还原 + 字符串解密"""
    
    def __init__(self):
        self.string_patterns = [
            # 常见字符串解密模式
            (r"invoke-static \{[^}]+\}, L([^;]+);->([^\(]+)\(Ljava/lang/String;\)Ljava/lang/String;",
             "静态解密方法"),
            (r"invoke-static \{[^}]+\}, L([^;]+);->([^\(]+)\(\[B\)Ljava/lang/String;",
             "字节数组解密"),
            (r"invoke-direct \{[^}]+\}, L([^;]+);-><init>\(Ljava/lang/String;\)",
             "构造器解密"),
        ]
        
        self.control_flow_patterns = [
            # 控制流扁平化特征
            r"packed-switch",
            r"sparse-switch",
            r"if-eq.*:goto",
            r"if-ne.*:goto",
        ]
    
    def analyze(self, apk_path: str) -> DeobfuscationReport:
        """分析APK的混淆类型"""
        obfuscation_types = []
        
        # 检查各种混淆特征
        if self._has_control_flow_obfuscation(apk_path):
            obfuscation_types.append(ObfuscationType.CONTROL_FLOW)
        
        if self._has_string_obfuscation(apk_path):
            obfuscation_types.append(ObfuscationType.STRING)
        
        if self._has_renaming(apk_path):
            obfuscation_types.append(ObfuscationType.RENAME)
        
        if self._has_reflection(apk_path):
            obfuscation_types.append(ObfuscationType.REFLECTION)
        
        if self._has_dynamic_loading(apk_path):
            obfuscation_types.append(ObfuscationType.DYNAMIC)
        
        if self._has_jni_obfuscation(apk_path):
            obfuscation_types.append(ObfuscationType.JNI)
        
        return DeobfuscationReport(
            apk_path=apk_path,
            obfuscation_types=obfuscation_types,
            strings_recovered=[],
            control_flow_restored=[],
            classes_deobfuscated=[],
            success_rate=0.0
        )
    
    def _has_control_flow_obfuscation(self, apk_path: str) -> bool:
        """检测控制流混淆"""
        try:
            import zipfile
            with zipfile.ZipFile(apk_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.dex'):
                        data = zf.read(name)
                        # 检查switch指令密度
                        switch_count = data.count(b'\x2b') + data.count(b'\x2c')  # packed/sparse-switch
                        if switch_count > 100:
                            return True
            return False
        except:
            return False
    
    def _has_string_obfuscation(self, apk_path: str) -> bool:
        """检测字符串混淆"""
        try:
            import zipfile
            with zipfile.ZipFile(apk_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.dex'):
                        data = zf.read(name)
                        # 检查加密字符串特征
                        if b'Ljava/lang/String;-><init>([B)V' in data:
                            return True
            return False
        except:
            return False
    
    def _has_renaming(self, apk_path: str) -> bool:
        """检测标识符重命名"""
        try:
            import zipfile
            with zipfile.ZipFile(apk_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.dex'):
                        # 检查短类名密度
                        short_names = 0
                        total_names = 0
                        for cls_name in self._extract_class_names(zf.read(name)):
                            total_names += 1
                            if len(cls_name) <= 3:
                                short_names += 1
                        
                        if total_names > 0 and short_names / total_names > 0.3:
                            return True
            return False
        except:
            return False
    
    def _has_reflection(self, apk_path: str) -> bool:
        """检测反射替换"""
        try:
            import zipfile
            with zipfile.ZipFile(apk_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.dex'):
                        data = zf.read(name)
                        if b'Ljava/lang/reflect/Method;->invoke' in data:
                            return True
            return False
        except:
            return False
    
    def _has_dynamic_loading(self, apk_path: str) -> bool:
        """检测动态加载"""
        try:
            import zipfile
            with zipfile.ZipFile(apk_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.dex'):
                        data = zf.read(name)
                        if b'DexClassLoader' in data or b'PathClassLoader' in data:
                            return True
            return False
        except:
            return False
    
    def _has_jni_obfuscation(self, apk_path: str) -> bool:
        """检测JNI混淆"""
        try:
            import zipfile
            with zipfile.ZipFile(apk_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.so'):
                        return True
            return False
        except:
            return False
    
    def _extract_class_names(self, dex_data: bytes) -> List[str]:
        """从DEX数据提取类名"""
        # 简化的类名提取
        class_names = []
        # 查找L...;格式的类名
        for match in re.finditer(b'L[A-Za-z0-9_$\/]+;', dex_data):
            name = match.group(0).decode('utf-8', errors='ignore')
            class_names.append(name)
        return class_names
    
    def restore_strings(self, smali_code: str) -> List[StringEntry]:
        """恢复加密字符串"""
        recovered = []
        
        # 查找字符串解密模式
        for pattern, desc in self.string_patterns:
            for match in re.finditer(pattern, smali_code):
                # 提取加密字符串和解密方法
                encrypted = match.group(0)
                method_class = match.group(1)
                method_name = match.group(2)
                
                # 尝试解密
                decrypted = self._try_decrypt(encrypted, method_class, method_name)
                
                if decrypted:
                    recovered.append(StringEntry(
                        encrypted=encrypted,
                        decrypted=decrypted,
                        method=f"{method_class}->{method_name}",
                        offset=match.start()
                    ))
        
        return recovered
    
    def _try_decrypt(self, encrypted: str, method_class: str, method_name: str) -> Optional[str]:
        """尝试解密字符串"""
        # 常见解密算法
        # 1. Base64
        try:
            import base64
            decoded = base64.b64decode(encrypted)
            return decoded.decode('utf-8')
        except:
            pass
        
        # 2. XOR
        try:
            # 尝试常见XOR密钥
            for key in [0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0]:
                decrypted = ''.join(chr(ord(c) ^ key) for c in encrypted)
                if all(32 <= ord(c) < 127 for c in decrypted):
                    return decrypted
        except:
            pass
        
        # 3. 简单替换
        try:
            # ROT13
            decrypted = encrypted.encode('rot13')
            return decrypted
        except:
            pass
        
        return None
    
    def restore_control_flow(self, smali_code: str) -> List[ControlFlowBlock]:
        """还原控制流"""
        blocks = []
        
        # 解析基本块
        current_block = []
        block_id = 0
        
        for line in smali_code.split('\n'):
            line = line.strip()
            
            if not line:
                continue
            
            # 标签行开始新块
            if line.startswith(':'):
                if current_block:
                    blocks.append(ControlFlowBlock(
                        id=block_id,
                        instructions=current_block,
                        successors=[],
                        predecessors=[]
                    ))
                    block_id += 1
                    current_block = []
            
            current_block.append(line)
            
            # 跳转指令结束当前块
            if any(line.startswith(op) for op in ['goto', 'if-', 'return', 'throw']):
                blocks.append(ControlFlowBlock(
                    id=block_id,
                    instructions=current_block,
                    successors=[],
                    predecessors=[]
                ))
                block_id += 1
                current_block = []
        
        # 添加最后一个块
        if current_block:
            blocks.append(ControlFlowBlock(
                id=block_id,
                instructions=current_block,
                successors=[],
                predecessors=[]
            ))
        
        # 构建控制流图
        for i, block in enumerate(blocks):
            last_inst = block.instructions[-1] if block.instructions else ""
            
            # 分析跳转目标
            if 'goto' in last_inst:
                target = self._extract_goto_target(last_inst)
                if target is not None:
                    block.successors.append(target)
            
            elif 'if-' in last_inst:
                # 条件跳转有两个后继
                block.successors.append(i + 1)  # 不跳转
                target = self._extract_goto_target(last_inst)
                if target is not None:
                    block.successors.append(target)
            
            elif 'return' in last_inst or 'throw' in last_inst:
                pass  # 无后继
            
            else:
                # 顺序执行
                if i + 1 < len(blocks):
                    block.successors.append(i + 1)
        
        # 计算前驱
        for block in blocks:
            for succ_id in block.successors:
                if 0 <= succ_id < len(blocks):
                    blocks[succ_id].predecessors.append(block.id)
        
        # 识别分发器（控制流扁平化）
        for block in blocks:
            if len(block.predecessors) > 5 and len(block.successors) > 5:
                block.is_dispatcher = True
        
        return blocks
    
    def _extract_goto_target(self, instruction: str) -> Optional[int]:
        """提取跳转目标"""
        match = re.search(r':goto_(\d+)', instruction)
        if match:
            return int(match.group(1))
        return None
    
    def deobfuscate_class(self, smali_code: str) -> str:
        """反混淆单个类"""
        # 1. 恢复字符串
        strings = self.restore_strings(smali_code)
        for entry in strings:
            smali_code = smali_code.replace(entry.encrypted, f'"{entry.decrypted}"')
        
        # 2. 还原控制流
        blocks = self.restore_control_flow(smali_code)
        
        # 3. 简化反射调用
        smali_code = self._simplify_reflection(smali_code)
        
        # 4. 优化JNI调用
        smali_code = self._optimize_jni(smali_code)
        
        return smali_code
    
    def _simplify_reflection(self, smali_code: str) -> str:
        """简化反射调用"""
        # 将反射调用替换为直接调用（如果可能）
        # 例如: invoke-virtual {v0}, Ljava/lang/reflect/Method;->invoke -> invoke-virtual {v0}, Ltarget;->method
        
        # 简化实现：标记反射调用位置
        lines = smali_code.split('\n')
        simplified = []
        
        for line in lines:
            if 'Ljava/lang/reflect/Method;->invoke' in line:
                simplified.append(f"# [REFLECTION] {line}")
            else:
                simplified.append(line)
        
        return '\n'.join(simplified)
    
    def _optimize_jni(self, smali_code: str) -> str:
        """优化JNI调用"""
        # 标记JNI调用
        lines = smali_code.split('\n')
        optimized = []
        
        for line in lines:
            if 'invoke-static' in line and 'native' in line:
                optimized.append(f"# [JNI] {line}")
            else:
                optimized.append(line)
        
        return '\n'.join(optimized)
    
    def batch_deobfuscate(self, smali_dir: str, output_dir: str) -> DeobfuscationReport:
        """批量反混淆"""
        import os
        
        total_files = 0
        success_files = 0
        all_strings = []
        all_blocks = []
        deobfuscated_classes = []
        
        for root, dirs, files in os.walk(smali_dir):
            for file in files:
                if file.endswith('.smali'):
                    total_files += 1
                    
                    input_path = os.path.join(root, file)
                    relative_path = os.path.relpath(input_path, smali_dir)
                    output_path = os.path.join(output_dir, relative_path)
                    
                    try:
                        with open(input_path, 'r', encoding='utf-8') as f:
                            smali_code = f.read()
                        
                        # 反混淆
                        deobfuscated = self.deobfuscate_class(smali_code)
                        
                        # 保存
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write(deobfuscated)
                        
                        success_files += 1
                        deobfuscated_classes.append(relative_path)
                        
                        # 收集结果
                        all_strings.extend(self.restore_strings(smali_code))
                        all_blocks.extend(self.restore_control_flow(smali_code))
                        
                    except Exception as e:
                        print(f"❌ 反混淆失败 {relative_path}: {e}")
        
        success_rate = success_files / total_files if total_files > 0 else 0
        
        return DeobfuscationReport(
            apk_path=smali_dir,
            obfuscation_types=[],
            strings_recovered=all_strings,
            control_flow_restored=all_blocks,
            classes_deobfuscated=deobfuscated_classes,
            success_rate=success_rate
        )

# 便捷函数
def analyze_obfuscation(apk_path: str) -> List[ObfuscationType]:
    """快速分析混淆类型"""
    engine = DeobfuscationEngine()
    report = engine.analyze(apk_path)
    return report.obfuscation_types

def deobfuscate_smali(smali_code: str) -> str:
    """快速反混淆Smali代码"""
    engine = DeobfuscationEngine()
    return engine.deobfuscate_class(smali_code)
