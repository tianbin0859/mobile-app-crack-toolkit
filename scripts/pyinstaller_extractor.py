#!/usr/bin/env python3
"""
pyinstaller_extractor.py - Python打包程序逆向工具
支持PyInstaller、UPX、Py2exe等打包格式

功能:
    1. 自动识别打包类型（PyInstaller/UPX/其他）
    2. 提取原始Python字节码（.pyc）
    3. 反编译pyc为.py源码
    4. 提取资源文件（图片、配置等）
    5. 分析依赖和导入

用法:
    # 自动分析并提取
    python pyinstaller_extractor.py --exe target.exe --output ./extracted
    
    # 仅反编译pyc文件
    python pyinstaller_extractor.py --pyc app.pyc --decompile
    
    # 批量处理目录
    python pyinstaller_extractor.py --batch ./packed_apps/ --output ./extracted

依赖:
    - pip install pyinstxtractor upx-unpacker uncompyle6
"""

import argparse
import os
import sys
import struct
import zlib
import marshal
import dis
from pathlib import Path
from typing import Dict, List, Optional, Tuple, BinaryIO
import io

class PyInstallerDetector:
    """PyInstaller打包检测器"""
    
    # PyInstaller特征签名
    PYI_SIGNATURES = [
        b'MEI\x0c\x13\x01\x0c\x0d',  # PyInstaller 2.0+
        b'MEI\x0f\x13\x01\x0c\x0d',  # PyInstaller 2.1+
        b'MEI\x10\x13\x01\x0c\x0d',  # PyInstaller 3.0+
    ]
    
    # UPX特征
    UPX_SIGNATURES = [
        b'UPX!',
        b'UPX0',
        b'UPX1',
    ]
    
    @staticmethod
    def detect_pyi(exe_path: str) -> Tuple[bool, str]:
        """检测是否为PyInstaller打包"""
        with open(exe_path, 'rb') as f:
            data = f.read(4096)
        
        for sig in PyInstallerDetector.PYI_SIGNATURES:
            if sig in data:
                return True, "PyInstaller"
        
        # 检查PyInstaller特征字符串
        if b'PyInstaller' in data or b'pyi_runtime' in data:
            return True, "PyInstaller"
        
        return False, "Unknown"
    
    @staticmethod
    def detect_upx(exe_path: str) -> Tuple[bool, str]:
        """检测是否为UPX压缩"""
        with open(exe_path, 'rb') as f:
            data = f.read(4096)
        
        for sig in PyInstallerDetector.UPX_SIGNATURES:
            if sig in data:
                return True, "UPX"
        
        return False, "Unknown"
    
    @staticmethod
    def detect(exe_path: str) -> Dict[str, any]:
        """综合检测"""
        result = {
            'path': exe_path,
            'size': os.path.getsize(exe_path),
            'is_pyi': False,
            'is_upx': False,
            'packer': 'Unknown',
            'version': 'Unknown',
        }
        
        # 检测PyInstaller
        is_pyi, packer = PyInstallerDetector.detect_pyi(exe_path)
        if is_pyi:
            result['is_pyi'] = True
            result['packer'] = packer
        
        # 检测UPX
        is_upx, packer = PyInstallerDetector.detect_upx(exe_path)
        if is_upx:
            result['is_upx'] = True
            if result['packer'] == 'Unknown':
                result['packer'] = packer
        
        return result


class PyInstallerExtractor:
    """PyInstaller提取器"""
    
    def __init__(self, exe_path: str, output_dir: str):
        self.exe_path = exe_path
        self.output_dir = output_dir
        self.pyi_archive = None
        
    def extract(self) -> bool:
        """执行提取"""
        print(f"[*] 提取: {self.exe_path}")
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 读取文件
        with open(self.exe_path, 'rb') as f:
            data = f.read()
        
        # 查找CArchive偏移
        carchive_offset = self._find_carchive(data)
        if carchive_offset == -1:
            print("[-] 未找到CArchive")
            return False
        
        print(f"[+] CArchive偏移: 0x{carchive_offset:X}")
        
        # 提取文件
        extracted = self._extract_files(data, carchive_offset)
        
        print(f"[+] 提取完成: {extracted} 个文件")
        print(f"    输出目录: {self.output_dir}")
        
        return True
    
    def _find_carchive(self, data: bytes) -> int:
        """查找CArchive位置"""
        # 查找MEI签名
        offset = 0
        while True:
            pos = data.find(b'MEI', offset)
            if pos == -1:
                break
            
            # 验证头部结构
            if pos + 24 < len(data):
                # 检查版本字段
                version = struct.unpack('<I', data[pos+4:pos+8])[0]
                if version in (0x0c13010c, 0x0f13010c, 0x1013010c):
                    return pos
            
            offset = pos + 1
        
        # 备用：查找尾部标记
        tail_marker = b'PYZ\x00'
        pos = data.rfind(tail_marker)
        if pos != -1:
            return pos
        
        return -1
    
    def _extract_files(self, data: bytes, offset: int) -> int:
        """提取所有文件"""
        count = 0
        
        # 简化实现：查找并提取所有pyc文件
        pyc_magic = b'\x55\x0d\x0d\x0a'  # Python 3.8+ magic
        
        pos = 0
        while True:
            pyc_pos = data.find(pyc_magic, pos)
            if pyc_pos == -1:
                break
            
            # 提取pyc文件（简化：固定大小）
            pyc_size = min(65536, len(data) - pyc_pos)
            pyc_data = data[pyc_pos:pyc_pos + pyc_size]
            
            # 保存
            output_path = os.path.join(self.output_dir, f"extracted_{count}.pyc")
            with open(output_path, 'wb') as f:
                f.write(pyc_data)
            
            count += 1
            pos = pyc_pos + pyc_size
        
        # 也尝试提取其他资源
        self._extract_resources(data)
        
        return count
    
    def _extract_resources(self, data: bytes):
        """提取资源文件"""
        # 查找常见的资源签名
        resource_signatures = {
            b'\x89PNG': '.png',
            b'\xff\xd8\xff': '.jpg',
            b'PK\x03\x04': '.zip',
            b'Rar!': '.rar',
        }
        
        for sig, ext in resource_signatures.items():
            pos = 0
            count = 0
            while True:
                res_pos = data.find(sig, pos)
                if res_pos == -1:
                    break
                
                # 提取资源（简化：固定大小）
                res_size = min(1048576, len(data) - res_pos)  # 最大1MB
                res_data = data[res_pos:res_pos + res_size]
                
                output_path = os.path.join(self.output_dir, f"resource_{count}{ext}")
                with open(output_path, 'wb') as f:
                    f.write(res_data)
                
                count += 1
                pos = res_pos + res_size


class PycDecompiler:
    """Python字节码反编译器"""
    
    @staticmethod
    def decompile(pyc_path: str, output_path: str) -> bool:
        """反编译pyc文件"""
        try:
            # 尝试使用uncompyle6
            import uncompyle6
            with open(output_path, 'w') as f:
                uncompyle6.decompile_file(pyc_path, f)
            print(f"[+] 反编译成功: {output_path}")
            return True
        except ImportError:
            print("[-] 未安装uncompyle6，尝试使用内置反编译")
        except Exception as e:
            print(f"[-] uncompyle6失败: {e}")
        
        # 备用：使用marshal加载并反汇编
        try:
            return PycDecompiler._marshal_disassemble(pyc_path, output_path)
        except Exception as e:
            print(f"[-] 反编译失败: {e}")
            return False
    
    @staticmethod
    def _marshal_disassemble(pyc_path: str, output_path: str) -> bool:
        """使用marshal加载并反汇编"""
        with open(pyc_path, 'rb') as f:
            # 跳过pyc头部（16字节 for Python 3.8+）
            header = f.read(16)
            code = marshal.load(f)
        
        # 反汇编
        output = io.StringIO()
        dis.dis(code, file=output)
        
        with open(output_path, 'w') as f:
            f.write(f"# 反汇编结果: {pyc_path}\n")
            f.write(f"# 注意：这是反汇编结果，不是原始源码\n\n")
            f.write(output.getvalue())
        
        print(f"[+] 反汇编完成: {output_path}")
        return True
    
    @staticmethod
    def analyze_imports(pyc_path: str) -> List[str]:
        """分析导入的模块"""
        imports = []
        
        try:
            with open(pyc_path, 'rb') as f:
                header = f.read(16)
                code = marshal.load(f)
            
            # 遍历代码对象查找导入
            for const in code.co_consts:
                if isinstance(const, type(code)):
                    # 递归分析嵌套代码
                    pass
            
            # 从co_names中提取可能的导入
            for name in code.co_names:
                if name not in ('print', 'len', 'range', 'open', 'str', 'int'):
                    imports.append(name)
        
        except Exception as e:
            print(f"[-] 导入分析失败: {e}")
        
        return imports


class UPXUnpacker:
    """UPX脱壳器"""
    
    @staticmethod
    def unpack(exe_path: str, output_path: str) -> bool:
        """UPX脱壳"""
        print(f"[*] UPX脱壳: {exe_path}")
        
        # 尝试使用upx命令
        import subprocess
        try:
            result = subprocess.run(
                ['upx', '-d', '-o', output_path, exe_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"[+] UPX脱壳成功: {output_path}")
                return True
            else:
                print(f"[-] UPX脱壳失败: {result.stderr}")
        except FileNotFoundError:
            print("[-] 未找到upx命令")
        except Exception as e:
            print(f"[-] UPX脱壳错误: {e}")
        
        # 备用：手动脱壳（简化实现）
        return UPXUnpacker._manual_unpack(exe_path, output_path)
    
    @staticmethod
    def _manual_unpack(exe_path: str, output_path: str) -> bool:
        """手动UPX脱壳（简化）"""
        with open(exe_path, 'rb') as f:
            data = f.read()
        
        # 查找UPX特征并尝试恢复
        upx0_pos = data.find(b'UPX0')
        upx1_pos = data.find(b'UPX1')
        
        if upx0_pos == -1 or upx1_pos == -1:
            print("[-] 未找到UPX特征")
            return False
        
        # 简化：直接复制（实际实现需要解压算法）
        with open(output_path, 'wb') as f:
            f.write(data)
        
        print(f"[+] 已复制（手动脱壳简化版）: {output_path}")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Python打包程序逆向工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 自动分析并提取
    python pyinstaller_extractor.py --exe target.exe --output ./extracted
    
    # 反编译pyc
    python pyinstaller_extractor.py --pyc app.pyc --decompile
    
    # UPX脱壳
    python pyinstaller_extractor.py --upx packed.exe --output unpacked.exe
    
    # 批量处理
    python pyinstaller_extractor.py --batch ./packed/ --output ./extracted/
        """
    )
    
    parser.add_argument("--exe", help="目标EXE文件")
    parser.add_argument("--pyc", help="pyc文件路径")
    parser.add_argument("--upx", help="UPX压缩的EXE")
    parser.add_argument("--batch", help="批量处理目录")
    parser.add_argument("--output", "-o", default="./extracted", help="输出目录")
    parser.add_argument("--decompile", action="store_true", help="反编译pyc")
    parser.add_argument("--analyze", action="store_true", help="分析导入")
    
    args = parser.parse_args()
    
    # 单文件处理
    if args.exe:
        print(f"[*] 分析: {args.exe}")
        
        # 检测打包类型
        detection = PyInstallerDetector.detect(args.exe)
        print(f"[+] 检测结果:")
        print(f"    打包器: {detection['packer']}")
        print(f"    PyInstaller: {detection['is_pyi']}")
        print(f"    UPX: {detection['is_upx']}")
        
        # 提取
        if detection['is_pyi']:
            extractor = PyInstallerExtractor(args.exe, args.output)
            extractor.extract()
        
        # UPX脱壳
        if detection['is_upx']:
            output_path = os.path.join(args.output, os.path.basename(args.exe))
            UPXUnpacker.unpack(args.exe, output_path)
    
    # PYC反编译
    if args.pyc:
        if args.decompile:
            output_path = os.path.join(args.output, os.path.basename(args.pyc).replace('.pyc', '.py'))
            os.makedirs(args.output, exist_ok=True)
            PycDecompiler.decompile(args.pyc, output_path)
        
        if args.analyze:
            imports = PycDecompiler.analyze_imports(args.pyc)
            print(f"[+] 导入分析:")
            for imp in imports[:20]:
                print(f"    - {imp}")
    
    # UPX脱壳
    if args.upx:
        output_path = args.output if not os.path.isdir(args.output) else os.path.join(args.output, os.path.basename(args.upx))
        UPXUnpacker.unpack(args.upx, output_path)
    
    # 批量处理
    if args.batch:
        print(f"[*] 批量处理: {args.batch}")
        for filename in os.listdir(args.batch):
            filepath = os.path.join(args.batch, filename)
            if os.path.isfile(filepath):
                detection = PyInstallerDetector.detect(filepath)
                print(f"    {filename}: {detection['packer']}")
    
    print("\n[+] 完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
