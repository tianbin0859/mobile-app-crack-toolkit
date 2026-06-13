"""完整性校验模块."""

import json
import os
import zipfile
import re
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

from apk_crack_engine.core.logger import logger


class CheckStatus(Enum):
    """检查状态."""

    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"
    INFO = "info"


@dataclass
class CheckResult:
    """单项检查结果."""

    check_name: str
    status: CheckStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "normal"  # normal, critical, minor


class IntegrityChecker:
    """破解完整性校验器."""

    def __init__(self, target_path: Path, crack_type: str = "apk"):
        self.target_path = target_path
        self.crack_type = crack_type.lower()
        self.results: List[CheckResult] = []

    def run_all_checks(self) -> Dict[str, Any]:
        """运行所有校验.

        Returns:
            校验报告
        """
        logger.info("启动破解完整性校验...")

        self._check_file_integrity()
        self._check_crack_traces()
        self._check_function_unlock()
        self._check_anti_detection()
        self._check_residual_issues()
        self._check_compatibility()

        if self.crack_type == "apk":
            self._check_apk_signature()
            self._check_dex_integrity()
            self._check_native_libs()

        if self.crack_type in ["game_save", "steam"]:
            self._check_save_integrity()

        self._check_network_verification()

        return self._generate_report()

    def _check_file_integrity(self) -> None:
        """文件完整性校验."""
        if not self.target_path.exists():
            self.results.append(CheckResult(
                "文件存在性",
                CheckStatus.FAIL,
                f"破解文件不存在: {self.target_path}",
                severity="critical",
            ))
            return

        file_size = self.target_path.stat().st_size
        if file_size == 0:
            self.results.append(CheckResult(
                "文件大小",
                CheckStatus.FAIL,
                "破解文件大小为0字节",
                {"size": file_size},
                severity="critical",
            ))
        elif file_size < 1024:
            self.results.append(CheckResult(
                "文件大小",
                CheckStatus.WARN,
                f"破解文件过小 ({file_size} bytes)",
                {"size": file_size},
            ))
        else:
            self.results.append(CheckResult(
                "文件大小",
                CheckStatus.PASS,
                f"文件大小正常: {file_size} bytes",
                {"size": file_size},
            ))

        if self.crack_type == "apk":
            try:
                with zipfile.ZipFile(self.target_path, "r") as z:
                    file_list = z.namelist()
                    self.results.append(CheckResult(
                        "APK结构",
                        CheckStatus.PASS,
                        f"APK结构有效，包含 {len(file_list)} 个文件",
                        {"file_count": len(file_list)},
                    ))

                    required = ["AndroidManifest.xml", "classes.dex"]
                    missing = [f for f in required if f not in file_list]
                    if missing:
                        self.results.append(CheckResult(
                            "关键文件",
                            CheckStatus.FAIL,
                            f"缺少关键文件: {missing}",
                            {"missing": missing},
                            severity="critical",
                        ))
                    else:
                        self.results.append(CheckResult(
                            "关键文件",
                            CheckStatus.PASS,
                            "所有关键文件存在",
                            {"required": required},
                        ))
            except zipfile.BadZipFile:
                self.results.append(CheckResult(
                    "APK结构",
                    CheckStatus.FAIL,
                    "无效ZIP/APK格式",
                    severity="critical",
                ))

    def _check_crack_traces(self) -> None:
        """破解痕迹校验."""
        if self.crack_type != "apk":
            return

        try:
            with zipfile.ZipFile(self.target_path, "r") as z:
                indicators = ["frida", "hook", "patch", "crack", "mod"]
                suspicious = []
                for name in z.namelist():
                    lower = name.lower()
                    for ind in indicators:
                        if ind in lower:
                            suspicious.append(name)

                if suspicious:
                    self.results.append(CheckResult(
                        "破解痕迹",
                        CheckStatus.WARN,
                        f"发现 {len(suspicious)} 个可疑文件",
                        {"files": suspicious[:10]},
                        severity="minor",
                    ))
                else:
                    self.results.append(CheckResult(
                        "破解痕迹",
                        CheckStatus.PASS,
                        "未发现明显破解痕迹",
                    ))

                # DEX Hook 痕迹
                if "classes.dex" in z.namelist():
                    dex_data = z.read("classes.dex")
                    hook_strings = [b"Xposed", b"Frida", b"hook", b"patch"]
                    found = [s.decode("utf-8", errors="ignore") for s in hook_strings if s in dex_data]
                    if found:
                        self.results.append(CheckResult(
                            "DEX Hook痕迹",
                            CheckStatus.WARN,
                            f"DEX中发现Hook字符串: {found}",
                            {"hooks": found},
                        ))
                    else:
                        self.results.append(CheckResult(
                            "DEX Hook痕迹",
                            CheckStatus.PASS,
                            "DEX中未发现Hook痕迹",
                        ))
        except Exception as e:
            self.results.append(CheckResult(
                "破解痕迹",
                CheckStatus.SKIP,
                f"无法检查: {e}",
            ))

    def _check_function_unlock(self) -> None:
        """功能解锁校验."""
        self.results.append(CheckResult(
            "功能解锁",
            CheckStatus.INFO,
            "需手动验证VIP/会员/广告是否已移除",
            {"note": "建议安装到设备测试"},
        ))

    def _check_anti_detection(self) -> None:
        """反检测校验."""
        if self.crack_type != "apk":
            return

        try:
            with zipfile.ZipFile(self.target_path, "r") as z:
                indicators = [
                    b"getPackageName", b"getApplicationInfo",
                    b"signature", b"checkSignature",
                    b"XposedBridge", b"frida",
                ]
                if "classes.dex" in z.namelist():
                    dex_data = z.read("classes.dex")
                    has_anti = any(ind in dex_data for ind in indicators)
                    if has_anti:
                        self.results.append(CheckResult(
                            "反检测",
                            CheckStatus.PASS,
                            "检测到反检测代码",
                        ))
                    else:
                        self.results.append(CheckResult(
                            "反检测",
                            CheckStatus.WARN,
                            "未检测到反检测代码",
                            severity="minor",
                        ))
        except Exception as e:
            self.results.append(CheckResult(
                "反检测",
                CheckStatus.SKIP,
                f"无法检查: {e}",
            ))

    def _check_residual_issues(self) -> None:
        """残留问题校验."""
        issues = [
            "需验证：所有收费验证点是否已绕过",
            "需验证：试用期/过期检查是否已移除",
            "需验证：网络验证是否已绕过",
            "需验证：破解后功能是否完整",
        ]
        self.results.append(CheckResult(
            "残留问题",
            CheckStatus.WARN,
            f"发现 {len(issues)} 个需手动验证的问题",
            {"issues": issues},
        ))

    def _check_compatibility(self) -> None:
        """兼容性校验."""
        if self.crack_type != "apk":
            return

        try:
            with zipfile.ZipFile(self.target_path, "r") as z:
                if "AndroidManifest.xml" in z.namelist():
                    manifest = z.read("AndroidManifest.xml")
                    match = re.search(rb'android:minSdkVersion="(\d+)"', manifest)
                    if match:
                        min_sdk = int(match.group(1))
                        self.results.append(CheckResult(
                            "最低SDK",
                            CheckStatus.INFO,
                            f"最低SDK: {min_sdk}",
                            {"min_sdk": min_sdk},
                        ))

                abis = set()
                for name in z.namelist():
                    if "lib/" in name:
                        parts = name.split("/")
                        if len(parts) > 1:
                            abis.add(parts[1])
                if abis:
                    self.results.append(CheckResult(
                        "ABI支持",
                        CheckStatus.PASS,
                        f"支持ABI: {list(abis)}",
                        {"abis": list(abis)},
                    ))
        except Exception as e:
            self.results.append(CheckResult(
                "兼容性",
                CheckStatus.SKIP,
                f"无法检查: {e}",
            ))

    def _check_apk_signature(self) -> None:
        """APK签名校验."""
        try:
            with zipfile.ZipFile(self.target_path, "r") as z:
                has_sig = any("META-INF/" in n for n in z.namelist())
                if has_sig:
                    self.results.append(CheckResult(
                        "APK签名",
                        CheckStatus.PASS,
                        "APK包含签名文件",
                    ))
                else:
                    self.results.append(CheckResult(
                        "APK签名",
                        CheckStatus.FAIL,
                        "APK缺少签名",
                        {"solution": "使用apksigner重新签名"},
                        severity="critical",
                    ))
        except Exception as e:
            self.results.append(CheckResult(
                "APK签名",
                CheckStatus.SKIP,
                f"无法检查: {e}",
            ))

    def _check_dex_integrity(self) -> None:
        """DEX完整性校验."""
        try:
            with zipfile.ZipFile(self.target_path, "r") as z:
                if "classes.dex" in z.namelist():
                    dex_data = z.read("classes.dex")
                    if dex_data[:4] == b"dex\n":
                        self.results.append(CheckResult(
                            "DEX Magic",
                            CheckStatus.PASS,
                            "DEX文件头正确",
                            {"magic": dex_data[:8].hex()},
                        ))
                    else:
                        self.results.append(CheckResult(
                            "DEX Magic",
                            CheckStatus.FAIL,
                            f"DEX文件头异常: {dex_data[:8].hex()}",
                            severity="critical",
                        ))
        except Exception as e:
            self.results.append(CheckResult(
                "DEX完整性",
                CheckStatus.SKIP,
                f"无法检查: {e}",
            ))

    def _check_native_libs(self) -> None:
        """Native库校验."""
        try:
            with zipfile.ZipFile(self.target_path, "r") as z:
                so_files = [n for n in z.namelist() if n.endswith(".so")]
                if so_files:
                    self.results.append(CheckResult(
                        "Native库",
                        CheckStatus.PASS,
                        f"发现 {len(so_files)} 个SO文件",
                        {"so_files": so_files[:5]},
                    ))
                    for so in so_files[:3]:
                        so_data = z.read(so)
                        if so_data[:4] == b"\x7fELF":
                            self.results.append(CheckResult(
                                f"SO完整性:{Path(so).name}",
                                CheckStatus.PASS,
                                "ELF头正确",
                            ))
                        else:
                            self.results.append(CheckResult(
                                f"SO完整性:{Path(so).name}",
                                CheckStatus.FAIL,
                                f"ELF头异常: {so_data[:4].hex()}",
                                severity="critical",
                            ))
                else:
                    self.results.append(CheckResult(
                        "Native库",
                        CheckStatus.INFO,
                        "APK不包含Native库",
                    ))
        except Exception as e:
            self.results.append(CheckResult(
                "Native库",
                CheckStatus.SKIP,
                f"无法检查: {e}",
            ))

    def _check_save_integrity(self) -> None:
        """游戏存档校验."""
        try:
            data = self.target_path.read_bytes()
            try:
                save_data = json.loads(data.decode("utf-8"))
                self.results.append(CheckResult(
                    "存档格式",
                    CheckStatus.PASS,
                    "存档是有效JSON",
                    {"keys": list(save_data.keys())[:10]},
                ))
                if "discovered_relics" in save_data:
                    count = len(save_data["discovered_relics"])
                    self.results.append(CheckResult(
                        "装备数量",
                        CheckStatus.PASS if count > 50 else CheckStatus.WARN,
                        f"存档包含 {count} 个装备",
                        {"relic_count": count},
                    ))
                if "gold" in save_data:
                    gold = save_data["gold"]
                    self.results.append(CheckResult(
                        "金币数量",
                        CheckStatus.PASS if gold > 1000 else CheckStatus.INFO,
                        f"金币: {gold}",
                        {"gold": gold},
                    ))
            except json.JSONDecodeError:
                self.results.append(CheckResult(
                    "存档格式",
                    CheckStatus.WARN,
                    "存档不是标准JSON",
                    {"size": len(data)},
                ))
        except Exception as e:
            self.results.append(CheckResult(
                "存档完整性",
                CheckStatus.SKIP,
                f"无法检查: {e}",
            ))

    def _check_network_verification(self) -> None:
        """网络验证校验."""
        if self.crack_type != "apk":
            return

        try:
            with zipfile.ZipFile(self.target_path, "r") as z:
                indicators = []
                for name in z.namelist():
                    if not name.endswith((".xml", ".json", ".txt", ".properties")):
                        continue
                    try:
                        content = z.read(name).decode("utf-8", errors="ignore")
                        urls = re.findall(r'https?://[^\s"\']+', content)
                        ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', content)
                        indicators.extend(urls[:3])
                        indicators.extend(ips[:3])
                    except Exception:
                        pass

                if indicators:
                    self.results.append(CheckResult(
                        "网络地址",
                        CheckStatus.WARN,
                        f"发现 {len(indicators)} 个网络地址",
                        {"addresses": indicators[:5]},
                    ))
                else:
                    self.results.append(CheckResult(
                        "网络地址",
                        CheckStatus.PASS,
                        "未发现网络验证地址",
                    ))
        except Exception as e:
            self.results.append(CheckResult(
                "网络验证",
                CheckStatus.SKIP,
                f"无法检查: {e}",
            ))

    def _generate_report(self) -> Dict[str, Any]:
        """生成校验报告.

        Returns:
            报告字典
        """
        passes = sum(1 for r in self.results if r.status == CheckStatus.PASS)
        critical_fails = sum(1 for r in self.results if r.status == CheckStatus.FAIL and r.severity == "critical")
        normal_fails = sum(1 for r in self.results if r.status == CheckStatus.FAIL and r.severity != "critical")
        warnings = sum(1 for r in self.results if r.status == CheckStatus.WARN)

        # 评分算法
        if critical_fails > 0:
            score = max(0, 30 - critical_fails * 10)
        elif normal_fails > 0:
            score = 60 - normal_fails * 5
        else:
            score = 90 - warnings * 3
        score = max(0, min(100, score))

        # 等级
        if score >= 90:
            level = "完整"
            recommendation = "破解完整，可直接使用"
        elif score >= 70:
            level = "基本完整"
            recommendation = "破解基本可用，建议处理警告项"
        elif score >= 50:
            level = "部分完整"
            recommendation = "需修复失败项"
        else:
            level = "不完整"
            recommendation = "破解失败，需重新执行"

        logger.info(f"完整性评分: {score}/100 ({level})")

        return {
            "integrity_score": score,
            "integrity_level": level,
            "recommendation": recommendation,
            "total_checks": len(self.results),
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
                    "severity": r.severity,
                }
                for r in self.results
            ],
        }


def check_integrity(target_path: str, crack_type: str = "apk") -> Dict[str, Any]:
    """快捷校验函数.

    Args:
        target_path: 目标文件路径
        crack_type: 破解类型

    Returns:
        校验报告
    """
    checker = IntegrityChecker(Path(target_path), crack_type)
    return checker.run_all_checks()


__all__ = ["IntegrityChecker", "check_integrity", "CheckStatus", "CheckResult"]
