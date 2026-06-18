#!/usr/bin/env python3
"""
ida_auto_patch.py - IDA Pro自动验证裁剪脚本 v1.0
自动定位验证函数并Patch为永远成功

用法:
    # 在IDA Pro中运行 (File -> Script file)
    # 或命令行: python ida_auto_patch.py --input "dumped.exe" --pattern "auth" --method "jmp"
    
    python ida_auto_patch.py --input "dumped.exe" --pattern "deltascript_rust::auth" --method "ret1"
    python ida_auto_patch.py --input "dumped.exe" --pattern "verify" --method "nop"
    python ida_auto_patch.py --list-patterns
"""

import argparse
import os
import sys
import json
from pathlib import Path

# IDA Pro Python API (仅在IDA环境中可用)
try:
    import ida_auto
    import idaapi
    import idautils
    import idc
    IDA_AVAILABLE = True
except ImportError:
    IDA_AVAILABLE = False
    print("[!] IDA Python API not available - running in standalone mode")

class IDAAutoPatch:
    """IDA Pro自动验证裁剪工具"""
    
    VERSION = "1.0.0"
    
    # 常见验证函数特征
    AUTH_PATTERNS = {
        "rust_auth": [
            "deltascript_rust::auth",
            "verify_license",
            "check_auth",
            "validate_key",
        ],
        "network_verify": [
            "send_request",
            "http_post",
            "verify_online",
            "check_server",
        ],
        "crypto_verify": [
            "verify_signature",
            "check_hash",
            "validate_hmac",
            "decrypt_config",
        ],
        "generic": [
            "is_authorized",
            "is_licensed",
            "is_expired",
            "is_valid",
        ]
    }
    
    # Patch方法
    PATCH_METHODS = {
        "ret1": {
            "name": "Return True",
            "description": "函数开头直接返回1 (成功)",
            "x86": "b8 01 00 00 00 c3",  # mov eax, 1; ret
            "x64": "b8 01 00 00 00 c3",  # mov eax, 1; ret
        },
        "ret0": {
            "name": "Return False",
            "description": "函数开头直接返回0 (失败)",
            "x86": "b8 00 00 00 00 c3",  # mov eax, 0; ret
            "x64": "b8 00 00 00 00 c3",  # mov eax, 0; ret
        },
        "jmp": {
            "name": "Unconditional Jump",
            "description": "条件跳转改为无条件跳转",
            "x86": "eb",  # jmp rel8
            "x64": "eb",  # jmp rel8
        },
        "nop": {
            "name": "NOP Slide",
            "description": "NOP掉关键指令",
            "x86": "90",  # nop
            "x64": "90",  # nop
        },
        "xor": {
            "name": "XOR Zero",
            "description": "xor eax, eax; ret (返回0)",
            "x86": "31 c0 c3",  # xor eax, eax; ret
            "x64": "31 c0 c3",  # xor eax, eax; ret
        }
    }
    
    def __init__(self, input_file, pattern=None, method="ret1"):
        self.input_file = input_file
        self.pattern = pattern
        self.method = method
        self.results = []
        
    def log(self, level, message):
        """记录日志"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def find_auth_functions(self):
        """查找验证函数"""
        self.log("INFO", "[*] 查找验证函数...")
        
        found_functions = []
        
        if not IDA_AVAILABLE:
            self.log("WARN", "IDA API不可用，使用字符串匹配模式")
            # 在独立模式下，提供搜索建议
            found_functions = self._find_patterns_standalone()
        else:
            # 在IDA环境中，使用IDA API搜索
            found_functions = self._find_patterns_ida()
        
        return found_functions
    
    def _find_patterns_standalone(self):
        """独立模式下的字符串搜索"""
        self.log("INFO", "    使用字符串搜索模式...")
        
        suggestions = []
        
        # 读取文件并搜索字符串
        try:
            with open(self.input_file, 'rb') as f:
                data = f.read()
                
            # 搜索所有模式
            for category, patterns in self.AUTH_PATTERNS.items():
                for pattern in patterns:
                    pattern_bytes = pattern.encode('utf-8')
                    pos = 0
                    while True:
                        pos = data.find(pattern_bytes, pos)
                        if pos == -1:
                            break
                        
                        suggestions.append({
                            "pattern": pattern,
                            "category": category,
                            "offset": hex(pos),
                            "type": "string"
                        })
                        pos += 1
        except Exception as e:
            self.log("ERROR", f"    文件读取失败: {str(e)}")
        
        self.log("INFO", f"    找到 {len(suggestions)} 个匹配")
        return suggestions
    
    def _find_patterns_ida(self):
        """IDA模式下的函数搜索"""
        functions = []
        
        # 搜索函数名
        for category, patterns in self.AUTH_PATTERNS.items():
            for pattern in patterns:
                # 使用IDA的搜索功能
                addr = idc.get_name_ea_simple(pattern)
                if addr != idc.BADADDR:
                    functions.append({
                        "name": pattern,
                        "address": hex(addr),
                        "category": category,
                        "type": "function"
                    })
        
        # 搜索字符串引用
        for string in idautils.Strings():
            for category, patterns in self.AUTH_PATTERNS.items():
                for pattern in patterns:
                    if pattern.lower() in str(string).lower():
                        functions.append({
                            "string": str(string),
                            "address": hex(string.ea),
                            "category": category,
                            "type": "string_ref"
                        })
        
        return functions
    
    def patch_function(self, func_info):
        """Patch验证函数"""
        self.log("INFO", f"[*] Patch函数: {func_info.get('name', func_info.get('pattern', 'unknown'))}")
        
        method = self.PATCH_METHODS.get(self.method)
        if not method:
            self.log("ERROR", f"    未知Patch方法: {self.method}")
            return False
        
        self.log("INFO", f"    方法: {method['name']} - {method['description']}")
        
        if not IDA_AVAILABLE:
            self.log("INFO", "    独立模式 - 生成Patch建议")
            return self._generate_patch_suggestion(func_info, method)
        else:
            self.log("INFO", "    IDA模式 - 直接Patch")
            return self._apply_patch_ida(func_info, method)
    
    def _generate_patch_suggestion(self, func_info, method):
        """生成Patch建议"""
        suggestion = {
            "function": func_info.get('name', func_info.get('pattern')),
            "address": func_info.get('address', func_info.get('offset')),
            "method": self.method,
            "method_name": method['name'],
            "description": method['description'],
            "x86_bytes": method['x86'],
            "x64_bytes": method['x64'],
            "steps": [
                f"1. 用IDA/x64dbg打开文件: {self.input_file}",
                f"2. 定位到地址: {func_info.get('address', func_info.get('offset'))}",
                f"3. 在函数开头Patch为: {method['x86']}",
                f"4. 保存修改",
                f"5. 测试验证"
            ]
        }
        
        self.results.append(suggestion)
        
        self.log("INFO", "    Patch建议:")
        self.log("INFO", f"    地址: {suggestion['address']}")
        self.log("INFO", f"    方法: {suggestion['method_name']}")
        self.log("INFO", f"    x86字节: {suggestion['x86_bytes']}")
        self.log("INFO", f"    x64字节: {suggestion['x64_bytes']}")
        
        return True
    
    def _apply_patch_ida(self, func_info, method):
        """在IDA中直接Patch"""
        try:
            addr = int(func_info['address'], 16)
            
            # 解析Patch字节
            patch_bytes = bytes.fromhex(method['x86'].replace(' ', ''))
            
            # 应用Patch
            for i, byte in enumerate(patch_bytes):
                idaapi.patch_byte(addr + i, byte)
            
            self.log("INFO", f"    ✅ Patch applied at {func_info['address']}")
            return True
            
        except Exception as e:
            self.log("ERROR", f"    Patch失败: {str(e)}")
            return False
    
    def generate_report(self):
        """生成Patch报告"""
        self.log("INFO", "[*] 生成Patch报告...")
        
        report = {
            "version": self.VERSION,
            "input_file": self.input_file,
            "pattern": self.pattern,
            "method": self.method,
            "results": self.results,
            "timestamp": str(datetime.now()),
        }
        
        report_path = f"{self.input_file}_patch_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.log("INFO", f"    ✅ 报告已保存: {report_path}")
        
        # 生成Markdown报告
        md_report = self._generate_markdown_report(report)
        md_path = f"{self.input_file}_patch_report.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_report)
        
        self.log("INFO", f"    ✅ Markdown报告: {md_path}")
        
        return report_path
    
    def _generate_markdown_report(self, report):
        """生成Markdown格式报告"""
        md = f"""# IDA自动验证裁剪报告

## 基本信息

- **工具版本**: {report['version']}
- **输入文件**: {report['input_file']}
- **搜索模式**: {report['pattern']}
- **Patch方法**: {report['method']}
- **生成时间**: {report['timestamp']}

## Patch结果

"""
        
        for i, result in enumerate(report['results'], 1):
            md += f"""### Patch {i}

- **函数**: {result['function']}
- **地址**: {result['address']}
- **方法**: {result['method_name']}
- **说明**: {result['description']}
- **x86字节**: `{result['x86_bytes']}`
- **x64字节**: `{result['x64_bytes']}`

**操作步骤**:
"""
            for step in result['steps']:
                md += f"1. {step}\n"
            md += "\n---\n\n"
        
        md += """## 验证清单

- [ ] Patch后文件能正常启动
- [ ] 断网环境下功能正常
- [ ] 使用错误卡密功能正常
- [ ] 所有功能模块工作正常

## 注意事项

1. 每次游戏更新后需重新Patch
2. 建议保留原始Dump文件
3. Patch前做好备份
4. 测试时先断网验证

---

*Generated by IDA Auto Patch v{VERSION}*
"""
        
        return md
    
    def run(self):
        """执行完整Patch流程"""
        self.log("INFO", "=" * 60)
        self.log("INFO", "IDA Pro自动验证裁剪工具 v" + self.VERSION)
        self.log("INFO", "=" * 60)
        
        # 查找验证函数
        functions = self.find_auth_functions()
        
        if not functions:
            self.log("WARN", "未找到验证函数，尝试通用搜索...")
            # 尝试更宽泛的搜索
            functions = self._find_generic_patterns()
        
        if not functions:
            self.log("ERROR", "未找到任何验证函数，请手动分析")
            return False
        
        self.log("INFO", f"找到 {len(functions)} 个候选函数")
        
        # Patch每个函数
        for func in functions:
            self.patch_function(func)
        
        # 生成报告
        self.generate_report()
        
        self.log("INFO", "=" * 60)
        self.log("INFO", "自动验证裁剪流程完成")
        self.log("INFO", "=" * 60)
        
        return True
    
    def _find_generic_patterns(self):
        """查找通用验证模式"""
        self.log("INFO", "[*] 通用模式搜索...")
        
        generic_patterns = [
            "auth", "verify", "check", "valid", "licens",
            "login", "register", "activate", "expire"
        ]
        
        results = []
        
        try:
            with open(self.input_file, 'rb') as f:
                data = f.read()
            
            for pattern in generic_patterns:
                pattern_bytes = pattern.encode('utf-8')
                pos = 0
                count = 0
                while True:
                    pos = data.find(pattern_bytes, pos)
                    if pos == -1 or count > 10:
                        break
                    
                    results.append({
                        "pattern": pattern,
                        "offset": hex(pos),
                        "type": "generic"
                    })
                    pos += 1
                    count += 1
        except:
            pass
        
        return results

def list_patterns():
    """列出所有内置模式"""
    print("[*] 内置验证函数模式:")
    
    for category, patterns in IDAAutoPatch.AUTH_PATTERNS.items():
        print(f"\n  [{category}]")
        for pattern in patterns:
            print(f"    - {pattern}")
    
    print("\n[*] Patch方法:")
    for method_id, method in IDAAutoPatch.PATCH_METHODS.items():
        print(f"\n  [{method_id}] {method['name']}")
        print(f"    {method['description']}")
        print(f"    x86: {method['x86']}")

def main():
    parser = argparse.ArgumentParser(
        description="IDA Pro自动验证裁剪工具 v1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 完整Patch流程
    python ida_auto_patch.py --input "dumped.exe" --pattern "auth" --method "ret1"
    
    # 使用NOP方法
    python ida_auto_patch.py --input "dumped.exe" --pattern "verify" --method "nop"
    
    # 列出所有模式
    python ida_auto_patch.py --list-patterns
        """
    )
    
    parser.add_argument("--input", "-i", help="输入文件路径")
    parser.add_argument("--pattern", "-p", help="搜索模式 (如: auth, verify)")
    parser.add_argument("--method", "-m", default="ret1", 
                       choices=["ret1", "ret0", "jmp", "nop", "xor"],
                       help="Patch方法 (默认: ret1)")
    parser.add_argument("--list-patterns", action="store_true", help="列出所有模式")
    
    args = parser.parse_args()
    
    if args.list_patterns:
        list_patterns()
        return
    
    if not args.input:
        print("Error: 请指定输入文件路径")
        parser.print_help()
        return
    
    # 创建Patch工具实例
    patcher = IDAAutoPatch(
        input_file=args.input,
        pattern=args.pattern,
        method=args.method
    )
    
    # 执行Patch
    patcher.run()

if __name__ == "__main__":
    from datetime import datetime
    main()
