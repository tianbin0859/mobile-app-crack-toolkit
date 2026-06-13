"""APK 分析器, 整合基础版 + Pro 版."""

import re
import os
import zipfile
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

from apk_crack_engine.core.logger import logger
from apk_crack_engine.core.models import AnalysisReport, VerificationPoint
from apk_crack_engine.analysis.shell_detector import shell_detector
from apk_crack_engine.utils.apk_utils import apk_utils
from apk_crack_engine.utils.adb import adb


@dataclass
class NativeLibInfo:
    """Native 库信息."""

    name: str
    path: str
    crypto_features: List[str] = field(default_factory=list)


class APKAnalyzer:
    """APK 分析器."""

    # 可疑字符串模式
    SUSPICIOUS_PATTERNS = [
        r"vip", r"premium", r"license", r"auth", r"verify",
        r"check", r"valid", r"expire", r"trial", r"register",
        r"unlock", r"pro", r"member", r"subscription",
    ]

    # 反调试特征
    ANTI_DEBUG_PATTERNS = [
        r"android\.os\.Debug",
        r"isDebuggerConnected",
        r"TracerPid",
        r"/proc/self/status",
        r"ptrace",
        r"inotify",
    ]

    # 反 Hook 特征
    ANTI_HOOK_PATTERNS = [
        r"XposedBridge",
        r"de\.robv\.android\.xposed",
        r"frida",
        r"substrate",
    ]

    # Root 检测特征
    ROOT_DETECTION_PATTERNS = [
        r"/system/bin/su",
        r"/system/xbin/su",
        r"com\.koushikdutta\.superuser",
        r"com\.thirdparty\.superuser",
        r"de\.robv\.android\.xposed\.installer",
        r"com\.saurik\.substrate",
        r"Magisk",
    ]

    def __init__(self, package_name: str, apk_path: Optional[Path] = None) -> None:
        self.package_name = package_name
        self.apk_path = apk_path
        self.decoded_dir: Optional[Path] = None
        self._report: Optional[AnalysisReport] = None

    def full_analysis(self) -> AnalysisReport:
        """执行完整分析.

        Returns:
            分析报告
        """
        logger.info(f"开始分析 APK: {self.package_name}")

        # 获取 APK
        if not self.apk_path:
            try:
                self.apk_path = apk_utils.pull_apk(self.package_name)
            except Exception as e:
                logger.warning(f"从设备拉取 APK 失败: {e}")
                self.apk_path = None

        # 基础信息
        info = self._get_basic_info()

        # 壳检测
        shell_type = self._detect_shell()

        # 混淆检测
        obfuscator = self._detect_obfuscation()

        # 反调试检测
        anti_debug = self._detect_anti_debug()

        # 反 Hook 检测
        anti_hook = self._detect_anti_hook()

        # Root 检测
        root_detection = self._detect_root()

        # 验证点分析
        verification_points = self._find_verification_points()

        # 生成策略建议
        strategy, success_rate = self._generate_strategy(
            shell_type, obfuscator, anti_debug, anti_hook,
            root_detection, verification_points
        )

        report = AnalysisReport(
            package_name=self.package_name,
            version=info.get("version"),
            min_sdk=info.get("min_sdk"),
            target_sdk=info.get("target_sdk"),
            shell_type=shell_type,
            obfuscator=obfuscator,
            anti_debug=anti_debug,
            anti_hook=anti_hook,
            root_detection=root_detection,
            verification_points=verification_points,
            suggested_strategy=strategy,
            success_rate_estimate=success_rate,
        )

        self._report = report
        logger.info(f"分析完成: {self.package_name}, 预估成功率: {success_rate:.0%}")
        return report

    def _get_basic_info(self) -> Dict[str, Any]:
        """获取基础信息."""
        info = {}

        if self.apk_path and self.apk_path.exists():
            # 从 APK 文件获取
            apk_info = apk_utils.get_apk_info(self.apk_path)
            info.update(apk_info)

            try:
                with zipfile.ZipFile(self.apk_path, "r") as z:
                    if "AndroidManifest.xml" in z.namelist():
                        manifest = z.read("AndroidManifest.xml")
                        # 简单的二进制 XML 解析
                        info["min_sdk"] = self._extract_sdk_version(manifest, b"minSdkVersion")
                        info["target_sdk"] = self._extract_sdk_version(manifest, b"targetSdkVersion")
            except Exception as e:
                logger.warning(f"解析 Manifest 失败: {e}")

        # 从设备获取
        try:
            dumpsys = adb.dumpsys_package(self.package_name)
            ver_match = re.search(r"versionName=(\S+)", dumpsys)
            if ver_match:
                info["version"] = ver_match.group(1)
        except Exception as e:
            logger.warning(f"dumpsys 获取失败: {e}")

        return info

    def _extract_sdk_version(self, manifest_data: bytes, key: bytes) -> Optional[int]:
        """从二进制 XML 提取 SDK 版本."""
        try:
            # 简单的二进制 XML 解析
            idx = manifest_data.find(key)
            if idx != -1:
                # 向后查找值
                after = manifest_data[idx:idx + 100]
                # 查找数值模式
                nums = re.findall(rb'(\d+)', after)
                if nums:
                    return int(nums[0])
        except Exception:
            pass
        return None

    def _detect_shell(self) -> str:
        """检测壳类型."""
        if self.apk_path and self.apk_path.exists():
            return shell_detector.detect_from_apk(self.apk_path)
        return "unknown"

    def _detect_obfuscation(self) -> str:
        """检测混淆器."""
        if not self.apk_path or not self.apk_path.exists():
            return "unknown"

        try:
            # 反编译后检查 Smali
            self.decoded_dir = apk_utils.decode_apk(self.apk_path)
            smali_dir = self.decoded_dir / "smali"
            if smali_dir.exists():
                smali_files = []
                for root, _, files in os.walk(smali_dir):
                    for f in files:
                        if f.endswith(".smali"):
                            smali_files.append(f)
                return shell_detector.detect_obfuscator(smali_files)
        except Exception as e:
            logger.warning(f"混淆检测失败: {e}")

        return "none"

    def _detect_anti_debug(self) -> List[str]:
        """检测反调试方法."""
        found = []
        if not self.decoded_dir:
            return found

        smali_dir = self.decoded_dir / "smali"
        if not smali_dir.exists():
            return found

        for pattern in self.ANTI_DEBUG_PATTERNS:
            for root, _, files in os.walk(smali_dir):
                for f in files:
                    if not f.endswith(".smali"):
                        continue
                    path = Path(root) / f
                    try:
                        content = path.read_text(errors="ignore")
                        if re.search(pattern, content, re.IGNORECASE):
                            found.append(pattern)
                            break
                    except Exception:
                        pass
                if pattern in found:
                    break

        return list(set(found))

    def _detect_anti_hook(self) -> List[str]:
        """检测反 Hook 方法."""
        found = []
        if not self.decoded_dir:
            return found

        smali_dir = self.decoded_dir / "smali"
        if not smali_dir.exists():
            return found

        for pattern in self.ANTI_HOOK_PATTERNS:
            for root, _, files in os.walk(smali_dir):
                for f in files:
                    if not f.endswith(".smali"):
                        continue
                    path = Path(root) / f
                    try:
                        content = path.read_text(errors="ignore")
                        if re.search(pattern, content, re.IGNORECASE):
                            found.append(pattern)
                            break
                    except Exception:
                        pass
                if pattern in found:
                    break

        return list(set(found))

    def _detect_root(self) -> List[str]:
        """检测 Root 检测方法."""
        found = []
        if not self.decoded_dir:
            return found

        smali_dir = self.decoded_dir / "smali"
        if not smali_dir.exists():
            return found

        for pattern in self.ROOT_DETECTION_PATTERNS:
            for root, _, files in os.walk(smali_dir):
                for f in files:
                    if not f.endswith(".smali"):
                        continue
                    path = Path(root) / f
                    try:
                        content = path.read_text(errors="ignore")
                        if re.search(pattern, content, re.IGNORECASE):
                            found.append(pattern)
                            break
                    except Exception:
                        pass
                if pattern in found:
                    break

        return list(set(found))

    def _find_verification_points(self) -> List[VerificationPoint]:
        """查找验证点."""
        points = []
        if not self.decoded_dir:
            return points

        smali_dir = self.decoded_dir / "smali"
        if not smali_dir.exists():
            return points

        for root, _, files in os.walk(smali_dir):
            for f in files:
                if not f.endswith(".smali"):
                    continue
                path = Path(root) / f
                try:
                    content = path.read_text(errors="ignore")
                    for pattern in self.SUSPICIOUS_PATTERNS:
                        if re.search(pattern, content, re.IGNORECASE):
                            # 提取类名
                            class_match = re.search(r"\.class\s+.*\s+L([\w/]+);", content)
                            class_name = class_match.group(1).replace("/", ".") if class_match else "unknown"

                            # 查找方法
                            method_matches = re.findall(
                                r"\.method\s+.*\s+(is\w+|check\w+|verify\w+|get\w+Type)\b",
                                content, re.IGNORECASE
                            )

                            for method in method_matches:
                                points.append(VerificationPoint(
                                    type="java",
                                    class_name=class_name,
                                    method_name=method,
                                    description=f"{pattern} 相关验证",
                                    suggested_strategy=f"Hook {class_name}.{method} 强制返回 true",
                                ))

                            # 检查 SharedPreferences
                            if "SharedPreferences" in content:
                                points.append(VerificationPoint(
                                    type="shared_prefs",
                                    class_name=class_name,
                                    description="SharedPreferences 含验证关键字",
                                    suggested_strategy="Hook SharedPreferences.getBoolean 强制返回 true",
                                ))

                            break
                except Exception:
                    pass

        # 去重
        seen = set()
        unique_points = []
        for p in points:
            key = f"{p.type}:{p.class_name}:{p.method_name}"
            if key not in seen:
                seen.add(key)
                unique_points.append(p)

        return unique_points

    def _generate_strategy(
        self,
        shell_type: str,
        obfuscator: str,
        anti_debug: List[str],
        anti_hook: List[str],
        root_detection: List[str],
        verification_points: List[VerificationPoint],
    ) -> tuple:
        """生成策略建议.

        Returns:
            (策略描述, 预估成功率)
        """
        # 基础成功率
        base_rate = 0.95

        # 壳影响
        if shell_type != "none":
            base_rate -= 0.15

        # 混淆影响
        if obfuscator != "none":
            base_rate -= 0.05

        # 反调试影响
        if anti_debug:
            base_rate -= 0.05 * len(anti_debug)

        # 反 Hook 影响
        if anti_hook:
            base_rate -= 0.1 * len(anti_hook)

        # 验证点数量影响
        if len(verification_points) > 5:
            base_rate -= 0.05

        # 确保在合理范围
        success_rate = max(0.3, min(0.95, base_rate))

        # 生成策略描述
        strategies = []
        if shell_type != "none":
            strategies.append(f"脱壳 ({shell_type})")
        if verification_points:
            java_points = [p for p in verification_points if p.type == "java"]
            sp_points = [p for p in verification_points if p.type == "shared_prefs"]
            if java_points:
                strategies.append(f"Java Hook ({len(java_points)} 个验证点)")
            if sp_points:
                strategies.append(f"SharedPrefs 伪造 ({len(sp_points)} 个)")

        strategy = " → ".join(strategies) if strategies else "直接修改"

        return strategy, success_rate

    def print_report(self) -> None:
        """打印分析报告."""
        if not self._report:
            self.full_analysis()

        report = self._report
        if not report:
            print("分析失败")
            return

        print("=" * 60)
        print("APK 深度分析报告")
        print("=" * 60)
        print(f"包名: {report.package_name}")
        print(f"版本: {report.version or 'unknown'}")
        print(f"SDK: min={report.min_sdk or 'unknown'}, target={report.target_sdk or 'unknown'}")
        print()
        print("保护措施:")
        print(f"  壳: {report.shell_type}")
        print(f"  混淆: {report.obfuscator}")
        print(f"  反调试: {', '.join(report.anti_debug) or '无'}")
        print(f"  反 Hook: {', '.join(report.anti_hook) or '无'}")
        print(f"  Root 检测: {', '.join(report.root_detection) or '无'}")
        print()
        print(f"验证点 ({len(report.verification_points)} 个):")
        for i, vp in enumerate(report.verification_points[:10], 1):
            print(f"  {i}. [{vp.type}] {vp.class_name}")
            if vp.method_name:
                print(f"     方法: {vp.method_name}")
            print(f"     策略: {vp.suggested_strategy}")
        if len(report.verification_points) > 10:
            print(f"  ... 还有 {len(report.verification_points) - 10} 个")
        print()
        print(f"建议策略: {report.suggested_strategy}")
        print(f"预估成功率: {report.success_rate_estimate:.0%}")
        print("=" * 60)


__all__ = ["APKAnalyzer", "NativeLibInfo"]
