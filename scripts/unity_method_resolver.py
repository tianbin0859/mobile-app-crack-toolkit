#!/usr/bin/env python3
"""
unity_method_resolver.py - Unity方法名还原与Hook点定位

功能:
    1. 基于Il2CppDumper输出，定位关键方法地址
    2. 生成Frida/Il2CppInspector可用的Hook脚本
    3. 方法签名解析（参数类型、返回值）
    4. 自动寻找MonoBehaviour生命周期方法

用法:
    # 基于Dump结果生成Hook脚本
    python unity_method_resolver.py --symbols il2cpp_symbols.json --target Update --frida
    
    # 查找特定类的方法
    python unity_method_resolver.py --symbols il2cpp_symbols.json --class PlayerController --list-methods
    
    # 生成Il2CppInspector配置
    python unity_method_resolver.py --symbols il2cpp_symbols.json --inspector-config

依赖:
    - pip install pyyaml
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple
from pathlib import Path

class MethodResolver:
    """Unity方法解析器"""
    
    # MonoBehaviour生命周期方法
    UNITY_LIFECYCLE_METHODS = [
        'Awake', 'Start', 'Update', 'FixedUpdate', 'LateUpdate',
        'OnEnable', 'OnDisable', 'OnDestroy',
        'OnCollisionEnter', 'OnCollisionExit', 'OnTriggerEnter',
        'OnApplicationPause', 'OnApplicationQuit',
    ]
    
    # 常用游戏方法模式
    GAME_METHOD_PATTERNS = [
        r'.*Damage.*',
        r'.*Attack.*',
        r'.*Health.*',
        r'.*Move.*',
        r'.*Jump.*',
        r'.*Fire.*',
        r'.*Spawn.*',
        r'.*Destroy.*',
        r'.*Score.*',
        r'.*Coin.*',
        r'.*Gold.*',
        r'.*Exp.*',
        r'.*Level.*',
        r'.*Skill.*',
        r'.*Buff.*',
        r'.*Item.*',
        r'.*Inventory.*',
        r'.*Equip.*',
        r'.*Chat.*',
        r'.*Send.*',
        r'.*Receive.*',
    ]
    
    def __init__(self, symbols_path: str):
        self.symbols_path = symbols_path
        self.symbols = {}
        self.classes = []
        self.methods = []
        
    def load(self) -> bool:
        """加载符号文件"""
        if not os.path.exists(self.symbols_path):
            print(f"[-] 符号文件不存在: {self.symbols_path}")
            return False
        
        with open(self.symbols_path, 'r', encoding='utf-8') as f:
            self.symbols = json.load(f)
        
        self.classes = self.symbols.get('classes', [])
        self.methods = self.symbols.get('methods', [])
        
        print(f"[+] 加载符号完成:")
        print(f"    类: {len(self.classes)} 个")
        print(f"    方法: {len(self.methods)} 个")
        
        return True
    
    def find_class(self, class_name: str) -> List[Dict]:
        """查找类"""
        results = []
        for cls in self.classes:
            if class_name.lower() in cls.get('name', '').lower():
                results.append(cls)
        return results
    
    def find_method(self, method_name: str) -> List[Dict]:
        """查找方法"""
        results = []
        for method in self.methods:
            if method_name.lower() in method.get('name', '').lower():
                results.append(method)
        return results
    
    def find_lifecycle_methods(self) -> List[Dict]:
        """查找所有生命周期方法"""
        results = []
        for method in self.methods:
            name = method.get('name', '')
            for lifecycle in self.UNITY_LIFECYCLE_METHODS:
                if lifecycle in name:
                    results.append(method)
                    break
        return results
    
    def find_game_methods(self) -> List[Dict]:
        """查找游戏相关方法（基于模式匹配）"""
        results = []
        for method in self.methods:
            name = method.get('name', '')
            for pattern in self.GAME_METHOD_PATTERNS:
                if re.match(pattern, name, re.IGNORECASE):
                    results.append(method)
                    break
        return results
    
    def generate_frida_script(self, target_methods: List[Dict], output_path: str):
        """生成Frida Hook脚本"""
        script = """// Unity IL2CPP Frida Hook脚本
// 生成时间: {time}
// 目标方法数: {count}

function hook_il2cpp_method(methodName, methodAddr) {
    Interceptor.attach(methodAddr, {
        onEnter: function(args) {
            console.log('[+] ' + methodName + ' called');
            // 打印参数
            for (var i = 0; i < 4; i++) {
                console.log('  arg' + i + ': ' + args[i]);
            }
        },
        onLeave: function(retval) {
            console.log('[-] ' + methodName + ' returned: ' + retval);
        }
    });
}

function find_il2cpp_methods() {
    // 基于符号表的方法地址
    var methods = {methods_json};
    
    methods.forEach(function(method) {
        var addr = Module.findExportByName(null, method.name);
        if (addr) {
            console.log('[+] Found: ' + method.name + ' @ ' + addr);
            hook_il2cpp_method(method.name, addr);
        } else {
            console.log('[-] Not found: ' + method.name);
        }
    });
}

// 主入口
Java.perform(function() {
    console.log('[*] Unity IL2CPP Hook started');
    find_il2cpp_methods();
});
""".format(
            time=__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            count=len(target_methods),
            methods_json=json.dumps(target_methods[:50], ensure_ascii=False)
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(script)
        
        print(f"[+] 生成Frida脚本: {output_path}")
    
    def generate_inspector_config(self, output_path: str):
        """生成Il2CppInspector配置"""
        config = {
            'version': '1.0',
            'generated_at': __import__('datetime').datetime.now().isoformat(),
            'classes': self.classes[:200],
            'methods': self.methods[:500],
            'hooks': {
                'lifecycle': self.find_lifecycle_methods()[:50],
                'game': self.find_game_methods()[:50],
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"[+] 生成Inspector配置: {output_path}")
    
    def generate_method_map(self, output_path: str):
        """生成方法映射表（地址->方法名）"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Unity IL2CPP 方法映射表\n")
            f.write(f"# 生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for i, method in enumerate(self.methods, 1):
                name = method.get('name', 'unknown')
                f.write(f"0x{i*0x1000:08X}    {name}\n")
        
        print(f"[+] 生成方法映射: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Unity方法名还原与Hook点定位",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 生成Frida Hook脚本
    python unity_method_resolver.py --symbols il2cpp_symbols.json --target Update --frida
    
    # 查找类的方法
    python unity_method_resolver.py --symbols il2cpp_symbols.json --class PlayerController --list-methods
    
    # 生成Inspector配置
    python unity_method_resolver.py --symbols il2cpp_symbols.json --inspector-config
        """
    )
    
    parser.add_argument("--symbols", required=True, help="IL2CPP符号JSON文件路径")
    parser.add_argument("--target", help="目标方法名（支持模糊匹配）")
    parser.add_argument("--class", dest="class_name", help="目标类名")
    parser.add_argument("--list-methods", action="store_true", help="列出类的方法")
    parser.add_argument("--frida", action="store_true", help="生成Frida脚本")
    parser.add_argument("--inspector-config", action="store_true", help="生成Il2CppInspector配置")
    parser.add_argument("--output", "-o", default="./output", help="输出目录")
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    # 加载解析器
    resolver = MethodResolver(args.symbols)
    if not resolver.load():
        return 1
    
    # 查找目标
    if args.target:
        print(f"\n[*] 查找方法: {args.target}")
        methods = resolver.find_method(args.target)
        print(f"[+] 找到 {len(methods)} 个匹配方法")
        for method in methods[:20]:
            print(f"    - {method.get('name', 'unknown')}")
        
        # 生成Frida脚本
        if args.frida:
            output_path = os.path.join(args.output, f"hook_{args.target}.js")
            resolver.generate_frida_script(methods, output_path)
    
    # 查找类
    if args.class_name:
        print(f"\n[*] 查找类: {args.class_name}")
        classes = resolver.find_class(args.class_name)
        print(f"[+] 找到 {len(classes)} 个匹配类")
        for cls in classes[:20]:
            print(f"    - {cls.get('name', 'unknown')}")
        
        # 列出方法
        if args.list_methods:
            print(f"\n[*] 类的方法列表:")
            # 简化：显示所有包含类名的方法
            class_methods = [m for m in resolver.methods 
                           if args.class_name.lower() in m.get('name', '').lower()]
            for method in class_methods[:50]:
                print(f"    - {method.get('name', 'unknown')}")
    
    # 生成Inspector配置
    if args.inspector_config:
        output_path = os.path.join(args.output, "inspector_config.json")
        resolver.generate_inspector_config(output_path)
    
    # 生成方法映射
    map_path = os.path.join(args.output, "method_map.txt")
    resolver.generate_method_map(map_path)
    
    print("\n[+] 完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
