"""壳检测模块, 统一签名库."""

from typing import Dict, List, Optional
from pathlib import Path
import zipfile
from apk_crack_engine.core.logger import logger

# 统一壳签名库
SHELL_PATTERNS: Dict[str, List[str]] = {
    "360": ["libjiagu", "libjiagu_art", "libjiagu_a64"],
    "梆梆": ["libsecexe", "libsecmain", "libsecexe2", "libsecmain2"],
    "爱加密": ["libexec", "libexecmain", "libexec2", "libexecmain2"],
    "腾讯": ["libshell", "libtup", "libBugly", "libturing"],
    "百度": ["libbaiduprotect", "libbaiduprotect_x86"],
    "网易": ["libnesec", "libnesec_x86"],
    "阿里": ["libmobisec", "libmobisec_x86"],
    "通付盾": ["libegis", "libegis_x86"],
    "海云安": ["libchaosvmp", "libchaosvmp_x86"],
    "娜迦": ["libedog", "libedog_x86"],
    "顶像": ["libx3g", "libx3g_x86"],
    "VMP": ["libvmp", "libvmp_x86", "libvmp_arm"],
}

# 混淆器签名
OBFUSCATOR_PATTERNS: Dict[str, List[str]] = {
    "ProGuard": ["proguard", "a.a.a", "a.b.c"],
    "R8": ["r8"],
    "Allatori": ["allatori"],
    "DashO": ["dasho"],
    "Arkari": ["arkari", "obfstr"],
}


class ShellDetector:
    """壳检测器."""

    def __init__(self) -> None:
        self.shell_patterns = SHELL_PATTERNS
        self.obfuscator_patterns = OBFUSCATOR_PATTERNS

    def detect_from_so(self, so_files: List[str]) -> str:
        """通过 SO 文件名检测壳类型.

        Args:
            so_files: SO 文件名列表

        Returns:
            壳类型, 未检测到返回 "none"
        """
        for shell_name, patterns in self.shell_patterns.items():
            for so in so_files:
                for pattern in patterns:
                    if pattern in so.lower():
                        logger.info(f"检测到壳: {shell_name} (SO: {so})")
                        return shell_name
        return "none"

    def detect_from_apk(self, apk_path: Path) -> str:
        """从 APK 中检测壳类型.

        Args:
            apk_path: APK 路径

        Returns:
            壳类型
        """
        try:
            with zipfile.ZipFile(apk_path, "r") as z:
                so_files = [
                    name for name in z.namelist()
                    if name.endswith(".so") and name.startswith("lib/")
                ]
                # 提取文件名
                file_names = [Path(p).name for p in so_files]
                return self.detect_from_so(file_names)
        except Exception as e:
            logger.warning(f"APK 壳检测失败: {e}")
            return "unknown"

    def detect_obfuscator(self, smali_files: List[str]) -> str:
        """通过 Smali 文件检测混淆器.

        Args:
            smali_files: Smali 文件名列表

        Returns:
            混淆器类型
        """
        for obf_name, patterns in self.obfuscator_patterns.items():
            for smali in smali_files:
                for pattern in patterns:
                    if pattern in smali.lower():
                        return obf_name
        return "none"

    def get_all_shell_types(self) -> List[str]:
        """获取所有支持的壳类型.

        Returns:
            壳类型列表
        """
        return list(self.shell_patterns.keys())

    def get_shell_info(self, shell_type: str) -> dict:
        """获取壳类型信息.

        Args:
            shell_type: 壳类型

        Returns:
            壳信息字典
        """
        patterns = self.shell_patterns.get(shell_type, [])
        return {
            "type": shell_type,
            "patterns": patterns,
            "known": shell_type in self.shell_patterns,
        }


# 全局检测器实例
shell_detector = ShellDetector()

__all__ = ["ShellDetector", "shell_detector", "SHELL_PATTERNS", "OBFUSCATOR_PATTERNS"]
