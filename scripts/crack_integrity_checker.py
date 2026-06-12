#!/usr/bin/env python3
"""
APK Crack Engine - 破解完整性校验模块 v1.0
校验破解结果是否完整、有效、无残留问题
"""

import json
import os
import hashlib
import zipfile
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

class CheckStatus(Enum):
    PASS = "✅ 通过"
    FAIL = "❌ 失败"
    WARN = "⚠️ 警告"
    SKIP = "⏭️ 跳过"
    INFO = "ℹ️ 信息"

@dataclass
class CheckResult:
    check_name: str
    status: CheckStatus
    message: str
    details: Dict = field(default_factory=dict)
    severity: str = "normal"  # normal, critical, minor

class CrackIntegrityChecker:
    """破解完整性校验器"""
    
    def __init__(self, target_path: str, crack_type: str = "apk"):
        self.target_path = target_path
        self.crack_type = crack_type.lower()
        self.results: List[CheckResult] = []
        self.score = 0
        self.max_score = 0
        
    def run_all_checks(self) -> Dict:
        """运行所有校验"""
        print("🔍 启动破解完整性校验...")
        print("=" * 60)
        
        # 1. 文件完整性校验
        self._check_file_integrity()
        
        # 2. 破解痕迹校验
        self._check_crack_traces()
        
        # 3. 功能解锁校验
        self._check_function_unlock()
        
        # 4. 反检测校验
        self._check_anti_detection()
        
        # 5. 残留问题校验
        self._check_residual_issues()
        
        # 6. 兼容性校验
        self._check_compatibility()
        
        # 7. 签名校验（APK）
        if self.crack_type == "apk":
            self._check_apk_signature()
            self._check_dex_integrity()
            self._check_native_libs()
        
        # 8. 存档校验（游戏）
        if self.crack_type in ["game_save", "steam"]:
            self._check_save_integrity()
        
        # 9. 网络验证校验
        self._check_network_verification()
        
        # 10. 生成报告
        return self._generate_report()
    
    def _check_file_integrity(self):
        """校验文件完整性"""
        print("\n[1/10] 文件完整性校验...")
        
        if not os.path.exists(self.target_path):
            self.results.append(CheckResult(
                "文件存在性",
                CheckStatus.FAIL,
                f"破解文件不存在: {self.target_path}",
                severity="critical"
            ))
            return
        
        # 检查文件大小
        file_size = os.path.getsize(self.target_path)
        if file_size == 0:
            self.results.append(CheckResult(
                "文件大小",
                CheckStatus.FAIL,
                "破解文件大小为0字节",
                {"size": file_size},
                severity="critical"
            ))
        elif file_size < 1024:
            self.results.append(CheckResult(
                "文件大小",
                CheckStatus.WARN,
                f"破解文件过小 ({file_size} bytes)，可能不完整",
                {"size": file_size},
                severity="normal"
            ))
        else:
            self.results.append(CheckResult(
                "文件大小",
                CheckStatus.PASS,
                f"文件大小正常: {file_size} bytes",
                {"size": file_size}
            ))
        
        # 检查文件格式
        if self.crack_type == "apk":
            try:
                with zipfile.ZipFile(self.target_path, 'r') as z:
                    file_list = z.namelist()
                    self.results.append(CheckResult(
                        "APK结构",
                        CheckStatus.PASS,
                        f"APK结构有效，包含 {len(file_list)} 个文件",
                        {"file_count": len(file_list)}
                    ))
                    
                    # 检查关键文件
                    required_files = ['AndroidManifest.xml', 'classes.dex']
                    missing = [f for f in required_files if f not in file_list]
                    if missing:
                        self.results.append(CheckResult(
                            "关键文件",
                            CheckStatus.FAIL,
                            f"缺少关键文件: {missing}",
                            {"missing": missing},
                            severity="critical"
                        ))
                    else:
                        self.results.append(CheckResult(
                            "关键文件",
                            CheckStatus.PASS,
                            "所有关键文件存在",
                            {"required": required_files}
                        ))
            except zipfile.BadZipFile:
                self.results.append(CheckResult(
                    "APK结构",
                    CheckStatus.FAIL,
                    "文件不是有效的ZIP/APK格式",
                    severity="critical"
                ))
    
    def _check_crack_traces(self):
        """校验破解痕迹"""
        print("[2/10] 破解痕迹校验...")
        
        if self.crack_type == "apk":
            try:
                with zipfile.ZipFile(self.target_path, 'r') as z:
                    # 检查是否包含破解相关文件
                    crack_indicators = ['frida', 'hook', 'patch', 'crack', 'mod']
                    suspicious_files = []
                    
                    for name in z.namelist():
                        lower_name = name.lower()
                        for indicator in crack_indicators:
                            if indicator in lower_name:
                                suspicious_files.append(name)
                    
                    if suspicious_files:
                        self.results.append(CheckResult(
                            "破解痕迹",
                            CheckStatus.WARN,
                            f"发现 {len(suspicious_files)} 个可疑文件",
                            {"files": suspicious_files[:10]},
                            severity="minor"
                        ))
                    else:
                        self.results.append(CheckResult(
                            "破解痕迹",
                            CheckStatus.PASS,
                            "未发现明显的破解痕迹文件",
                            severity="normal"
                        ))
                    
                    # 检查DEX修改痕迹
                    if 'classes.dex' in z.namelist():
                        dex_data = z.read('classes.dex')
                        # 检查常见的Hook字符串
                        hook_strings = [b'Xposed', b'Frida', b'hook', b'patch']
                        found_hooks = []
                        for hook_str in hook_strings:
                            if hook_str in dex_data:
                                found_hooks.append(hook_str.decode('utf-8', errors='ignore'))
                        
                        if found_hooks:
                            self.results.append(CheckResult(
                                "DEX Hook痕迹",
                                CheckStatus.WARN,
                                f"DEX中发现Hook相关字符串: {found_hooks}",
                                {"hooks": found_hooks},
                                severity="normal"
                            ))
                        else:
                            self.results.append(CheckResult(
                                "DEX Hook痕迹",
                                CheckStatus.PASS,
                                "DEX中未发现明显的Hook痕迹",
                                severity="normal"
                            ))
            except Exception as e:
                self.results.append(CheckResult(
                    "破解痕迹",
                    CheckStatus.SKIP,
                    f"无法检查: {str(e)}"
                ))
    
    def _check_function_unlock(self):
        """校验功能解锁"""
        print("[3/10] 功能解锁校验...")
        
        # 这里需要具体的破解目标信息
        # 通过分析破解前后的差异来判断
        self.results.append(CheckResult(
            "功能解锁",
            CheckStatus.INFO,
            "需要手动验证：VIP功能、会员限制、广告移除等是否生效",
            {"note": "建议安装到设备测试"},
            severity="normal"
        ))
    
    def _check_anti_detection(self):
        """反检测校验"""
        print("[4/10] 反检测校验...")
        
        if self.crack_type == "apk":
            try:
                with zipfile.ZipFile(self.target_path, 'r') as z:
                    # 检查是否包含反检测代码
                    anti_detect_indicators = [
                        b'getPackageName', b'getApplicationInfo',
                        b'signature', b'checkSignature',
                        b'XposedBridge', b'frida'
                    ]
                    
                    # 读取DEX检查
                    if 'classes.dex' in z.namelist():
                        dex_data = z.read('classes.dex')
                        
                        # 检查是否有反检测逻辑
                        has_anti_detect = any(ind in dex_data for ind in anti_detect_indicators)
                        
                        if has_anti_detect:
                            self.results.append(CheckResult(
                                "反检测",
                                CheckStatus.PASS,
                                "检测到反检测相关代码（可能是原始APK的检测逻辑）",
                                severity="normal"
                            ))
                        else:
                            self.results.append(CheckResult(
                                "反检测",
                                CheckStatus.WARN,
                                "未检测到反检测代码，可能已被移除或绕过",
                                severity="minor"
                            ))
            except Exception as e:
                self.results.append(CheckResult(
                    "反检测",
                    CheckStatus.SKIP,
                    f"无法检查: {str(e)}"
                ))
    
    def _check_residual_issues(self):
        """残留问题校验"""
        print("[5/10] 残留问题校验...")
        
        issues = []
        
        # 检查1: 是否还有未绕过的验证点
        issues.append("需验证：是否所有收费验证点都已绕过")
        
        # 检查2: 是否还有时间限制
        issues.append("需验证：试用期/过期检查是否已移除")
        
        # 检查3: 是否还有网络验证
        issues.append("需验证：网络验证是否已绕过或模拟")
        
        # 检查4: 功能完整性
        issues.append("需验证：破解后功能是否完整可用")
        
        self.results.append(CheckResult(
            "残留问题",
            CheckStatus.WARN,
            f"发现 {len(issues)} 个需手动验证的残留问题",
            {"issues": issues},
            severity="normal"
        ))
    
    def _check_compatibility(self):
        """兼容性校验"""
        print("[6/10] 兼容性校验...")
        
        if self.crack_type == "apk":
            try:
                with zipfile.ZipFile(self.target_path, 'r') as z:
                    # 检查minSdkVersion和targetSdkVersion
                    manifest = z.read('AndroidManifest.xml')
                    
                    # 简单的XML解析（实际应该用aapt或更复杂的解析）
                    sdk_match = re.search(b'android:minSdkVersion="(\d+)"', manifest)
                    if sdk_match:
                        min_sdk = int(sdk_match.group(1))
                        self.results.append(CheckResult(
                            "最低SDK版本",
                            CheckStatus.INFO,
                            f"最低SDK版本: {min_sdk}",
                            {"min_sdk": min_sdk}
                        ))
                    
                    # 检查ABI支持
                    abis = set()
                    for name in z.namelist():
                        if 'lib/' in name:
                            abi = name.split('/')[1] if len(name.split('/')) > 1 else 'unknown'
                            abis.add(abi)
                    
                    if abis:
                        self.results.append(CheckResult(
                            "ABI支持",
                            CheckStatus.PASS,
                            f"支持的ABI: {list(abis)}",
                            {"abis": list(abis)}
                        ))
            except Exception as e:
                self.results.append(CheckResult(
                    "兼容性",
                    CheckStatus.SKIP,
                    f"无法检查: {str(e)}"
                ))
    
    def _check_apk_signature(self):
        """APK签名校验"""
        print("[7/10] APK签名校验...")
        
        try:
            # 检查是否有签名
            with zipfile.ZipFile(self.target_path, 'r') as z:
                has_signature = any('META-INF/' in name for name in z.namelist())
                
                if has_signature:
                    self.results.append(CheckResult(
                        "APK签名",
                        CheckStatus.PASS,
                        "APK包含签名文件",
                        severity="normal"
                    ))
                else:
                    self.results.append(CheckResult(
                        "APK签名",
                        CheckStatus.FAIL,
                        "APK缺少签名文件，无法安装",
                        {"solution": "使用apksigner或jarsigner重新签名"},
                        severity="critical"
                    ))
        except Exception as e:
            self.results.append(CheckResult(
                "APK签名",
                CheckStatus.SKIP,
                f"无法检查: {str(e)}"
            ))
    
    def _check_dex_integrity(self):
        """DEX完整性校验"""
        print("[8/10] DEX完整性校验...")
        
        try:
            with zipfile.ZipFile(self.target_path, 'r') as z:
                if 'classes.dex' in z.namelist():
                    dex_data = z.read('classes.dex')
                    
                    # 检查DEX magic
                    if dex_data[:4] == b'dex\n':
                        self.results.append(CheckResult(
                            "DEX Magic",
                            CheckStatus.PASS,
                            "DEX文件头正确",
                            {"magic": dex_data[:8].hex()}
                        ))
                    else:
                        self.results.append(CheckResult(
                            "DEX Magic",
                            CheckStatus.FAIL,
                            f"DEX文件头异常: {dex_data[:8].hex()}",
                            severity="critical"
                        ))
                    
                    # 检查DEX校验和
                    # 实际应该计算并比较checksum
                    self.results.append(CheckResult(
                        "DEX校验和",
                        CheckStatus.INFO,
                        "DEX校验和检查需要更详细的解析",
                        {"note": "建议使用baksmali/smali验证"}
                    ))
        except Exception as e:
            self.results.append(CheckResult(
                "DEX完整性",
                CheckStatus.SKIP,
                f"无法检查: {str(e)}"
            ))
    
    def _check_native_libs(self):
        """Native库校验"""
        print("[9/10] Native库校验...")
        
        try:
            with zipfile.ZipFile(self.target_path, 'r') as z:
                so_files = [name for name in z.namelist() if name.endswith('.so')]
                
                if so_files:
                    self.results.append(CheckResult(
                        "Native库",
                        CheckStatus.PASS,
                        f"发现 {len(so_files)} 个SO文件",
                        {"so_files": so_files[:5]}
                    ))
                    
                    # 检查SO文件是否完整
                    for so in so_files[:3]:  # 只检查前3个
                        so_data = z.read(so)
                        if so_data[:4] == b'\x7fELF':
                            self.results.append(CheckResult(
                                f"SO完整性: {os.path.basename(so)}",
                                CheckStatus.PASS,
                                "ELF头正确",
                                severity="normal"
                            ))
                        else:
                            self.results.append(CheckResult(
                                f"SO完整性: {os.path.basename(so)}",
                                CheckStatus.FAIL,
                                f"ELF头异常: {so_data[:4].hex()}",
                                severity="critical"
                            ))
                else:
                    self.results.append(CheckResult(
                        "Native库",
                        CheckStatus.INFO,
                        "APK不包含Native库",
                        severity="normal"
                    ))
        except Exception as e:
            self.results.append(CheckResult(
                "Native库",
                CheckStatus.SKIP,
                f"无法检查: {str(e)}"
            ))
    
    def _check_save_integrity(self):
        """游戏存档完整性校验"""
        print("[存档校验] 游戏存档完整性...")
        
        try:
            with open(self.target_path, 'rb') as f:
                data = f.read()
            
            # 尝试解析为JSON
            try:
                save_data = json.loads(data.decode('utf-8'))
                self.results.append(CheckResult(
                    "存档格式",
                    CheckStatus.PASS,
                    "存档是有效的JSON格式",
                    {"keys": list(save_data.keys())[:10]}
                ))
                
                # 检查关键字段
                if 'discovered_relics' in save_data:
                    relic_count = len(save_data['discovered_relics'])
                    self.results.append(CheckResult(
                        "装备数量",
                        CheckStatus.PASS if relic_count > 50 else CheckStatus.WARN,
                        f"存档包含 {relic_count} 个装备",
                        {"relic_count": relic_count}
                    ))
                
                if 'gold' in save_data:
                    gold = save_data['gold']
                    self.results.append(CheckResult(
                        "金币数量",
                        CheckStatus.PASS if gold > 1000 else CheckStatus.INFO,
                        f"金币: {gold}",
                        {"gold": gold}
                    ))
                    
            except json.JSONDecodeError:
                self.results.append(CheckResult(
                    "存档格式",
                    CheckStatus.WARN,
                    "存档不是标准JSON格式，可能是二进制或加密格式",
                    {"size": len(data)},
                    severity="normal"
                ))
        except Exception as e:
            self.results.append(CheckResult(
                "存档完整性",
                CheckStatus.SKIP,
                f"无法检查: {str(e)}"
            ))
    
    def _check_network_verification(self):
        """网络验证校验"""
        print("[10/10] 网络验证校验...")
        
        # 检查APK中是否还有网络验证相关的域名/IP
        if self.crack_type == "apk":
            try:
                with zipfile.ZipFile(self.target_path, 'r') as z:
                    # 读取所有文本文件检查网络地址
                    network_indicators = []
                    for name in z.namelist():
                        if name.endswith(('.xml', '.json', '.txt', '.properties')):
                            try:
                                content = z.read(name).decode('utf-8', errors='ignore')
                                # 查找URL/IP
                                urls = re.findall(r'https?://[^\s"\']+', content)
                                ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', content)
                                if urls or ips:
                                    network_indicators.extend(urls[:3])
                                    network_indicators.extend(ips[:3])
                            except:
                                pass
                    
                    if network_indicators:
                        self.results.append(CheckResult(
                            "网络地址",
                            CheckStatus.WARN,
                            f"发现 {len(network_indicators)} 个网络地址",
                            {"addresses": network_indicators[:5]},
                            severity="normal"
                        ))
                    else:
                        self.results.append(CheckResult(
                            "网络地址",
                            CheckStatus.PASS,
                            "未发现明显的网络验证地址",
                            severity="normal"
                        ))
            except Exception as e:
                self.results.append(CheckResult(
                    "网络验证",
                    CheckStatus.SKIP,
                    f"无法检查: {str(e)}"
                ))
    
    def _generate_report(self) -> Dict:
        """生成校验报告"""
        print("\n" + "=" * 60)
        print("📊 破解完整性校验报告")
        print("=" * 60)
        
        # 统计结果
        status_counts = {status: 0 for status in CheckStatus}
        for result in self.results:
            status_counts[result.status] += 1
        
        # 计算得分
        critical_fails = sum(1 for r in self.results if r.status == CheckStatus.FAIL and r.severity == "critical")
        normal_fails = sum(1 for r in self.results if r.status == CheckStatus.FAIL and r.severity != "critical")
        warnings = sum(1 for r in self.results if r.status == CheckStatus.WARN)
        passes = sum(1 for r in self.results if r.status == CheckStatus.PASS)
        
        total_checks = len(self.results)
        
        # 完整性评分 (0-100)
        if critical_fails > 0:
            integrity_score = max(0, 30 - critical_fails * 10)
        elif normal_fails > 0:
            integrity_score = 60 - normal_fails * 5
        else:
            integrity_score = 90 - warnings * 3
        
        integrity_score = max(0, min(100, integrity_score))
        
        # 判断破解完整性
        if integrity_score >= 90:
            integrity_level = "完整"
            recommendation = "破解完整，可直接使用"
        elif integrity_score >= 70:
            integrity_level = "基本完整"
            recommendation = "破解基本可用，建议处理警告项"
        elif integrity_score >= 50:
            integrity_level = "部分完整"
            recommendation = "破解不完整，需要修复失败项"
        else:
            integrity_level = "不完整"
            recommendation = "破解失败，需要重新执行"
        
        # 输出详细结果
        print(f"\n📈 统计:")
        print(f"   总检查项: {total_checks}")
        print(f"   ✅ 通过: {passes}")
        print(f"   ❌ 失败: {critical_fails + normal_fails} (严重: {critical_fails})")
        print(f"   ⚠️ 警告: {warnings}")
        
        print(f"\n🎯 完整性评分: {integrity_score}/100")
        print(f"   等级: {integrity_level}")
        print(f"   建议: {recommendation}")
        
        # 输出失败项
        fails = [r for r in self.results if r.status == CheckStatus.FAIL]
        if fails:
            print(f"\n❌ 失败项详情:")
            for i, result in enumerate(fails, 1):
                print(f"   {i}. [{result.severity}] {result.check_name}")
                print(f"      → {result.message}")
                if result.details:
                    print(f"      → 详情: {result.details}")
        
        # 输出警告项
        warns = [r for r in self.results if r.status == CheckStatus.WARN]
        if warns:
            print(f"\n⚠️ 警告项详情:")
            for i, result in enumerate(warns, 1):
                print(f"   {i}. {result.check_name}")
                print(f"      → {result.message}")
        
        print("\n" + "=" * 60)
        
        return {
            "integrity_score": integrity_score,
            "integrity_level": integrity_level,
            "recommendation": recommendation,
            "total_checks": total_checks,
            "passes": passes,
            "fails": critical_fails + normal_fails,
            "critical_fails": critical_fails,
            "warnings": warnings,
            "details": [
                {
                    "check": r.check_name,
                    "status": r.status.value,
                    "message": r.message,
                    "details": r.details,
                    "severity": r.severity
                }
                for r in self.results
            ]
        }


def check_crack_integrity(target_path: str, crack_type: str = "apk") -> Dict:
    """
    快捷函数：校验破解完整性
    
    Args:
        target_path: 破解后的文件路径
        crack_type: 破解类型 (apk/exe/zip/game_save/steam/ipa)
    
    Returns:
        校验报告字典
    """
    checker = CrackIntegrityChecker(target_path, crack_type)
    return checker.run_all_checks()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python3 crack_integrity_checker.py <破解文件路径> [类型]")
        print("类型: apk, exe, zip, game_save, steam, ipa")
        sys.exit(1)
    
    target = sys.argv[1]
    crack_type = sys.argv[2] if len(sys.argv) > 2 else "apk"
    
    report = check_crack_integrity(target, crack_type)
    
    # 输出JSON报告
    print("\n📄 JSON报告:")
    print(json.dumps(report, indent=2, ensure_ascii=False))
