#!/usr/bin/env python3
"""
APK资源修改工具
功能：修改标题、LOGO、包名、版本号等
"""

import xml.etree.ElementTree as ET
import shutil
import os
import re
import sys
from pathlib import Path


class APKModifier:
    def __init__(self, decoded_dir):
        self.decoded_dir = Path(decoded_dir)
        if not self.decoded_dir.exists():
            raise FileNotFoundError(f"Directory not found: {decoded_dir}")
            
    def change_app_name(self, new_name):
        """修改应用名称"""
        strings_path = self.decoded_dir / "res" / "values" / "strings.xml"
        if not strings_path.exists():
            print(f"[!] strings.xml not found")
            return False
            
        tree = ET.parse(strings_path)
        root = tree.getroot()
        
        modified = False
        for string in root.findall("string"):
            if string.get("name") == "app_name":
                string.text = new_name
                modified = True
                break
                
        if modified:
            tree.write(strings_path, encoding='utf-8', xml_declaration=True)
            print(f"[+] App name changed to: {new_name}")
        else:
            # 添加app_name
            new_elem = ET.SubElement(root, 'string', {'name': 'app_name'})
            new_elem.text = new_name
            tree.write(strings_path, encoding='utf-8', xml_declaration=True)
            print(f"[+] App name added: {new_name}")
            
        return True
        
    def replace_icon(self, icon_path):
        """替换图标"""
        icon_path = Path(icon_path)
        if not icon_path.exists():
            print(f"[!] Icon not found: {icon_path}")
            return False
            
        replaced = 0
        res_dir = self.decoded_dir / "res"
        
        for root, dirs, files in os.walk(res_dir):
            for file in files:
                if "ic_launcher" in file or "logo" in file or "icon" in file:
                    if file.endswith(('.png', '.jpg', '.webp')):
                        target = Path(root) / file
                        shutil.copy(icon_path, target)
                        replaced += 1
                        print(f"[+] Replaced: {target}")
                        
        print(f"[+] Total replaced: {replaced} icons")
        return replaced > 0
        
    def change_package(self, new_package):
        """修改包名（实现共存）"""
        manifest_path = self.decoded_dir / "AndroidManifest.xml"
        if not manifest_path.exists():
            print(f"[!] AndroidManifest.xml not found")
            return False
            
        with open(manifest_path, 'r') as f:
            content = f.read()
            
        # 提取原包名
        match = re.search(r'package="([^"]+)"', content)
        if not match:
            print(f"[!] Could not find package name")
            return False
            
        old_package = match.group(1)
        
        # 替换包名
        content = content.replace(f'package="{old_package}"', f'package="{new_package}"')
        
        with open(manifest_path, 'w') as f:
            f.write(content)
            
        # 替换Smali中的包名引用
        smali_dir = self.decoded_dir / "smali"
        if smali_dir.exists():
            self._replace_in_smali(old_package, new_package)
            
        print(f"[+] Package changed: {old_package} -> {new_package}")
        return True
        
    def _replace_in_smali(self, old_pkg, new_pkg):
        """在Smali文件中替换包名"""
        old_path = old_pkg.replace('.', '/')
        new_path = new_pkg.replace('.', '/')
        
        smali_dir = self.decoded_dir / "smali"
        modified = 0
        
        for root, dirs, files in os.walk(smali_dir):
            for file in files:
                if file.endswith(".smali"):
                    filepath = Path(root) / file
                    with open(filepath, 'r') as f:
                        content = f.read()
                        
                    if old_path in content:
                        content = content.replace(old_path, new_path)
                        with open(filepath, 'w') as f:
                            f.write(content)
                        modified += 1
                        
        print(f"[+] Modified {modified} Smali files")
        
    def change_version(self, version_name=None, version_code=None):
        """修改版本号"""
        manifest_path = self.decoded_dir / "AndroidManifest.xml"
        with open(manifest_path, 'r') as f:
            content = f.read()
            
        if version_name:
            content = re.sub(
                r'android:versionName="[^"]*"',
                f'android:versionName="{version_name}"',
                content
            )
            print(f"[+] Version name: {version_name}")
            
        if version_code:
            content = re.sub(
                r'android:versionCode="[^"]*"',
                f'android:versionCode="{version_code}"',
                content
            )
            print(f"[+] Version code: {version_code}")
            
        with open(manifest_path, 'w') as f:
            f.write(content)
            
    def remove_ads(self):
        """移除广告SDK（基础版）"""
        ad_patterns = [
            'com.google.android.gms.ads',
            'com.facebook.ads',
            'com.mopub',
            'com.unity3d.ads',
            'com.chartboost',
            'com.applovin',
            'com.adcolony'
        ]
        
        manifest_path = self.decoded_dir / "AndroidManifest.xml"
        with open(manifest_path, 'r') as f:
            content = f.read()
            
        removed = 0
        for pattern in ad_patterns:
            if pattern in content:
                # 简单移除包含广告SDK的activity/service
                content = re.sub(
                    rf'<activity[^>]*{re.escape(pattern)}[^>]*/?>',
                    '',
                    content
                )
                content = re.sub(
                    rf'<service[^>]*{re.escape(pattern)}[^>]*/?>',
                    '',
                    content
                )
                removed += 1
                print(f"[+] Removed ad SDK: {pattern}")
                
        with open(manifest_path, 'w') as f:
            f.write(content)
            
        print(f"[+] Total ad SDKs removed: {removed}")
        
    def add_permission(self, permission):
        """添加权限"""
        manifest_path = self.decoded_dir / "AndroidManifest.xml"
        with open(manifest_path, 'r') as f:
            content = f.read()
            
        if permission in content:
            print(f"[!] Permission already exists: {permission}")
            return
            
        # 在manifest标签内添加权限
        perm_line = f'    <uses-permission android:name="{permission}" />\n'
        content = content.replace(
            '<application',
            perm_line + '    <application'
        )
        
        with open(manifest_path, 'w') as f:
            f.write(content)
            
        print(f"[+] Added permission: {permission}")
        
    def patch_method(self, class_name, method_name, return_value):
        """修改Smali方法返回值"""
        # 将类名转换为Smali路径
        smali_path = class_name.replace('.', '/') + '.smali'
        
        # 在多个smali目录中查找
        for smali_dir in ['smali', 'smali_classes2', 'smali_classes3']:
            full_path = self.decoded_dir / smali_dir / smali_path
            if full_path.exists():
                with open(full_path, 'r') as f:
                    content = f.read()
                    
                # 查找方法并修改返回值
                method_pattern = rf'(\.method.*?{method_name}.*?\n)(.*?)(\.end method)'
                
                # 根据返回值类型生成Smali代码
                return_smali = self._get_return_smali(return_value)
                
                # 简单替换：在方法末尾添加return指令
                content = re.sub(
                    rf'(\.method.*?{method_name}.*?\n)(.*?)(\.end method)',
                    rf'\1\2\n    {return_smali}\n\3',
                    content,
                    flags=re.DOTALL
                )
                
                with open(full_path, 'w') as f:
                    f.write(content)
                    
                print(f"[+] Patched {class_name}.{method_name} -> {return_value}")
                return True
                
        print(f"[!] Class not found: {class_name}")
        return False
        
    def _get_return_smali(self, value):
        """根据值生成Smali返回指令"""
        if isinstance(value, bool):
            return 'return-{}'.format('true' if value else 'false')
        elif isinstance(value, int):
            if value == 0:
                return 'const/4 v0, 0x0\n    return v0'
            else:
                return f'const/4 v0, 0x{value}\n    return v0'
        elif isinstance(value, str):
            return f'const-string v0, "{value}"\n    return-object v0'
        else:
            return 'return-void'


def main():
    if len(sys.argv) < 3:
        print("Usage: python apk_modifier.py <decoded_dir> <command> [args...]")
        print("Commands:")
        print("  name <new_name>           - Change app name")
        print("  icon <icon_path>          - Replace icon")
        print("  package <new_package>     - Change package name")
        print("  version <name> [code]     - Change version")
        print("  remove_ads                - Remove ad SDKs")
        print("  permission <perm>         - Add permission")
        sys.exit(1)
        
    decoded_dir = sys.argv[1]
    command = sys.argv[2]
    
    modifier = APKModifier(decoded_dir)
    
    if command == 'name' and len(sys.argv) > 3:
        modifier.change_app_name(sys.argv[3])
    elif command == 'icon' and len(sys.argv) > 3:
        modifier.replace_icon(sys.argv[3])
    elif command == 'package' and len(sys.argv) > 3:
        modifier.change_package(sys.argv[3])
    elif command == 'version' and len(sys.argv) > 3:
        code = sys.argv[4] if len(sys.argv) > 4 else None
        modifier.change_version(sys.argv[3], code)
    elif command == 'remove_ads':
        modifier.remove_ads()
    elif command == 'permission' and len(sys.argv) > 3:
        modifier.add_permission(sys.argv[3])
    else:
        print("[!] Unknown command or missing arguments")


if __name__ == '__main__':
    main()
