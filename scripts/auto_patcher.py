#!/usr/bin/env python3
"""
auto_patcher.py - 自动化Patch工具
基于黑曼巴6.16实战经验开发

功能:
    1. 基于偏移参考自动Patch跳转
    2. 修改条件跳转（JE→JMP）
    3. 修改返回值（RET 0/1）
    4. 自动备份原始文件
    5. 验证Patch有效性

用法:
    # 自动Patch（基于偏移参考）
    python auto_patcher.py --exe game.exe --offset 0x123456 --patch-type jmp --backup
    
    # 修改条件跳转
    python auto_patcher.py --exe game.exe --offset 0x123456 --patch-type je2jmp --backup
    
    # 恢复备份
    python auto_patcher.py --exe game.exe --restore

依赖:
    - 无（纯Python实现）
"""

import argparse
import os
import sys
import struct
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class BinaryPatcher:
    """二进制Patch器"""
    
    # 常见Patch模式
    PATCH_PATTERNS = {
        'jmp': b'\xEB',  # 短跳转
        'je2jmp': b'\x90\x90',  # JE→NOP NOP
        'jne2jmp': b'\xEB',  # JNE→JMP
        'ret0': b'\xB8\x00\x00\x00\x00\xC3',  # MOV EAX, 0; RET
        'ret1': b'\xB8\x01\x00\x00\x00\xC3',  # MOV EAX, 1; RET
        'nop': b'\x90',  # NOP
        'nop5': b'\x90\x90\x90\x90\x90',  # 5 NOPs
        'call2nop': b'\x90\x90\x90\x90\x90',  # CALL→NOP
        'int3': b'\xCC',  # INT3断点
    }
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.backup_path = file_path + '.backup'
        self.data = None
        
    def load(self):
        """加载二进制文件"""
        with open(self.file_path, 'rb') as f:
            self.data = bytearray(f.read())
        print(f"[*] 加载: {self.file_path} ({len(self.data)} 字节)")
    
    def save(self, output_path: Optional[str] = None):
        """保存修改后的文件"""
        save_path = output_path or self.file_path
        with open(save_path, 'wb') as f:
            f.write(self.data)
        print(f"[+] 保存: {save_path}")
    
    def backup(self):
        """创建备份"""
        shutil.copy2(self.file_path, self.backup_path)
        print(f"[+] 备份: {self.backup_path}")
    
    def restore(self):
        """恢复备份"""
        if os.path.exists(self.backup_path):
            shutil.copy2(self.backup_path, self.file_path)
            print(f"[+] 恢复: {self.file_path}")
        else:
            print(f"[-] 备份不存在: {self.backup_path}")
    
    def patch_bytes(self, offset: int, new_bytes: bytes, description: str = ""):
        """Patch字节"""
        if offset < 0 or offset + len(new_bytes) > len(self.data):
            print(f"[-] 偏移越界: 0x{offset:08X}")
            return False
        
        # 记录原始值
        old_bytes = self.data[offset:offset+len(new_bytes)]
        
        # 应用Patch
        self.data[offset:offset+len(new_bytes)] = new_bytes
        
        print(f"[+] Patch 0x{offset:08X}: {old_bytes.hex()} → {new_bytes.hex()} {description}")
        
        return True
    
    def patch_je2jmp(self, offset: int):
        """JE→JMP"""
        # JE opcode: 0x74 XX
        # JMP opcode: 0xEB XX
        return self.patch_bytes(offset, b'\xEB', "JE→JMP")
    
    def patch_jne2jmp(self, offset: int):
        """JNE→JMP"""
        # JNE opcode: 0x75 XX
        # JMP opcode: 0xEB XX
        return self.patch_bytes(offset, b'\xEB', "JNE→JMP")
    
    def patch_ret0(self, offset: int):
        """RET 0"""
        return self.patch_bytes(offset, self.PATCH_PATTERNS['ret0'], "RET 0")
    
    def patch_ret1(self, offset: int):
        """RET 1"""
        return self.patch_bytes(offset, self.PATCH_PATTERNS['ret1'], "RET 1")
    
    def patch_nop(self, offset: int, size: int = 1):
        """NOP填充"""
        return self.patch_bytes(offset, b'\x90' * size, f"NOP x{size}")
    
    def find_pattern(self, pattern: bytes, start: int = 0) -> List[int]:
        """查找字节模式"""
        offsets = []
        pos = start
        while True:
            pos = self.data.find(pattern, pos)
            if pos == -1:
                break
            offsets.append(pos)
            pos += 1
        return offsets
    
    def verify(self) -> bool:
        """验证Patch有效性"""
        # 检查文件是否可执行
        if not os.access(self.file_path, os.X_OK):
            print(f"[!] 文件不可执行: {self.file_path}")
        
        # 检查PE头
        if self.data[:2] != b'MZ':
            print(f"[!] 不是有效的PE文件")
            return False
        
        print(f"[+] 验证通过")
        return True


class PatchManager:
    """Patch管理器"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.patcher = BinaryPatcher(file_path)
        self.patches = []
        
    def add_patch(self, offset: int, patch_type: str, description: str = ""):
        """添加Patch"""
        self.patches.append({
            'offset': offset,
            'type': patch_type,
            'description': description,
        })
        
    def apply_all(self, backup: bool = True):
        """应用所有Patch"""
        self.patcher.load()
        
        if backup:
            self.patcher.backup()
        
        for patch in self.patches:
            offset = patch['offset']
            patch_type = patch['type']
            description = patch['description']
            
            if patch_type == 'je2jmp':
                self.patcher.patch_je2jmp(offset)
            elif patch_type == 'jne2jmp':
                self.patcher.patch_jne2jmp(offset)
            elif patch_type == 'ret0':
                self.patcher.patch_ret0(offset)
            elif patch_type == 'ret1':
                self.patcher.patch_ret1(offset)
            elif patch_type == 'nop':
                self.patcher.patch_nop(offset)
            elif patch_type == 'jmp':
                self.patcher.patch_bytes(offset, b'\xEB', "JMP")
            else:
                print(f"[-] 未知Patch类型: {patch_type}")
        
        self.patcher.save()
        self.patcher.verify()
        
        print(f"[+] 应用 {len(self.patches)} 个Patch")


def main():
    parser = argparse.ArgumentParser(
        description="自动化Patch工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 自动Patch（基于偏移参考）
    python auto_patcher.py --exe game.exe --offset 0x123456 --patch-type jmp --backup
    
    # 修改条件跳转
    python auto_patcher.py --exe game.exe --offset 0x123456 --patch-type je2jmp --backup
    
    # 恢复备份
    python auto_patcher.py --exe game.exe --restore
        """
    )
    
    parser.add_argument("--exe", required=True, help="目标PE文件")
    parser.add_argument("--offset", type=lambda x: int(x, 0), help="Patch偏移（十六进制）")
    parser.add_argument("--patch-type", choices=['jmp', 'je2jmp', 'jne2jmp', 'ret0', 'ret1', 'nop'], help="Patch类型")
    parser.add_argument("--backup", action="store_true", help="创建备份")
    parser.add_argument("--restore", action="store_true", help="恢复备份")
    parser.add_argument("--output", "-o", help="输出文件路径")
    
    args = parser.parse_args()
    
    # 恢复备份
    if args.restore:
        patcher = BinaryPatcher(args.exe)
        patcher.restore()
        return 0
    
    # 应用Patch
    if args.offset and args.patch_type:
        patcher = BinaryPatcher(args.exe)
        patcher.load()
        
        if args.backup:
            patcher.backup()
        
        if args.patch_type == 'je2jmp':
            patcher.patch_je2jmp(args.offset)
        elif args.patch_type == 'jne2jmp':
            patcher.patch_jne2jmp(args.offset)
        elif args.patch_type == 'ret0':
            patcher.patch_ret0(args.offset)
        elif args.patch_type == 'ret1':
            patcher.patch_ret1(args.offset)
        elif args.patch_type == 'nop':
            patcher.patch_nop(args.offset)
        elif args.patch_type == 'jmp':
            patcher.patch_bytes(args.offset, b'\xEB', "JMP")
        
        patcher.save(args.output)
        patcher.verify()
    
    print("\n[+] 完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
