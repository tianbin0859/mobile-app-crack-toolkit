#!/usr/bin/env python3
"""
rust_analyzer.py - Rust二进制专项分析工具
基于黑曼巴6.16实战经验开发

功能:
    1. 识别Rust编译特征（混淆区段、.rdata字符串、Rust符号）
    2. 提取Rust字符串和错误信息（用于定位认证逻辑）
    3. 分析枚举跳转表（Rust match/switch 模式）
    4. 定位认证相关代码（通过字符串交叉引用）
    5. 生成IDA/Ghidra脚本辅助分析

用法:
    # 分析Rust二进制
    python rust_analyzer.py --exe game.exe --analyze
    
    # 提取字符串并搜索认证相关
    python rust_analyzer.py --exe game.exe --extract-strings --search-auth
    
    # 生成IDA脚本
    python rust_analyzer.py --exe game.exe --generate-ida-script --output ./ida_script.py

依赖:
    - pip install pefile
"""

import argparse
import os
import sys
import struct
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from collections import Counter

class RustDetector:
    """Rust编译特征检测器"""
    
    # Rust特征字符串
    RUST_SIGNATURES = [
        b'rust_begin_unwind',
        b'RUST_BACKTRACE',
        b'__rust_',
        b'rustc',
        b'cargo',
        b'libstd-',
        b'libcore-',
        b'liballoc-',
    ]
    
    # Rust混淆区段命名模式
    OBFUSCATED_SECTION_PATTERNS = [
        re.compile(r'^[a-zA-Z0-9]{4,6}$'),  # 短随机字符串
        re.compile(r'^[a-zA-Z0-9+/]{2,4}[a-zA-Z0-9+/]{2,}$'),  # base64-like
    ]
    
    @staticmethod
    def detect_pe(file_path: str) -> Dict[str, any]:
        """检测PE文件是否为Rust编译"""
        result = {
            'is_rust': False,
            'confidence': 0.0,
            'features': [],
            'sections': [],
            'strings': [],
        }
        
        try:
            import pefile
        except ImportError:
            print("[-] 需要pefile库: pip install pefile")
            return result
        
        try:
            pe = pefile.PE(file_path)
        except Exception as e:
            print(f"[-] PE解析失败: {e}")
            return result
        
        # 检查区段特征
        sections = []
        obfuscated_count = 0
        for section in pe.sections:
            name = section.Name.decode('utf-8', errors='ignore').strip('\x00')
            sections.append({
                'name': name,
                'virtual_address': hex(section.VirtualAddress),
                'virtual_size': section.Misc_VirtualSize,
                'raw_size': section.SizeOfRawData,
            })
            
            # 检查混淆命名
            if name not in ['.text', '.data', '.rdata', '.bss', '.idata', '.edata', '.reloc', '.rsrc']:
                if len(name) >= 4 and len(name) <= 8:
                    obfuscated_count += 1
        
        result['sections'] = sections
        
        if obfuscated_count >= 3:
            result['features'].append(f'混淆区段: {obfuscated_count}个')
            result['confidence'] += 0.3
        
        # 检查导入表
        if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
            result['features'].append(f'导入DLL: {len(pe.DIRECTORY_ENTRY_IMPORT)}个')
        else:
            result['features'].append('无静态导入表（动态解析）')
            result['confidence'] += 0.2  # Rust常见特征
        
        # 检查字符串
        with open(file_path, 'rb') as f:
            data = f.read()
        
        rust_strings = []
        for sig in RustDetector.RUST_SIGNATURES:
            if sig in data:
                rust_strings.append(sig.decode('utf-8', errors='ignore'))
        
        if rust_strings:
            result['features'].append(f'Rust字符串: {len(rust_strings)}个')
            result['strings'] = rust_strings
            result['confidence'] += 0.3
        
        # 检查panic信息
        panic_count = data.count(b'panic')
        if panic_count > 10:
            result['features'].append(f'Panic信息: {panic_count}处')
            result['confidence'] += 0.1
        
        # 检查.rdata大小
        rdata_section = None
        for section in sections:
            if section['name'] == '.rdata':
                rdata_section = section
                break
        
        if rdata_section and rdata_section['virtual_size'] > 10 * 1024 * 1024:
            result['features'].append(f'.rdata区段: {rdata_section["virtual_size"] / 1024 / 1024:.1f}MB')
            result['confidence'] += 0.1
        
        # 最终判断
        if result['confidence'] >= 0.5:
            result['is_rust'] = True
        
        return result


class StringExtractor:
    """字符串提取器"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.strings = []
        
    def extract_all(self, min_length: int = 4) -> List[Dict]:
        """提取所有可打印字符串"""
        print(f"[*] 提取字符串: {self.file_path}")
        
        with open(self.file_path, 'rb') as f:
            data = f.read()
        
        strings = []
        
        # 提取ASCII字符串
        for match in re.finditer(b'[\x20-\x7e]{' + str(min_length).encode() + b',}', data):
            s = match.group().decode('utf-8', errors='ignore')
            strings.append({
                'string': s,
                'offset': match.start(),
                'type': 'ascii',
            })
        
        # 提取Unicode字符串
        for match in re.finditer(b'(?:[\x20-\x7e]\x00){' + str(min_length).encode() + b',}', data):
            s = match.group().decode('utf-16-le', errors='ignore')
            strings.append({
                'string': s,
                'offset': match.start(),
                'type': 'unicode',
            })
        
        self.strings = strings
        
        print(f"[+] 提取 {len(strings)} 个字符串")
        
        return strings
    
    def search_auth_related(self) -> List[Dict]:
        """搜索认证相关字符串"""
        if not self.strings:
            self.extract_all()
        
        auth_keywords = [
            'auth', 'login', 'license', 'verify', 'check',
            'valid', 'invalid', 'error', 'fail', 'success',
            'token', 'key', 'password', 'credential',
            '卡密', '授权', '登录', '验证',
        ]
        
        auth_strings = []
        for s in self.strings:
            text = s['string'].lower()
            for keyword in auth_keywords:
                if keyword in text:
                    auth_strings.append(s)
                    break
        
        print(f"[+] 发现 {len(auth_strings)} 个认证相关字符串")
        
        return auth_strings
    
    def export(self, output_path: str, filter_auth: bool = False):
        """导出字符串列表"""
        strings = self.search_auth_related() if filter_auth else self.strings
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for s in strings:
                f.write(f"0x{s['offset']:08X}\t{s['type']}\t{s['string']}\n")
        
        print(f"[+] 导出字符串: {output_path}")


class JumpTableAnalyzer:
    """枚举跳转表分析器（Rust match/switch）"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        
    def analyze(self, enum_strings: List[str]) -> List[Dict]:
        """分析枚举跳转表"""
        print(f"[*] 分析枚举跳转表: {self.file_path}")
        
        with open(self.file_path, 'rb') as f:
            data = f.read()
        
        results = []
        
        # 查找枚举字符串（错误码、状态等）
        for enum_str in enum_strings:
            # 查找字符串位置
            str_bytes = enum_str.encode('utf-8')
            pos = data.find(str_bytes)
            
            if pos == -1:
                continue
            
            # 查找引用该字符串的代码（简化：查找附近地址）
            # 实际应该解析重定位表
            results.append({
                'enum': enum_str,
                'string_offset': pos,
                'type': 'enum_string',
            })
        
        print(f"[+] 发现 {len(results)} 个枚举字符串")
        
        return results


class IDAScriptGenerator:
    """IDA脚本生成器"""
    
    @staticmethod
    def generate_rust_analysis_script(file_path: str, output_path: str, auth_offsets: List[int]):
        """生成IDA分析脚本"""
        script = f'''# IDA Python脚本 - Rust二进制分析
# 生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 目标文件: {file_path}

import idaapi
import idautils
import idc

# 1. 标记认证相关偏移
auth_offsets = {auth_offsets}

for offset in auth_offsets:
    ea = idc.get_segm_base(idaapi.get_segm_by_name(".text")) + offset
    idc.set_cmt(ea, "AUTH_RELATED", 1)
    print(f"[+] 标记认证偏移: 0x{{offset:08X}}")

# 2. 查找字符串引用
def find_string_refs(string):
    for addr in idautils.Strings():
        if string in str(addr):
            for ref in idautils.DataRefsTo(addr.ea):
                print(f"[+] 字符串引用: {{string}} @ 0x{{ref:08X}}")

# 3. 分析枚举跳转表
def analyze_enum_jumptable(enum_addr):
    """分析枚举跳转表"""
    # 查找引用该枚举的代码
    for ref in idautils.DataRefsTo(enum_addr):
        print(f"[+] 枚举引用: 0x{{ref:08X}}")
        # 尝试反汇编周围代码
        for i in range(-50, 50):
            ea = ref + i
            if idc.is_code(idc.get_full_flags(ea)):
                print(f"    0x{{ea:08X}}: {{idc.generate_disasm_line(ea)}}")

# 4. 主函数
def main():
    print("[*] Rust二进制分析脚本启动")
    
    # 标记认证偏移
    for offset in auth_offsets:
        ea = idc.get_segm_base(idaapi.get_segm_by_name(".text")) + offset
        idc.set_cmt(ea, "AUTH_RELATED", 1)
    
    print("[+] 分析完成")

if __name__ == "__main__":
    main()
'''
        
        with open(output_path, 'w') as f:
            f.write(script)
        
        print(f"[+] 生成IDA脚本: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Rust二进制专项分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 分析Rust二进制
    python rust_analyzer.py --exe game.exe --analyze
    
    # 提取字符串并搜索认证相关
    python rust_analyzer.py --exe game.exe --extract-strings --search-auth
    
    # 生成IDA脚本
    python rust_analyzer.py --exe game.exe --generate-ida-script --output ./ida_script.py
        """
    )
    
    parser.add_argument("--exe", required=True, help="目标PE文件")
    parser.add_argument("--output", "-o", default="./rust_output", help="输出目录")
    parser.add_argument("--analyze", action="store_true", help="分析Rust特征")
    parser.add_argument("--extract-strings", action="store_true", help="提取字符串")
    parser.add_argument("--search-auth", action="store_true", help="搜索认证相关字符串")
    parser.add_argument("--generate-ida-script", action="store_true", help="生成IDA脚本")
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    # 分析Rust特征
    if args.analyze:
        print(f"[*] 分析: {args.exe}")
        detection = RustDetector.detect_pe(args.exe)
        
        print(f"[+] 分析结果:")
        print(f"    Rust程序: {'是' if detection['is_rust'] else '否'}")
        print(f"    置信度: {detection['confidence']:.0%}")
        print(f"    特征: {', '.join(detection['features'])}")
        
        if detection['sections']:
            print(f"    区段:")
            for section in detection['sections']:
                print(f"      {section['name']}: VA={section['virtual_address']}, Size={section['virtual_size']}")
    
    # 提取字符串
    if args.extract_strings:
        extractor = StringExtractor(args.exe)
        extractor.extract_all()
        
        if args.search_auth:
            auth_strings = extractor.search_auth_related()
            print(f"\n[+] 认证相关字符串:")
            for s in auth_strings[:20]:
                print(f"    0x{s['offset']:08X}: {s['string']}")
        
        extractor.export(os.path.join(args.output, "strings.txt"), filter_auth=args.search_auth)
    
    # 生成IDA脚本
    if args.generate_ida_script:
        # 提取认证相关偏移
        extractor = StringExtractor(args.exe)
        auth_strings = extractor.search_auth_related()
        auth_offsets = [s['offset'] for s in auth_strings[:10]]
        
        output_path = os.path.join(args.output, "ida_rust_analysis.py")
        IDAScriptGenerator.generate_rust_analysis_script(args.exe, output_path, auth_offsets)
    
    print("\n[+] 完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
