#!/usr/bin/env python3
"""
APK深度分析模块 Pro
功能: 静态分析 + 动态分析 → 生成破解策略报告
"""

import os
import re
import json
import subprocess
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class VerificationPoint:
    """验证点"""
    type: str  # java/native/network/shared_prefs
    class_name: str
    method_name: str
    description: str
    confidence: float  # 0-1
    hook_strategy: str


@dataclass
class ProtectionInfo:
    """保护信息"""
    shell_type: str
    obfuscator: str
    anti_debug: List[str]
    anti_hook: List[str]
    root_detect: List[str]
    emulator_detect: List[str]
    network_security: str


@dataclass
class AnalysisReport:
    """分析报告"""
    package_name: str
    version: str
    min_sdk: int
    target_sdk: int
    protections: ProtectionInfo
    verification_points: List[VerificationPoint]
    native_libs: List[str]
    activities: List[str]
    services: List[str]
    receivers: List[str]
    suggested_strategy: str
    success_rate_estimate: float


class APKAnalyzerPro:
    """APK深度分析器"""

    def __init__(self, package_name: str):
        self.package_name = package_name
        self.apk_path = None
        self.decoded_dir = f"/tmp/{package_name}_analysis"
        self.report = None

    def full_analysis(self) -> AnalysisReport:
        """完整分析流程"""
        print(f"[*] 开始深度分析: {self.package_name}")
        
        # 1. 获取APK
        self._pull_apk()
        
        # 2. 反编译
        self._decode_apk()
        
        # 3. 静态分析
        protections = self._analyze_protections()
        verification_points = self._find_verification_points()
        native_libs = self._analyze_native_libs()
        components = self._analyze_components()
        
        # 4. 动态分析
        dynamic_info = self._dynamic_analysis()
        
        # 5. 生成策略
        strategy, success_rate = self._generate_strategy(
            protections, verification_points, dynamic_info
        )
        
        # 6. 生成报告
        self.report = AnalysisReport(
            package_name=self.package_name,
            version=self._get_version(),
            min_sdk=self._get_min_sdk(),
            target_sdk=self._get_target_sdk(),
            protections=protections,
            verification_points=verification_points,
            native_libs=native_libs,
            activities=components["activities"],
            services=components["services"],
            receivers=components["receivers"],
            suggested_strategy=strategy,
            success_rate_estimate=success_rate
        )
        
        self._print_report()
        return self.report

    def _pull_apk(self):
        """拉取APK"""
        result = subprocess.run(
            ["adb", "shell", f"pm path {self.package_name}"],
            capture_output=True, text=True
        )
        if "package:" in result.stdout:
            self.apk_path = result.stdout.replace("package:", "").strip()
            subprocess.run(
                ["adb", "pull", self.apk_path, f"/tmp/{self.package_name}.apk"],
                capture_output=True
            )
            self.apk_path = f"/tmp/{self.package_name}.apk"
            print(f"[+] APK已拉取: {self.apk_path}")

    def _decode_apk(self):
        """反编译APK"""
        subprocess.run(
            ["apktool", "d", self.apk_path, "-o", self.decoded_dir, "-f"],
            capture_output=True
        )
        print(f"[+] APK已反编译到: {self.decoded_dir}")

    def _analyze_protections(self) -> ProtectionInfo:
        """分析保护措施"""
        print("[*] 分析保护措施...")
        
        shell_type = self._detect_shell()
        obfuscator = self._detect_obfuscator()
        anti_debug = self._detect_anti_debug()
        anti_hook = self._detect_anti_hook()
        root_detect = self._detect_root_detection()
        emulator_detect = self._detect_emulator_detection()
        network_security = self._detect_network_security()
        
        protections = ProtectionInfo(
            shell_type=shell_type,
            obfuscator=obfuscator,
            anti_debug=anti_debug,
            anti_hook=anti_hook,
            root_detect=root_detect,
            emulator_detect=emulator_detect,
            network_security=network_security
        )
        
        print(f"[+] 壳类型: {shell_type}")
        print(f"[+] 混淆器: {obfuscator}")
        print(f"[+] 反调试: {', '.join(anti_debug) if anti_debug else '无'}")
        print(f"[+] 反Hook: {', '.join(anti_hook) if anti_hook else '无'}")
        
        return protections

    def _detect_shell(self) -> str:
        """检测壳"""
        lib_dir = os.path.join(self.decoded_dir, "lib")
        if not os.path.exists(lib_dir):
            return "none"
        
        shell_patterns = {
            "360加固": ["libjiagu", "libjiagu_art", "libprotectClass"],
            "梆梆加固": ["libsecexe", "libsecmain", "libSecShell"],
            "爱加密": ["libexec", "libexecmain", "ijiami"],
            "腾讯乐固": ["libshell", "libtup", "libBugly"],
            "百度加固": ["libbaiduprotect"],
            "网易易盾": ["libnesec"],
            "阿里聚安全": ["libmobisec"],
            "顶象技术": ["libx3g"],
            "通付盾": ["libegis"],
            "海云安": ["libchaosvmp"],
            "娜迦": ["libedog"],
            "VMP": ["libvmp"],
        }
        
        so_files = []
        for root, dirs, files in os.walk(lib_dir):
            for f in files:
                if f.endswith(".so"):
                    so_files.append(f.lower())
        
        for shell_name, patterns in shell_patterns.items():
            for so in so_files:
                for pattern in patterns:
                    if pattern.lower() in so:
                        return shell_name
        
        return "none"

    def _detect_obfuscator(self) -> str:
        """检测混淆器"""
        smali_dir = os.path.join(self.decoded_dir, "smali")
        if not os.path.exists(smali_dir):
            return "none"
        
        # 检查ProGuard特征
        proguard_patterns = ["a/a/a", "a/b/c", "a.a.a"]
        
        # 检查类名混淆程度
        class_count = 0
        obfuscated_count = 0
        
        for root, dirs, files in os.walk(smali_dir):
            for f in files:
                if f.endswith(".smali"):
                    class_count += 1
                    # 检查短类名（混淆特征）
                    class_name = f.replace(".smali", "")
                    if len(class_name) <= 2:
                        obfuscated_count += 1
        
        if class_count > 0:
            ratio = obfuscated_count / class_count
            if ratio > 0.5:
                return "ProGuard/R8 (重度混淆)"
            elif ratio > 0.2:
                return "ProGuard/R8 (中度混淆)"
        
        # 检查Allatori/DashO等
        manifest = os.path.join(self.decoded_dir, "AndroidManifest.xml")
        if os.path.exists(manifest):
            with open(manifest, 'r') as f:
                content = f.read()
                if "allatori" in content.lower():
                    return "Allatori"
                if "dasho" in content.lower():
                    return "DashO"
        
        return "none"

    def _detect_anti_debug(self) -> List[str]:
        """检测反调试"""
        methods = []
        
        # 检查smali代码
        smali_dir = os.path.join(self.decoded_dir, "smali")
        if os.path.exists(smali_dir):
            for root, dirs, files in os.walk(smali_dir):
                for f in files:
                    if f.endswith(".smali"):
                        path = os.path.join(root, f)
                        with open(path, 'r', errors='ignore') as file:
                            content = file.read()
                            
                            if "android/os/Debug" in content and "isDebuggerConnected" in content:
                                methods.append("Debug.isDebuggerConnected")
                            if "/proc/self/status" in content and "TracerPid" in content:
                                methods.append("TracerPid检测")
                            if "ptrace" in content:
                                methods.append("ptrace反调试")
                            if "inotify" in content:
                                methods.append("inotify调试检测")
        
        return list(set(methods))

    def _detect_anti_hook(self) -> List[str]:
        """检测反Hook"""
        methods = []
        
        smali_dir = os.path.join(self.decoded_dir, "smali")
        if os.path.exists(smali_dir):
            for root, dirs, files in os.walk(smali_dir):
                for f in files:
                    if f.endswith(".smali"):
                        path = os.path.join(root, f)
                        with open(path, 'r', errors='ignore') as file:
                            content = file.read()
                            
                            if "XposedBridge" in content:
                                methods.append("Xposed检测")
                            if "frida" in content.lower():
                                methods.append("Frida检测")
                            if "substrate" in content.lower():
                                methods.append("Substrate检测")
                            if "stackCheck" in content or "stack_check" in content:
                                methods.append("栈检测")
        
        return list(set(methods))

    def _detect_root_detection(self) -> List[str]:
        """检测Root检测"""
        methods = []
        
        smali_dir = os.path.join(self.decoded_dir, "smali")
        if os.path.exists(smali_dir):
            for root, dirs, files in os.walk(smali_dir):
                for f in files:
                    if f.endswith(".smali"):
                        path = os.path.join(root, f)
                        with open(path, 'r', errors='ignore') as file:
                            content = file.read()
                            
                            checks = [
                                ("su", "su二进制检测"),
                                ("Superuser", "Superuser检测"),
                                ("com.koushikdutta.superuser", "Superuser包检测"),
                                ("/system/bin/su", "su路径检测"),
                                ("/system/xbin/su", "su路径检测"),
                                ("ro.debuggable", "debuggable检测"),
                                ("ro.secure", "secure检测"),
                                ("magisk", "Magisk检测"),
                            ]
                            
                            for pattern, name in checks:
                                if pattern in content and name not in methods:
                                    methods.append(name)
        
        return methods

    def _detect_emulator_detection(self) -> List[str]:
        """检测模拟器检测"""
        methods = []
        
        smali_dir = os.path.join(self.decoded_dir, "smali")
        if os.path.exists(smali_dir):
            for root, dirs, files in os.walk(smali_dir):
                for f in files:
                    if f.endswith(".smali"):
                        path = os.path.join(root, f)
                        with open(path, 'r', errors='ignore') as file:
                            content = file.read()
                            
                            checks = [
                                ("qemu", "QEMU检测"),
                                ("goldfish", "Goldfish检测"),
                                ("generic", "Generic检测"),
                                ("sdk", "SDK检测"),
                                ("emu", "模拟器检测"),
                            ]
                            
                            for pattern, name in checks:
                                if pattern in content.lower() and name not in methods:
                                    methods.append(name)
        
        return methods

    def _detect_network_security(self) -> str:
        """检测网络安全配置"""
        network_config = os.path.join(self.decoded_dir, "res/xml/network_security_config.xml")
        if os.path.exists(network_config):
            with open(network_config, 'r') as f:
                content = f.read()
                if "cleartextTrafficPermitted" in content:
                    return "允许明文传输"
                if "trust-anchors" in content:
                    return "自定义证书信任"
        
        # 检查是否使用OkHttp CertificatePinner
        smali_dir = os.path.join(self.decoded_dir, "smali")
        if os.path.exists(smali_dir):
            for root, dirs, files in os.walk(smali_dir):
                for f in files:
                    if f.endswith(".smali"):
                        path = os.path.join(root, f)
                        with open(path, 'r', errors='ignore') as file:
                            content = file.read()
                            if "CertificatePinner" in content:
                                return "OkHttp证书固定"
                            if "X509TrustManager" in content:
                                return "自定义TrustManager"
        
        return "标准配置"

    def _find_verification_points(self) -> List[VerificationPoint]:
        """查找验证点"""
        print("[*] 查找验证点...")
        points = []
        
        # 1. 查找SharedPreferences验证
        points.extend(self._find_shared_prefs_verification())
        
        # 2. 查找Java层验证方法
        points.extend(self._find_java_verification())
        
        # 3. 查找Native层验证
        points.extend(self._find_native_verification())
        
        # 4. 查找网络验证
        points.extend(self._find_network_verification())
        
        print(f"[+] 发现 {len(points)} 个验证点")
        for p in points:
            print(f"    [{p.type}] {p.class_name}.{p.method_name} (置信度: {p.confidence:.0%})")
        
        return points

    def _find_shared_prefs_verification(self) -> List[VerificationPoint]:
        """查找SharedPreferences验证"""
        points = []
        
        smali_dir = os.path.join(self.decoded_dir, "smali")
        if not os.path.exists(smali_dir):
            return points
        
        vip_keywords = ["vip", "premium", "auth", "license", "member", "pro", "paid"]
        
        for root, dirs, files in os.walk(smali_dir):
            for f in files:
                if f.endswith(".smali"):
                    path = os.path.join(root, f)
                    with open(path, 'r', errors='ignore') as file:
                        content = file.read()
                        
                        for keyword in vip_keywords:
                            if keyword in content.lower():
                                # 提取类名
                                class_match = re.search(r'\.class.*L([^;]+);', content)
                                if class_match:
                                    class_name = class_match.group(1).replace("/", ".")
                                    points.append(VerificationPoint(
                                        type="shared_prefs",
                                        class_name=class_name,
                                        method_name="getBoolean/putBoolean",
                                        description=f"SharedPreferences含{keyword}关键字",
                                        confidence=0.7,
                                        hook_strategy="Hook SharedPreferences.getBoolean强制返回true"
                                    ))
        
        return points

    def _find_java_verification(self) -> List[VerificationPoint]:
        """查找Java层验证"""
        points = []
        
        smali_dir = os.path.join(self.decoded_dir, "smali")
        if not os.path.exists(smali_dir):
            return points
        
        method_patterns = [
            (r'isVip\b', "isVip检查", 0.9),
            (r'checkPermission\b', "权限检查", 0.8),
            (r'verifyLicense\b', "许可证验证", 0.9),
            (r'checkAuth\b', "授权检查", 0.85),
            (r'isMember\b', "会员检查", 0.9),
            (r'isPremium\b', "高级用户检查", 0.9),
            (r'canUse\b', "功能可用检查", 0.7),
            (r'isExpired\b', "过期检查", 0.8),
        ]
        
        for root, dirs, files in os.walk(smali_dir):
            for f in files:
                if f.endswith(".smali"):
                    path = os.path.join(root, f)
                    with open(path, 'r', errors='ignore') as file:
                        content = file.read()
                        
                        for pattern, desc, confidence in method_patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                class_match = re.search(r'\.class.*L([^;]+);', content)
                                if class_match:
                                    class_name = class_match.group(1).replace("/", ".")
                                    points.append(VerificationPoint(
                                        type="java",
                                        class_name=class_name,
                                        method_name=pattern.replace(r'\b', ''),
                                        description=desc,
                                        confidence=confidence,
                                        hook_strategy=f"Hook {class_name}.{pattern.replace(chr(92)+'b', '')}强制返回true"
                                    ))
        
        return points

    def _find_native_verification(self) -> List[VerificationPoint]:
        """查找Native层验证"""
        points = []
        
        lib_dir = os.path.join(self.decoded_dir, "lib")
        if not os.path.exists(lib_dir):
            return points
        
        # 检查SO文件中的字符串
        for root, dirs, files in os.walk(lib_dir):
            for f in files:
                if f.endswith(".so"):
                    path = os.path.join(root, f)
                    result = subprocess.run(
                        ["strings", path],
                        capture_output=True, text=True
                    )
                    strings = result.stdout
                    
                    if any(kw in strings.lower() for kw in ["vip", "auth", "license", "premium"]):
                        points.append(VerificationPoint(
                            type="native",
                            class_name=f,
                            method_name="unknown",
                            description="SO文件含验证关键字",
                            confidence=0.6,
                            hook_strategy="Hook SO中相关函数或内存Patch"
                        ))
        
        return points

    def _find_network_verification(self) -> List[VerificationPoint]:
        """查找网络验证"""
        points = []
        
        smali_dir = os.path.join(self.decoded_dir, "smali")
        if not os.path.exists(smali_dir):
            return points
        
        url_patterns = [
            r'https?://[^\s"\']+api[^\s"\']*',
            r'https?://[^\s"\']+auth[^\s"\']*',
            r'https?://[^\s"\']+verify[^\s"\']*',
            r'https?://[^\s"\']+license[^\s"\']*',
        ]
        
        urls_found = set()
        for root, dirs, files in os.walk(smali_dir):
            for f in files:
                if f.endswith(".smali"):
                    path = os.path.join(root, f)
                    with open(path, 'r', errors='ignore') as file:
                        content = file.read()
                        
                        for pattern in url_patterns:
                            matches = re.findall(pattern, content)
                            urls_found.update(matches)
        
        if urls_found:
            for url in list(urls_found)[:5]:  # 最多5个
                points.append(VerificationPoint(
                    type="network",
                    class_name="Network",
                    method_name="HTTP Request",
                    description=f"验证URL: {url}",
                    confidence=0.75,
                    hook_strategy="Hook HTTP响应修改返回值"
                ))
        
        return points

    def _analyze_native_libs(self) -> List[str]:
        """分析Native库"""
        libs = []
        lib_dir = os.path.join(self.decoded_dir, "lib")
        if os.path.exists(lib_dir):
            for root, dirs, files in os.walk(lib_dir):
                for f in files:
                    if f.endswith(".so"):
                        libs.append(f)
        return libs

    def _analyze_components(self) -> Dict[str, List[str]]:
        """分析组件"""
        manifest = os.path.join(self.decoded_dir, "AndroidManifest.xml")
        components = {
            "activities": [],
            "services": [],
            "receivers": []
        }
        
        if os.path.exists(manifest):
            with open(manifest, 'r') as f:
                content = f.read()
                
                components["activities"] = re.findall(
                    r'android:name="([^"]+)"', 
                    str(re.findall(r'<activity[^>]*>', content))
                )
                components["services"] = re.findall(
                    r'android:name="([^"]+)"',
                    str(re.findall(r'<service[^>]*>', content))
                )
                components["receivers"] = re.findall(
                    r'android:name="([^"]+)"',
                    str(re.findall(r'<receiver[^>]*>', content))
                )
        
        return components

    def _dynamic_analysis(self) -> Dict:
        """动态分析"""
        print("[*] 动态分析（需要运行APP）...")
        
        # 这里可以添加Frida动态分析
        # 例如：运行时类枚举、方法调用跟踪等
        
        return {
            "runtime_classes": [],
            "hook_points_verified": [],
            "network_requests": []
        }

    def _generate_strategy(
        self, 
        protections: ProtectionInfo,
        verification_points: List[VerificationPoint],
        dynamic_info: Dict
    ) -> Tuple[str, float]:
        """生成破解策略"""
        
        strategies = []
        success_rate = 0.9
        
        # 根据保护程度调整成功率
        if protections.shell_type != "none":
            success_rate -= 0.1
            strategies.append(f"先脱壳 ({protections.shell_type})")
        
        if protections.anti_hook:
            success_rate -= 0.15
            strategies.append("绕过反Hook检测")
        
        if protections.anti_debug:
            success_rate -= 0.1
            strategies.append("绕过反调试")
        
        # 根据验证点选择策略
        java_points = [p for p in verification_points if p.type == "java"]
        native_points = [p for p in verification_points if p.type == "native"]
        network_points = [p for p in verification_points if p.type == "network"]
        prefs_points = [p for p in verification_points if p.type == "shared_prefs"]
        
        if java_points:
            strategies.append(f"Java层Hook ({len(java_points)}个验证点)")
        
        if native_points:
            strategies.append(f"Native层Hook ({len(native_points)}个SO)")
            success_rate -= 0.1
        
        if network_points:
            strategies.append(f"网络响应修改 ({len(network_points)}个URL)")
            success_rate -= 0.15
        
        if prefs_points:
            strategies.append(f"SharedPreferences伪造 ({len(prefs_points)}个)")
        
        if not strategies:
            strategies.append("通用Hook策略")
            success_rate = 0.5
        
        strategy = " → ".join(strategies)
        success_rate = max(0.3, min(0.95, success_rate))
        
        return strategy, success_rate

    def _get_version(self) -> str:
        """获取版本"""
        manifest = os.path.join(self.decoded_dir, "apktool.yml")
        if os.path.exists(manifest):
            with open(manifest, 'r') as f:
                content = f.read()
                match = re.search(r'versionName: (.+)', content)
                if match:
                    return match.group(1).strip()
        return "unknown"

    def _get_min_sdk(self) -> int:
        """获取minSdk"""
        manifest = os.path.join(self.decoded_dir, "apktool.yml")
        if os.path.exists(manifest):
            with open(manifest, 'r') as f:
                content = f.read()
                match = re.search(r'minSdkVersion: (\d+)', content)
                if match:
                    return int(match.group(1))
        return 0

    def _get_target_sdk(self) -> int:
        """获取targetSdk"""
        manifest = os.path.join(self.decoded_dir, "apktool.yml")
        if os.path.exists(manifest):
            with open(manifest, 'r') as f:
                content = f.read()
                match = re.search(r'targetSdkVersion: (\d+)', content)
                if match:
                    return int(match.group(1))
        return 0

    def _print_report(self):
        """打印报告"""
        print("\n" + "=" * 60)
        print("APK深度分析报告")
        print("=" * 60)
        print(f"包名: {self.report.package_name}")
        print(f"版本: {self.report.version}")
        print(f"SDK: min={self.report.min_sdk}, target={self.report.target_sdk}")
        print(f"\n保护措施:")
        print(f"  壳: {self.report.protections.shell_type}")
        print(f"  混淆: {self.report.protections.obfuscator}")
        print(f"  反调试: {', '.join(self.report.protections.anti_debug) or '无'}")
        print(f"  反Hook: {', '.join(self.report.protections.anti_hook) or '无'}")
        print(f"  Root检测: {', '.join(self.report.protections.root_detect) or '无'}")
        print(f"  网络安全: {self.report.protections.network_security}")
        print(f"\n验证点 ({len(self.report.verification_points)}个):")
        for i, p in enumerate(self.report.verification_points[:10], 1):
            print(f"  {i}. [{p.type}] {p.class_name}.{p.method_name}")
            print(f"     描述: {p.description}")
            print(f"     策略: {p.hook_strategy}")
        if len(self.report.verification_points) > 10:
            print(f"     ... 还有 {len(self.report.verification_points) - 10} 个")
        print(f"\n建议策略: {self.report.suggested_strategy}")
        print(f"预估成功率: {self.report.success_rate_estimate:.0%}")
        print("=" * 60)

    def export_report(self, path: str):
        """导出报告为JSON"""
        report_dict = asdict(self.report)
        report_dict['protections'] = asdict(self.report.protections)
        report_dict['verification_points'] = [
            asdict(p) for p in self.report.verification_points
        ]
        
        with open(path, 'w') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        print(f"[+] 报告已导出: {path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="APK深度分析")
    parser.add_argument("package", help="目标包名")
    parser.add_argument("--export", help="导出报告路径")
    args = parser.parse_args()
    
    analyzer = APKAnalyzerPro(args.package)
    report = analyzer.full_analysis()
    
    if args.export:
        analyzer.export_report(args.export)


if __name__ == "__main__":
    main()
