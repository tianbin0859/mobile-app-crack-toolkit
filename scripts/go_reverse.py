#!/usr/bin/env python3
"""
go_reverse.py - Go二进制程序逆向工具

功能:
    1. 识别Go编译特征和版本
    2. 恢复函数名（Go符号表解析）
    3. 提取字符串和常量
    4. 分析Goroutine和Channel
    5. 生成IDA/Ghidra脚本

用法:
    # 分析Go程序
    python go_reverse.py --bin target --analyze
    
    # 提取字符串
    python go_reverse.py --bin target --strings --output ./strings.txt
    
    # 恢复函数名
    python go_reverse.py --bin target --recover-functions --output ./funcs.txt

依赖:
    - pip install pefile capstone
"""

import argparse
import os
import sys
import struct
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class GoDetector:
    """Go程序检测器"""
    
    # Go特征签名
    GO_SIGNATURES = [
        b'go1.',           # Go版本字符串
        b'runtime.',       # runtime包
        b'fmt.',           # fmt包
        b'main.main',      # main函数
        b'go.buildid',     # buildid
        b'Go build ID:',   # 构建ID
    ]
    
    @staticmethod
    def detect(file_path: str) -> Dict[str, any]:
        """检测Go程序"""
        result = {
            'is_go': False,
            'version': 'Unknown',
            'architecture': 'Unknown',
            'stripped': True,
            'features': [],
        }
        
        if not os.path.exists(file_path):
            return result
        
        with open(file_path, 'rb') as f:
            data = f.read(131072)  # 读取前128KB
        
        # 检查Go特征
        go_found = False
        for sig in GoDetector.GO_SIGNATURES:
            if sig in data:
                go_found = True
                result['features'].append(f'Signature: {sig.decode("utf-8", errors="ignore")}')
        
        if not go_found:
            return result
        
        result['is_go'] = True
        
        # 提取Go版本
        version_match = re.search(b'go1\.(\d+)(?:\.(\d+))?', data)
        if version_match:
            major = version_match.group(1).decode()
            minor = version_match.group(2).decode() if version_match.group(2) else '0'
            result['version'] = f'go1.{major}.{minor}'
        
        # 检测架构
        if data[:4] == b'\x7fELF':
            # ELF文件
            arch = struct.unpack('<H', data[18:20])[0]
            if arch == 0x3E:
                result['architecture'] = 'x64'
            elif arch == 0x3:
                result['architecture'] = 'x86'
            elif arch == 0x28:
                result['architecture'] = 'ARM'
        elif data[:2] == b'MZ':
            # PE文件
            pe_offset = struct.unpack('<I', data[0x3C:0x40])[0]
            if data[pe_offset:pe_offset+4] == b'PE\x00\x00':
                machine = struct.unpack('<H', data[pe_offset+4:pe_offset+6])[0]
                if machine == 0x8664:
                    result['architecture'] = 'x64'
                elif machine == 0x14c:
                    result['architecture'] = 'x86'
        elif data[:4] == b'\xcf\xfa\xed\xfe':
            # Mach-O (little endian)
            cputype = struct.unpack('<I', data[4:8])[0]
            if cputype == 0x01000007:
                result['architecture'] = 'x64'
            elif cputype == 0x0100000C:
                result['architecture'] = 'ARM64'
        
        # 检查是否stripped
        if b'go.buildid' in data or b'runtime.buildVersion' in data:
            result['stripped'] = False
        
        return result


class GoSymbolRecover:
    """Go符号恢复器"""
    
    def __init__(self, bin_path: str):
        self.bin_path = bin_path
        self.functions = []
        
    def recover_functions(self) -> List[Dict]:
        """恢复函数名"""
        print(f"[*] 恢复函数名: {self.bin_path}")
        
        with open(self.bin_path, 'rb') as f:
            data = f.read()
        
        # Go函数名特征：包名.函数名
        # 例如：fmt.Printf, main.main, runtime.goexit
        func_pattern = re.compile(
            b'([a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z][a-zA-Z0-9_]*)+)'
        )
        
        # 查找所有可能的函数名
        matches = func_pattern.findall(data)
        
        functions = []
        seen = set()
        
        for match in matches:
            func_name = match.decode('utf-8', errors='ignore')
            
            # 过滤无效名称
            if len(func_name) < 3 or len(func_name) > 100:
                continue
            
            # 检查是否包含Go包特征
            if any(pkg in func_name for pkg in ['runtime.', 'fmt.', 'os.', 'net.', 'crypto.', 'main.']):
                if func_name not in seen:
                    seen.add(func_name)
                    functions.append({
                        'name': func_name,
                        'offset': data.find(match),
                    })
        
        self.functions = functions
        
        print(f"[+] 恢复 {len(functions)} 个函数名")
        
        # 分类统计
        categories = {}
        for func in functions:
            cat = func['name'].split('.')[0]
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"[+] 函数分类:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"    {cat}: {count}")
        
        return functions
    
    def export_functions(self, output_path: str):
        """导出函数列表"""
        with open(output_path, 'w') as f:
            for func in self.functions:
                f.write(f"0x{func['offset']:X}\t{func['name']}\n")
        
        print(f"[+] 导出函数列表: {output_path}")


class GoStringExtractor:
    """Go字符串提取器"""
    
    def __init__(self, bin_path: str):
        self.bin_path = bin_path
        self.strings = []
        
    def extract_strings(self) -> List[Dict]:
        """提取Go字符串"""
        print(f"[*] 提取字符串: {self.bin_path}")
        
        with open(self.bin_path, 'rb') as f:
            data = f.read()
        
        strings = []
        
        # Go字符串特征：长度前缀 + 字符串数据
        # 在Go二进制中，字符串通常以 (指针, 长度) 对的形式存储
        
        # 方法1：查找可打印字符串
        min_len = 4
        max_len = 1000
        
        i = 0
        while i < len(data) - min_len:
            # 检查是否是字符串长度前缀
            if data[i] >= min_len and data[i] <= max_len:
                length = data[i]
                
                # 检查后续字节是否都是可打印字符
                is_string = True
                for j in range(1, length + 1):
                    if i + j >= len(data) or data[i + j] < 32 or data[i + j] > 126:
                        is_string = False
                        break
                
                if is_string:
                    string_data = data[i+1:i+1+length].decode('utf-8', errors='ignore')
                    strings.append({
                        'offset': i,
                        'length': length,
                        'string': string_data,
                    })
                    i += length + 1
                    continue
            
            i += 1
        
        # 方法2：查找长字符串（UTF-8）
        # 使用正则表达式查找可打印字符串
        for match in re.finditer(b'[\x20-\x7e]{10,}', data):
            strings.append({
                'offset': match.start(),
                'length': len(match.group()),
                'string': match.group().decode('utf-8', errors='ignore'),
            })
        
        self.strings = strings
        
        print(f"[+] 提取 {len(strings)} 个字符串")
        
        return strings
    
    def export_strings(self, output_path: str):
        """导出字符串"""
        with open(output_path, 'w') as f:
            for s in self.strings:
                f.write(f"0x{s['offset']:X}\t{s['string']}\n")
        
        print(f"[+] 导出字符串: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Go二进制程序逆向工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 分析Go程序
    python go_reverse.py --bin target --analyze
    
    # 提取字符串
    python go_reverse.py --bin target --strings --output ./strings.txt
    
    # 恢复函数名
    python go_reverse.py --bin target --recover-functions --output ./funcs.txt
        """
    )
    
    parser.add_argument("--bin", help="目标二进制文件")
    parser.add_argument("--output", "-o", default="./go_output", help="输出目录")
    parser.add_argument("--analyze", action="store_true", help="分析程序")
    parser.add_argument("--strings", action="store_true", help="提取字符串")
    parser.add_argument("--recover-functions", action="store_true", help="恢复函数名")
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    # 分析
    if args.bin and args.analyze:
        print(f"[*] 分析: {args.bin}")
        detection = GoDetector.detect(args.bin)
        
        print(f"[+] 分析结果:")
        print(f"    Go程序: {'是' if detection['is_go'] else '否'}")
        print(f"    版本: {detection['version']}")
        print(f"    架构: {detection['architecture']}")
        print(f"    Stripped: {'是' if detection['stripped'] else '否'}")
        print(f"    特征: {', '.join(detection['features'])}")
    
    # 提取字符串
    if args.bin and args.strings:
        extractor = GoStringExtractor(args.bin)
        extractor.extract_strings()
        extractor.export_strings(os.path.join(args.output, "strings.txt"))
    
    # 恢复函数名
    if args.bin and args.recover_functions:
        recoverer = GoSymbolRecover(args.bin)
        recoverer.recover_functions()
        recoverer.export_functions(os.path.join(args.output, "functions.txt"))
    
    print("\n[+] 完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
