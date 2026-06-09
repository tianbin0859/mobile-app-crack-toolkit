#!/usr/bin/env python3
"""
APK静态分析工具
功能：识别壳类型、提取关键信息、分析加密特征
"""

import zipfile
import os
import re
import sys
import struct
from pathlib import Path

class APKAnalyzer:
    def __init__(self, apk_path):
        self.apk_path = apk_path
        self.info = {
            'package': None,
            'version': None,
            'min_sdk': None,
            'target_sdk': None,
            'permissions': [],
            'activities': [],
            'services': [],
            'receivers': [],
            'native_libs': [],
            'shell_type': None,
            'crypto_features': [],
            'suspicious_strings': []
        }
        
    def analyze(self):
        """执行完整分析"""
        print(f"[*] Analyzing: {self.apk_path}")
        
        with zipfile.ZipFile(self.apk_path, 'r') as zf:
            # 分析AndroidManifest.xml
            self._parse_manifest(zf)
            
            # 分析SO文件
            self._analyze_native_libs(zf)
            
            # 分析DEX文件
            self._analyze_dex(zf)
            
            # 分析资源
            self._analyze_resources(zf)
            
        # 识别壳类型
        self._identify_shell()
        
        return self.info
        
    def _parse_manifest(self, zf):
        """解析AndroidManifest.xml"""
        try:
            manifest = zf.read('AndroidManifest.xml')
            # 简化的XML解析（实际应用使用axmlparser）
            content = manifest.decode('utf-8', errors='ignore')
            
            # 提取包名
            pkg_match = re.search(r'package="([^"]+)"', content)
            if pkg_match:
                self.info['package'] = pkg_match.group(1)
                
            # 提取权限
            perms = re.findall(r'android\.permission\.([A-Z_]+)', content)
            self.info['permissions'] = perms
            
            # 提取组件
            self.info['activities'] = re.findall(r'activity[^>]*android:name="([^"]+)"', content)
            self.info['services'] = re.findall(r'service[^>]*android:name="([^"]+)"', content)
            self.info['receivers'] = re.findall(r'receiver[^>]*android:name="([^"]+)"', content)
            
        except Exception as e:
            print(f"[!] Manifest parse error: {e}")
            
    def _analyze_native_libs(self, zf):
        """分析原生库文件"""
        for name in zf.namelist():
            if name.startswith('lib/') and name.endswith('.so'):
                lib_name = os.path.basename(name)
                self.info['native_libs'].append(lib_name)
                
                # 读取SO分析
                try:
                    so_data = zf.read(name)
                    self._analyze_so_content(lib_name, so_data)
                except:
                    pass
                    
    def _analyze_so_content(self, lib_name, data):
        """分析SO文件内容"""
        # 检查加密特征
        crypto_features = []
        
        if b'AES' in data or b'aes' in data:
            crypto_features.append('AES')
        if b'RSA' in data or b'rsa' in data:
            crypto_features.append('RSA')
        if b'DES' in data or b'des' in data:
            crypto_features.append('DES')
        if b'MD5' in data or b'md5' in data:
            crypto_features.append('MD5')
        if b'SHA' in data:
            crypto_features.append('SHA')
            
        if crypto_features:
            self.info['crypto_features'].extend(crypto_features)
            print(f"[+] {lib_name} crypto: {crypto_features}")
            
        # 检查可疑字符串
        suspicious = [
            b'checkLicense', b'validate', b'authorize',
            b'premium', b'vip', b'pro_version',
            b'expired', b'trial', b'demo'
        ]
        
        for s in suspicious:
            if s in data:
                self.info['suspicious_strings'].append(f"{lib_name}: {s.decode()}")
                
    def _analyze_dex(self, zf):
        """分析DEX文件"""
        for name in zf.namelist():
            if name.endswith('.dex'):
                try:
                    dex_data = zf.read(name)
                    self._check_dex_encryption(dex_data)
                except:
                    pass
                    
    def _check_dex_encryption(self, dex_data):
        """检查DEX是否加密"""
        # 正常DEX头: "dex\n035\0"
        if not dex_data.startswith(b'dex\n'):
            print("[!] DEX header abnormal - possibly encrypted")
            
    def _analyze_resources(self, zf):
        """分析资源文件"""
        # 检查assets下的加密资源
        for name in zf.namelist():
            if name.startswith('assets/'):
                if 'jiagu' in name or 'shell' in name or 'protect' in name:
                    print(f"[!] Suspicious asset: {name}")
                    
    def _identify_shell(self):
        """识别加固壳类型"""
        libs = self.info['native_libs']
        
        shell_signatures = {
            '360加固': ['libjiagu.so', 'libjiagu_art.so'],
            '梆梆加固': ['libsecexe.so', 'libsecmain.so'],
            '爱加密': ['libexec.so', 'libexecmain.so'],
            '腾讯乐固': ['libshell.so', 'libtup.so'],
            '百度加固': ['libbaiduprotect.so'],
            '阿里聚安全': ['libmobisec.so'],
            '网易易盾': ['libnesec.so'],
            '通付盾': ['libegis.so'],
            '娜迦': ['libedog.so'],
            '海云安': ['libchaosvmp.so'],
            '顶象技术': ['libx3g.so'],
            '盛大': ['libapssec.so']
        }
        
        for shell_name, signatures in shell_signatures.items():
            for sig in signatures:
                if sig in libs:
                    self.info['shell_type'] = shell_name
                    print(f"[!] Shell detected: {shell_name} ({sig})")
                    return
                    
        # 检查VMP特征
        if any('libbaiduprotect' in lib for lib in libs):
            self.info['shell_type'] = '百度VMP'
        elif len(libs) == 0 and self._has_encrypted_dex():
            self.info['shell_type'] = 'Unknown (possibly VMP)'
            
    def _has_encrypted_dex(self):
        """检查是否有加密DEX"""
        try:
            with zipfile.ZipFile(self.apk_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.dex'):
                        data = zf.read(name)
                        if not data.startswith(b'dex\n'):
                            return True
        except:
            pass
        return False
        
    def print_report(self):
        """打印分析报告"""
        print("\n" + "="*60)
        print("APK ANALYSIS REPORT")
        print("="*60)
        print(f"Package: {self.info['package']}")
        print(f"Shell: {self.info['shell_type'] or 'None'}")
        print(f"Native libs: {', '.join(self.info['native_libs']) or 'None'}")
        print(f"Crypto features: {', '.join(set(self.info['crypto_features'])) or 'None'}")
        print(f"Permissions: {len(self.info['permissions'])}")
        print(f"Activities: {len(self.info['activities'])}")
        print(f"Services: {len(self.info['services'])}")
        
        if self.info['suspicious_strings']:
            print("\n[!] Suspicious strings:")
            for s in self.info['suspicious_strings'][:10]:
                print(f"    - {s}")
                
        print("="*60)


def main():
    if len(sys.argv) < 2:
        print("Usage: python apk_analyzer.py <target.apk>")
        sys.exit(1)
        
    apk_path = sys.argv[1]
    if not os.path.exists(apk_path):
        print(f"[!] File not found: {apk_path}")
        sys.exit(1)
        
    analyzer = APKAnalyzer(apk_path)
    analyzer.analyze()
    analyzer.print_report()


if __name__ == '__main__':
    main()
