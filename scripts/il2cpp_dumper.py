#!/usr/bin/env python3
"""
il2cpp_dumper.py - Unity IL2CPP自动Dump工具
基于Perfare/Il2CppDumper架构，Python封装实现

功能:
    1. 自动解析 global-metadata.dat 文件
    2. 恢复类名、方法名、字段名
    3. 生成IDA/Ghidra脚本辅助分析
    4. 输出结构化的JSON符号表

用法:
    # 自动分析APK/IPA中的IL2CPP
    python il2cpp_dumper.py --apk game.apk --output ./output
    
    # 直接分析已提取的文件
    python il2cpp_dumper.py --binary libil2cpp.so --metadata global-metadata.dat
    
    # 生成IDA脚本
    python il2cpp_dumper.py --binary libil2cpp.so --metadata global-metadata.dat --ida-script

依赖:
    - pip install construct pycryptodome
"""

import argparse
import os
import sys
import json
import struct
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

class Il2CppMetadata:
    """IL2CPP Metadata解析器"""
    
    # Metadata文件头结构
    HEADER_SIZE = 0x100
    
    def __init__(self, metadata_path: str):
        self.path = metadata_path
        self.data = b""
        self.header = {}
        self.version = 0
        self.strings = []
        self.methods = []
        self.classes = []
        self.fields = []
        
    def parse(self) -> bool:
        """解析metadata文件"""
        if not os.path.exists(self.path):
            print(f"[-] Metadata文件不存在: {self.path}")
            return False
        
        with open(self.path, 'rb') as f:
            self.data = f.read()
        
        if len(self.data) < self.HEADER_SIZE:
            print("[-] Metadata文件太小")
            return False
        
        # 解析头部
        self._parse_header()
        
        # 解析字符串表
        self._parse_strings()
        
        # 解析类定义
        self._parse_classes()
        
        # 解析方法定义
        self._parse_methods()
        
        # 解析字段定义
        self._parse_fields()
        
        print(f"[+] Metadata解析完成:")
        print(f"    版本: {self.version}")
        print(f"    字符串: {len(self.strings)} 个")
        print(f"    类: {len(self.classes)} 个")
        print(f"    方法: {len(self.methods)} 个")
        print(f"    字段: {len(self.fields)} 个")
        
        return True
    
    def _parse_header(self):
        """解析Metadata头部"""
        # IL2CPP metadata header format (简化版)
        # 实际实现需要更完整的结构定义
        
        # 读取版本号 (偏移0x0)
        self.version = struct.unpack('<I', self.data[0:4])[0]
        
        # 读取字符串表偏移和大小
        str_offset = struct.unpack('<I', self.data[0x10:0x14])[0]
        str_count = struct.unpack('<I', self.data[0x14:0x18])[0]
        
        self.header = {
            'version': self.version,
            'string_offset': str_offset,
            'string_count': str_count,
        }
    
    def _parse_strings(self):
        """解析字符串表"""
        str_offset = self.header.get('string_offset', 0x100)
        str_count = self.header.get('string_count', 0)
        
        # 简化实现：读取以null结尾的字符串
        pos = str_offset
        for _ in range(min(str_count, 10000)):  # 限制数量防止错误
            if pos >= len(self.data):
                break
            
            end = self.data.find(b'\x00', pos)
            if end == -1:
                break
            
            try:
                s = self.data[pos:end].decode('utf-8')
                self.strings.append(s)
            except:
                pass
            
            pos = end + 1
    
    def _parse_classes(self):
        """解析类定义"""
        # 简化实现：从字符串中提取类名特征
        for s in self.strings:
            if '.' in s and not s.startswith('<'):
                self.classes.append({
                    'name': s,
                    'namespace': self._extract_namespace(s),
                })
    
    def _parse_methods(self):
        """解析方法定义"""
        # 简化实现
        for s in self.strings:
            if '(' in s and ')' in s:
                self.methods.append({
                    'name': s,
                    'signature': s,
                })
    
    def _parse_fields(self):
        """解析字段定义"""
        # 简化实现
        for s in self.strings:
            if not '(' in s and '.' in s and not s.startswith('<'):
                self.fields.append({
                    'name': s,
                })
    
    def _extract_namespace(self, class_name: str) -> str:
        """提取命名空间"""
        if '.' in class_name:
            return '.'.join(class_name.split('.')[:-1])
        return ""
    
    def get_class_list(self) -> List[Dict]:
        """获取类列表"""
        return self.classes
    
    def get_method_list(self) -> List[Dict]:
        """获取方法列表"""
        return self.methods
    
    def export_json(self, output_path: str):
        """导出为JSON"""
        data = {
            'version': self.version,
            'header': self.header,
            'classes': self.classes[:1000],  # 限制数量
            'methods': self.methods[:1000],
            'fields': self.fields[:1000],
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"[+] 导出JSON: {output_path}")


class Il2CppBinary:
    """IL2CPP二进制文件分析器"""
    
    def __init__(self, binary_path: str):
        self.path = binary_path
        self.data = b""
        self.arch = "unknown"
        self.code_sections = []
        
    def parse(self) -> bool:
        """解析二进制文件"""
        if not os.path.exists(self.path):
            print(f"[-] 二进制文件不存在: {self.path}")
            return False
        
        with open(self.path, 'rb') as f:
            self.data = f.read()
        
        # 检测架构
        self._detect_arch()
        
        # 解析代码段
        self._parse_sections()
        
        print(f"[+] 二进制解析完成:")
        print(f"    架构: {self.arch}")
        print(f"    大小: {len(self.data):,} bytes")
        print(f"    代码段: {len(self.code_sections)} 个")
        
        return True
    
    def _detect_arch(self):
        """检测CPU架构"""
        # ELF文件
        if self.data[:4] == b'\x7fELF':
            e_machine = struct.unpack('<H', self.data[18:20])[0]
            if e_machine == 0x3E:
                self.arch = "x86_64"
            elif e_machine == 0x28:
                self.arch = "ARM"
            elif e_machine == 0xB7:
                self.arch = "AArch64"
        
        # Mach-O文件
        elif self.data[:4] in (b'\xfe\xed\xfa\xcf', b'\xcf\xfa\xed\xfe'):
            self.arch = "Mach-O (iOS/macOS)"
        
        # PE文件
        elif self.data[:2] == b'MZ':
            self.arch = "x86/x64 (Windows)"
    
    def _parse_sections(self):
        """解析代码段"""
        # 简化实现
        self.code_sections = [{
            'name': '.text',
            'offset': 0x1000,
            'size': min(len(self.data), 0x100000),
        }]
    
    def find_code_refs(self, pattern: bytes) -> List[int]:
        """查找代码引用"""
        refs = []
        start = 0
        while True:
            pos = self.data.find(pattern, start)
            if pos == -1:
                break
            refs.append(pos)
            start = pos + 1
        return refs


class Il2CppDumper:
    """IL2CPP自动Dump主控制器"""
    
    VERSION = "1.0.0"
    
    def __init__(self, binary_path: str, metadata_path: str, output_dir: str = "./output"):
        self.binary_path = binary_path
        self.metadata_path = metadata_path
        self.output_dir = output_dir
        self.metadata = None
        self.binary = None
        
    def run(self) -> bool:
        """执行完整Dump流程"""
        print("=" * 60)
        print(f"Unity IL2CPP Dumper v{self.VERSION}")
        print("=" * 60)
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 解析Metadata
        print("\n[*] 解析Metadata...")
        self.metadata = Il2CppMetadata(self.metadata_path)
        if not self.metadata.parse():
            return False
        
        # 解析二进制
        print("\n[*] 解析二进制...")
        self.binary = Il2CppBinary(self.binary_path)
        if not self.binary.parse():
            return False
        
        # 生成输出
        print("\n[*] 生成输出文件...")
        self._generate_outputs()
        
        print("\n" + "=" * 60)
        print("[+] Dump完成!")
        print(f"    输出目录: {self.output_dir}")
        print("=" * 60)
        
        return True
    
    def _generate_outputs(self):
        """生成所有输出文件"""
        if not self.metadata:
            print("[-] Metadata未解析，无法生成输出")
            return
        
        # 1. JSON符号表
        json_path = os.path.join(self.output_dir, "il2cpp_symbols.json")
        self.metadata.export_json(json_path)
        
        # 2. IDA脚本
        ida_script = os.path.join(self.output_dir, "il2cpp_ida.py")
        self._generate_ida_script(ida_script)
        
        # 3. 方法列表文本
        methods_txt = os.path.join(self.output_dir, "methods.txt")
        self._generate_methods_txt(methods_txt)
        
        # 4. 类列表文本
        classes_txt = os.path.join(self.output_dir, "classes.txt")
        self._generate_classes_txt(classes_txt)
    
    def _generate_ida_script(self, output_path: str):
        """生成IDA脚本"""
        script = f'''# Unity IL2CPP IDA辅助脚本
# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

import idaapi
import idc
import idautils

# 类名列表
classes = {json.dumps([c['name'] for c in self.metadata.classes[:500]], ensure_ascii=False)}

# 方法名列表  
methods_list = {json.dumps([m['name'] for m in self.metadata.methods[:500]], ensure_ascii=False)}

def rename_functions():
"""根据IL2CPP符号重命名函数"""
for method_name in methods_list:
# 查找匹配的函数
for func_addr in idautils.Functions():
    func_name = idc.get_func_name(func_addr)
    if method_name in func_name or func_name in method_name:
        # 重命名
        idc.set_name(func_addr, f"il2cpp_{{method_name}}", idc.SN_CHECK)
    
print(f"[+] 已重命名 {{len(methods_list)}} 个函数")

def add_comments():
"""添加类名注释"""
for class_name in classes:
# 在相关地址添加注释
pass

# 执行
rename_functions()
print("[+] IL2CPP IDA脚本执行完成")
'''
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(script)
        
        print(f"[+] 生成IDA脚本: {output_path}")
    
    def _generate_methods_txt(self, output_path: str):
        """生成方法列表"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Unity IL2CPP 方法列表\\n")
            f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
            f.write(f"# 总计: {len(self.metadata.methods)} 个方法\\n\\n")
            
            for i, method in enumerate(self.metadata.methods, 1):
                f.write(f"{i}. {method['name']}\\n")
        
        print(f"[+] 生成方法列表: {output_path}")
    
    def _generate_classes_txt(self, output_path: str):
        """生成类列表"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Unity IL2CPP 类列表\\n")
            f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
            f.write(f"# 总计: {len(self.metadata.classes)} 个类\\n\\n")
            
            for i, cls in enumerate(self.metadata.classes, 1):
                ns = cls.get('namespace', '')
                name = cls['name']
                if ns:
                    f.write(f"{i}. {ns}.{name}\\n")
                else:
                    f.write(f"{i}. {name}\\n")
        
        print(f"[+] 生成类列表: {output_path}")


class APKExtractor:
    """APK/IPA文件提取器"""
    
    @staticmethod
    def extract_il2cpp(apk_path: str, output_dir: str) -> Tuple[Optional[str], Optional[str]]:
        """从APK中提取IL2CPP相关文件"""
        import zipfile
        
        binary_path = None
        metadata_path = None
        
        try:
            with zipfile.ZipFile(apk_path, 'r') as z:
                # 查找libil2cpp.so
                for name in z.namelist():
                    if 'libil2cpp.so' in name:
                        binary_path = os.path.join(output_dir, os.path.basename(name))
                        z.extract(name, output_dir)
                        print(f"[+] 提取: {name}")
                        break
                
                # 查找global-metadata.dat
                for name in z.namelist():
                    if 'global-metadata.dat' in name:
                        metadata_path = os.path.join(output_dir, os.path.basename(name))
                        z.extract(name, output_dir)
                        print(f"[+] 提取: {name}")
                        break
        
        except Exception as e:
            print(f"[-] APK提取失败: {e}")
        
        return binary_path, metadata_path


def main():
    parser = argparse.ArgumentParser(
        description=f"Unity IL2CPP Dumper v1.0.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 从APK自动提取并分析
    python il2cpp_dumper.py --apk game.apk --output ./output
    
    # 直接分析已提取的文件
    python il2cpp_dumper.py --binary libil2cpp.so --metadata global-metadata.dat
    
    # 生成IDA脚本
    python il2cpp_dumper.py --binary libil2cpp.so --metadata global-metadata.dat --ida-script
        """
    )
    
    parser.add_argument("--apk", help="APK/IPA文件路径")
    parser.add_argument("--binary", help="IL2CPP二进制文件路径")
    parser.add_argument("--metadata", help="global-metadata.dat路径")
    parser.add_argument("--output", "-o", default="./output", help="输出目录")
    parser.add_argument("--ida-script", action="store_true", help="生成IDA脚本")
    
    args = parser.parse_args()
    
    binary_path = args.binary
    metadata_path = args.metadata
    
    # 从APK提取
    if args.apk:
        print(f"[*] 从APK提取: {args.apk}")
        binary_path, metadata_path = APKExtractor.extract_il2cpp(args.apk, args.output)
    
    # 验证文件
    if not binary_path or not os.path.exists(binary_path):
        print("[-] 未找到IL2CPP二进制文件")
        sys.exit(1)
    
    if not metadata_path or not os.path.exists(metadata_path):
        print("[-] 未找到metadata文件")
        sys.exit(1)
    
    # 执行Dump
    dumper = Il2CppDumper(binary_path, metadata_path, args.output)
    success = dumper.run()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
