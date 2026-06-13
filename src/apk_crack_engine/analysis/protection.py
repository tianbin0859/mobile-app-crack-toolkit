"""保护分析模块."""

from typing import List, Dict
from pathlib import Path
import zipfile
import re
from apk_crack_engine.core.logger import logger


class ProtectionAnalyzer:
    """保护分析器."""

    # 网络安全配置特征
    NETWORK_SECURITY_PATTERNS = [
        r"networkSecurityConfig",
        r"cleartextTrafficPermitted",
        r"trust-anchors",
    ]

    # 加密特征
    CRYPTO_PATTERNS = [
        r"javax\.crypto",
        r"Cipher",
        r"AES",
        r"DES",
        r"RSA",
        r"MD5",
        r"SHA",
        r"Base64",
    ]

    # 反射特征
    REFLECTION_PATTERNS = [
        r"java\.lang\.reflect",
        r"getDeclaredMethod",
        r"getMethod",
        r"invoke",
        r"setAccessible",
    ]

    # 动态加载特征
    DYNAMIC_LOAD_PATTERNS = [
        r"DexClassLoader",
        r"PathClassLoader",
        r"loadClass",
        r"defineClass",
    ]

    def analyze_manifest(self, apk_path: Path) -> Dict:
        """分析 Manifest.

        Args:
            apk_path: APK 路径

        Returns:
            分析结果
        """
        result = {
            "permissions": [],
            "activities": [],
            "services": [],
            "receivers": [],
            "network_security": False,
        }

        try:
            with zipfile.ZipFile(apk_path, "r") as z:
                if "AndroidManifest.xml" not in z.namelist():
                    return result

                manifest = z.read("AndroidManifest.xml")
                # 简单的二进制 XML 字符串提取
                text = self._extract_strings(manifest)

                # 提取权限
                result["permissions"] = re.findall(
                    r'android\.permission\.[A-Z_]+', text
                )

                # 检查网络安全配置
                result["network_security"] = any(
                    p in text for p in self.NETWORK_SECURITY_PATTERNS
                )

        except Exception as e:
            logger.warning(f"Manifest 分析失败: {e}")

        return result

    def analyze_native_libs(self, apk_path: Path) -> List[Dict]:
        """分析 Native 库.

        Args:
            apk_path: APK 路径

        Returns:
            Native 库信息列表
        """
        libs = []

        try:
            with zipfile.ZipFile(apk_path, "r") as z:
                for name in z.namelist():
                    if not name.endswith(".so"):
                        continue

                    lib_info = {
                        "name": Path(name).name,
                        "path": name,
                        "abi": name.split("/")[1] if len(name.split("/")) > 1 else "unknown",
                        "crypto": False,
                        "size": z.getinfo(name).file_size,
                    }

                    # 检查加密特征
                    data = z.read(name)
                    crypto_indicators = [b"AES", b"DES", b"RSA", b"MD5", b"SHA"]
                    lib_info["crypto"] = any(ind in data for ind in crypto_indicators)

                    libs.append(lib_info)

        except Exception as e:
            logger.warning(f"Native 库分析失败: {e}")

        return libs

    def analyze_strings(self, apk_path: Path) -> Dict[str, List[str]]:
        """分析字符串.

        Args:
            apk_path: APK 路径

        Returns:
            分类的字符串列表
        """
        result = {
            "urls": [],
            "ips": [],
            "emails": [],
            "api_keys": [],
            "suspicious": [],
        }

        try:
            with zipfile.ZipFile(apk_path, "r") as z:
                for name in z.namelist():
                    if not name.endswith((".xml", ".json", ".txt", ".properties")):
                        continue

                    try:
                        content = z.read(name).decode("utf-8", errors="ignore")

                        # URL
                        urls = re.findall(r'https?://[^\s"\'<>]+', content)
                        result["urls"].extend(urls)

                        # IP
                        ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', content)
                        result["ips"].extend(ips)

                        # Email
                        emails = re.findall(r'[\w.-]+@[\w.-]+\.\w+', content)
                        result["emails"].extend(emails)

                        # API Key 模式
                        api_keys = re.findall(r'[a-zA-Z0-9_-]{20,}', content)
                        result["api_keys"].extend(api_keys)

                    except Exception:
                        pass

            # 去重
            for key in result:
                result[key] = list(set(result[key]))[:50]  # 限制数量

        except Exception as e:
            logger.warning(f"字符串分析失败: {e}")

        return result

    def _extract_strings(self, data: bytes) -> str:
        """从二进制数据提取可打印字符串.

        Args:
            data: 二进制数据

        Returns:
            提取的字符串
        """
        # 提取 ASCII 字符串
        strings = []
        current = []
        for byte in data:
            if 32 <= byte <= 126:
                current.append(chr(byte))
            else:
                if len(current) >= 4:
                    strings.append("".join(current))
                current = []
        if len(current) >= 4:
            strings.append("".join(current))

        return " ".join(strings)


__all__ = ["ProtectionAnalyzer"]
