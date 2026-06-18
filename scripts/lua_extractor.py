#!/usr/bin/env python3
"""
lua_extractor.py - Lua脚本提取工具
支持从游戏、应用中提取Lua脚本

功能:
    1. 自动识别Lua字节码和源码
    2. 提取Lua脚本（从APK、IPA、二进制）
    3. 反编译Lua字节码（luajit/lua5.x）
    4. 修改Lua脚本（Patch验证、解锁功能）
    5. 重新打包

用法:
    # 从APK提取Lua
    python lua_extractor.py --apk app.apk --extract --output ./lua
    
    # 反编译Lua字节码
    python lua_extractor.py --lua game.luac --decompile --output ./src
    
    # 修改Lua脚本
    python lua_extractor.py --lua script.lua --patch --replace "return false" "return true"

依赖:
    - pip install unluac
"""

import argparse
import os
import sys
import struct
import zipfile
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class LuaDetector:
    """Lua检测器"""
    
    # Lua特征签名
    LUA_SIGNATURES = {
        b'\x1bLua': 'Lua 5.x bytecode',
        b'\x1bLJ': 'LuaJIT bytecode',
    }
    
    # Lua源码特征
    LUA_SOURCE_PATTERNS = [
        r'function\s+\w+\s*\(',
        r'local\s+\w+\s*=',
        r'require\s*\(',
        r'module\s*\(',
    ]
    
    @staticmethod
    def detect(data: bytes) -> Dict[str, any]:
        """检测Lua类型"""
        result = {
            'is_lua': False,
            'type': 'Unknown',
            'version': 'Unknown',
            'jit': False,
            'features': [],
        }
        
        # 检查字节码特征
        for sig, desc in LuaDetector.LUA_SIGNATURES.items():
            if data.startswith(sig):
                result['is_lua'] = True
                result['type'] = desc
                result['features'].append(desc)
                
                # 提取版本
                if sig == b'\x1bLua':
                    version = data[4] if len(data) > 4 else 0
                    result['version'] = f'5.{version - 0x50}'
                elif sig == b'\x1bLJ':
                    result['jit'] = True
                    result['version'] = 'JIT'
        
        # 检查源码特征
        if not result['is_lua']:
            text = data.decode('utf-8', errors='ignore')
            for pattern in LuaDetector.LUA_SOURCE_PATTERNS:
                if re.search(pattern, text):
                    result['is_lua'] = True
                    result['type'] = 'Lua source'
                    result['features'].append('Lua source code')
                    break
        
        return result


class LuaExtractor:
    """Lua提取器"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.lua_files = []
        
    def extract_from_apk(self, output_dir: str) -> List[Dict]:
        """从APK提取Lua"""
        print(f"[*] 从APK提取Lua: {self.file_path}")
        
        lua_files = []
        
        with zipfile.ZipFile(self.file_path, 'r') as zf:
            for name in zf.namelist():
                if name.endswith(('.lua', '.luac', '.lua.bytes', '.lua.txt')):
                    # 提取文件
                    data = zf.read(name)
                    
                    # 检测类型
                    detection = LuaDetector.detect(data)
                    
                    output_path = os.path.join(output_dir, os.path.basename(name))
                    with open(output_path, 'wb') as f:
                        f.write(data)
                    
                    lua_files.append({
                        'name': name,
                        'type': detection['type'],
                        'version': detection['version'],
                        'size': len(data),
                        'output': output_path,
                    })
        
        self.lua_files = lua_files
        
        print(f"[+] 提取 {len(lua_files)} 个Lua文件")
        
        return lua_files
    
    def extract_from_binary(self, output_dir: str) -> List[Dict]:
        """从二进制提取Lua"""
        print(f"[*] 从二进制提取Lua: {self.file_path}")
        
        lua_files = []
        
        with open(self.file_path, 'rb') as f:
            data = f.read()
        
        # 查找Lua字节码特征
        pos = 0
        count = 0
        while True:
            # 查找Lua签名
            lua_pos = data.find(b'\x1bLua', pos)
            lj_pos = data.find(b'\x1bLJ', pos)
            
            if lua_pos == -1 and lj_pos == -1:
                break
            
            # 选择最近的一个
            if lua_pos == -1:
                found_pos = lj_pos
                sig = b'\x1bLJ'
            elif lj_pos == -1:
                found_pos = lua_pos
                sig = b'\x1bLua'
            else:
                if lua_pos < lj_pos:
                    found_pos = lua_pos
                    sig = b'\x1bLua'
                else:
                    found_pos = lj_pos
                    sig = b'\x1bLJ'
            
            # 提取Lua数据（简化：固定大小）
            lua_size = min(1048576, len(data) - found_pos)  # 最大1MB
            lua_data = data[found_pos:found_pos + lua_size]
            
            # 保存
            output_path = os.path.join(output_dir, f"extracted_{count}.lua")
            with open(output_path, 'wb') as f:
                f.write(lua_data)
            
            detection = LuaDetector.detect(lua_data)
            
            lua_files.append({
                'offset': found_pos,
                'type': detection['type'],
                'version': detection['version'],
                'size': lua_size,
                'output': output_path,
            })
            
            count += 1
            pos = found_pos + lua_size
        
        self.lua_files = lua_files
        
        print(f"[+] 提取 {len(lua_files)} 个Lua字节码")
        
        return lua_files
    
    def export_list(self, output_path: str):
        """导出文件列表"""
        with open(output_path, 'w') as f:
            for lua in self.lua_files:
                f.write(f"{lua['name'] if 'name' in lua else lua['output']}\t{lua['type']}\t{lua['version']}\n")
        
        print(f"[+] 导出列表: {output_path}")


class LuaDecompiler:
    """Lua反编译器"""
    
    @staticmethod
    def decompile(luac_path: str, output_path: str) -> bool:
        """反编译Lua字节码"""
        print(f"[*] 反编译: {luac_path}")
        
        # 尝试使用unluac
        import subprocess
        try:
            result = subprocess.run(
                ['java', '-jar', 'unluac.jar', luac_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                with open(output_path, 'w') as f:
                    f.write(result.stdout)
                print(f"[+] 反编译成功: {output_path}")
                return True
            else:
                print(f"[-] unluac失败: {result.stderr}")
        except FileNotFoundError:
            print("[-] 未找到unluac")
        except Exception as e:
            print(f"[-] 反编译错误: {e}")
        
        # 备用：提取字符串
        try:
            return LuaDecompiler._extract_strings(luac_path, output_path)
        except Exception as e:
            print(f"[-] 字符串提取失败: {e}")
        
        return False
    
    @staticmethod
    def _extract_strings(luac_path: str, output_path: str) -> bool:
        """提取字符串作为备用"""
        with open(luac_path, 'rb') as f:
            data = f.read()
        
        # 查找可打印字符串
        strings = []
        for match in re.finditer(b'[\x20-\x7e]{4,}', data):
            strings.append(match.group().decode('utf-8', errors='ignore'))
        
        with open(output_path, 'w') as f:
            f.write("-- 反编译失败，提取的字符串:\n")
            for s in strings:
                f.write(f"-- {s}\n")
        
        print(f"[+] 提取字符串: {output_path}")
        return True


class LuaPatcher:
    """Lua脚本Patch工具"""
    
    def __init__(self, lua_path: str):
        self.lua_path = lua_path
        
    def patch_source(self, old_code: str, new_code: str) -> bool:
        """Patch Lua源码"""
        print(f"[*] Patch Lua: {self.lua_path}")
        
        with open(self.lua_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        if old_code not in content:
            print(f"[-] 未找到代码: {old_code}")
            return False
        
        # 替换代码
        new_content = content.replace(old_code, new_code)
        
        # 保存
        output_path = self.lua_path.replace('.lua', '_patched.lua')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"[+] Patch完成: {output_path}")
        return True
    
    def patch_bytecode(self, offset: int, new_bytes: bytes) -> bool:
        """Patch Lua字节码"""
        print(f"[*] Patch Lua字节码: {self.lua_path} @ 0x{offset:X}")
        
        with open(self.lua_path, 'rb') as f:
            data = bytearray(f.read())
        
        if offset + len(new_bytes) > len(data):
            print("[-] Patch超出文件范围")
            return False
        
        data[offset:offset+len(new_bytes)] = new_bytes
        
        output_path = self.lua_path.replace('.luac', '_patched.luac')
        with open(output_path, 'wb') as f:
            f.write(data)
        
        print(f"[+] Patch完成: {output_path}")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Lua脚本提取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 从APK提取Lua
    python lua_extractor.py --apk app.apk --extract --output ./lua
    
    # 从二进制提取Lua
    python lua_extractor.py --bin game.exe --extract --output ./lua
    
    # 反编译Lua字节码
    python lua_extractor.py --lua game.luac --decompile --output ./src
    
    # 修改Lua脚本
    python lua_extractor.py --lua script.lua --patch --replace "return false" "return true"
        """
    )
    
    parser.add_argument("--apk", help="目标APK文件")
    parser.add_argument("--bin", help="目标二进制文件")
    parser.add_argument("--lua", help="Lua文件路径")
    parser.add_argument("--output", "-o", default="./lua_output", help="输出目录")
    parser.add_argument("--extract", action="store_true", help="提取Lua")
    parser.add_argument("--decompile", action="store_true", help="反编译")
    parser.add_argument("--patch", action="store_true", help="Patch脚本")
    parser.add_argument("--replace", nargs=2, metavar=('OLD', 'NEW'), help="替换代码")
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    # 从APK提取
    if args.apk and args.extract:
        extractor = LuaExtractor(args.apk)
        extractor.extract_from_apk(args.output)
        extractor.export_list(os.path.join(args.output, "lua_files.txt"))
    
    # 从二进制提取
    if args.bin and args.extract:
        extractor = LuaExtractor(args.bin)
        extractor.extract_from_binary(args.output)
        extractor.export_list(os.path.join(args.output, "lua_files.txt"))
    
    # 反编译
    if args.lua and args.decompile:
        output_path = os.path.join(args.output, os.path.basename(args.lua).replace('.luac', '.lua'))
        LuaDecompiler.decompile(args.lua, output_path)
    
    # Patch
    if args.lua and args.patch and args.replace:
        patcher = LuaPatcher(args.lua)
        patcher.patch_source(args.replace[0], args.replace[1])
    
    print("\n[+] 完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
