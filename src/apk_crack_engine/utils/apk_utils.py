"""APK 工具函数, 统一拉取/反编译/重打包/签名."""

import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Optional, List
from apk_crack_engine.core.config import settings
from apk_crack_engine.core.exceptions import APKToolError
from apk_crack_engine.core.logger import logger
from apk_crack_engine.utils.adb import adb


class APKUtils:
    """APK 工具类."""

    def __init__(self) -> None:
        self.work_dir = settings.work_dir
        self.apktool = settings.apktool_path
        self.java = settings.java_path
        self.apksigner = settings.apksigner_path
        self._check_tools()

    def _check_tools(self) -> None:
        """检查必要工具."""
        for tool in [self.apktool, self.java]:
            if not shutil.which(tool):
                logger.warning(f"工具未安装: {tool}")

    def pull_apk(self, package_name: str, output_path: Optional[Path] = None) -> Path:
        """从设备拉取 APK.

        Args:
            package_name: 包名
            output_path: 输出路径, 默认 work_dir/{package_name}.apk

        Returns:
            APK 本地路径
        """
        if output_path is None:
            output_path = self.work_dir / f"{package_name}.apk"

        device_path = adb.pm_path(package_name)
        if not device_path:
            raise APKToolError(f"无法获取应用 APK 路径: {package_name}")

        adb.pull(device_path, str(output_path))
        return output_path

    def decode_apk(self, apk_path: Path, output_dir: Optional[Path] = None,
                   force: bool = True) -> Path:
        """反编译 APK.

        Args:
            apk_path: APK 路径
            output_dir: 输出目录
            force: 是否强制覆盖

        Returns:
            反编译目录
        """
        if output_dir is None:
            output_dir = self.work_dir / f"{apk_path.stem}_decoded"

        cmd = [self.apktool, "d", str(apk_path), "-o", str(output_dir)]
        if force:
            cmd.append("-f")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if result.returncode != 0:
                raise APKToolError(f"反编译失败: {result.stderr}")
        except subprocess.TimeoutExpired:
            raise APKToolError("反编译超时 (120s)")

        logger.info(f"反编译完成: {output_dir}")
        return output_dir

    def rebuild_apk(self, decoded_dir: Path, output_apk: Optional[Path] = None) -> Path:
        """重打包 APK.

        Args:
            decoded_dir: 反编译目录
            output_apk: 输出 APK 路径

        Returns:
            输出 APK 路径
        """
        if output_apk is None:
            output_apk = self.work_dir / f"{decoded_dir.name}_rebuilt.apk"

        cmd = [self.apktool, "b", str(decoded_dir), "-o", str(output_apk)]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if result.returncode != 0:
                raise APKToolError(f"重打包失败: {result.stderr}")
        except subprocess.TimeoutExpired:
            raise APKToolError("重打包超时 (120s)")

        logger.info(f"重打包完成: {output_apk}")
        return output_apk

    def sign_apk(self, apk_path: Path, keystore: Optional[Path] = None) -> None:
        """签名 APK.

        Args:
            apk_path: APK 路径
            keystore: 密钥库路径, 默认使用调试密钥
        """
        if keystore is None:
            keystore = self._ensure_keystore()

        cmd = [
            self.apksigner, "sign",
            "--ks", str(keystore),
            "--ks-key-alias", settings.key_alias,
            "--ks-pass", f"pass:{settings.keystore_password_safe}",
            "--key-pass", f"pass:{settings.key_password_safe}",
            str(apk_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if result.returncode != 0:
                raise APKToolError(f"签名失败: {result.stderr}")
        except subprocess.TimeoutExpired:
            raise APKToolError("签名超时 (60s)")

        # 验证签名
        verify_result = subprocess.run(
            [self.apksigner, "verify", str(apk_path)],
            capture_output=True,
            check=False,
        )
        if verify_result.returncode == 0:
            logger.info(f"APK 签名验证通过: {apk_path}")
        else:
            logger.warning(f"APK 签名验证失败: {apk_path}")

    def _ensure_keystore(self) -> Path:
        """确保调试密钥库存在.

        Returns:
            密钥库路径
        """
        keystore = settings.keystore_path
        if keystore.exists():
            return keystore

        # 生成调试密钥
        logger.info("生成调试密钥库...")
        cmd = [
            "keytool", "-genkey", "-v",
            "-keystore", str(keystore),
            "-alias", settings.key_alias,
            "-keyalg", "RSA",
            "-keysize", "2048",
            "-validity", "10000",
            "-storepass", settings.keystore_password_safe,
            "-keypass", settings.key_password_safe,
            "-dname", "CN=Android Debug,O=Android,C=US",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise APKToolError(f"生成密钥库失败: {result.stderr}")

        logger.info(f"调试密钥库已生成: {keystore}")
        return keystore

    def extract_dex(self, apk_path: Path, output_dir: Optional[Path] = None) -> List[Path]:
        """从 APK 提取 DEX 文件.

        Args:
            apk_path: APK 路径
            output_dir: 输出目录

        Returns:
            DEX 文件路径列表
        """
        if output_dir is None:
            output_dir = self.work_dir / f"{apk_path.stem}_dex"
        output_dir.mkdir(parents=True, exist_ok=True)

        dex_files = []
        with zipfile.ZipFile(apk_path, "r") as z:
            for name in z.namelist():
                if name.endswith(".dex"):
                    z.extract(name, str(output_dir))
                    dex_files.append(output_dir / name)

        logger.info(f"提取 {len(dex_files)} 个 DEX 文件到 {output_dir}")
        return dex_files

    def get_apk_info(self, apk_path: Path) -> dict:
        """获取 APK 基本信息.

        Args:
            apk_path: APK 路径

        Returns:
            基本信息字典
        """
        info = {"path": str(apk_path), "size": apk_path.stat().st_size}

        try:
            with zipfile.ZipFile(apk_path, "r") as z:
                info["file_count"] = len(z.namelist())
                info["has_manifest"] = "AndroidManifest.xml" in z.namelist()
                info["dex_count"] = sum(1 for n in z.namelist() if n.endswith(".dex"))
                info["has_native"] = any("lib/" in n for n in z.namelist())
        except zipfile.BadZipFile:
            info["error"] = "无效的 APK 文件"

        return info


# 全局 APK 工具实例
apk_utils = APKUtils()

__all__ = ["APKUtils", "apk_utils"]
