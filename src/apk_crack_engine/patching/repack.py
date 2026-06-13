"""重打包和签名模块, 统一签名逻辑."""

from pathlib import Path
from typing import Optional
from apk_crack_engine.core.config import settings
from apk_crack_engine.core.exceptions import APKToolError
from apk_crack_engine.core.logger import logger
from apk_crack_engine.utils.apk_utils import apk_utils


class Repacker:
    """APK 重打包器."""

    def __init__(self) -> None:
        self.work_dir = settings.work_dir

    def repack(self, decoded_dir: Path, output_apk: Optional[Path] = None) -> Path:
        """重打包 APK.

        Args:
            decoded_dir: 反编译目录
            output_apk: 输出路径

        Returns:
            输出 APK 路径
        """
        if output_apk is None:
            output_apk = self.work_dir / f"{decoded_dir.name}_repacked.apk"

        return apk_utils.rebuild_apk(decoded_dir, output_apk)

    def sign(self, apk_path: Path, keystore: Optional[Path] = None) -> None:
        """签名 APK.

        Args:
            apk_path: APK 路径
            keystore: 密钥库路径
        """
        apk_utils.sign_apk(apk_path, keystore)

    def full_repack(self, decoded_dir: Path, output_apk: Optional[Path] = None,
                    keystore: Optional[Path] = None) -> Path:
        """完整重打包+签名.

        Args:
            decoded_dir: 反编译目录
            output_apk: 输出路径
            keystore: 密钥库路径

        Returns:
            最终 APK 路径
        """
        logger.info(f"开始重打包: {decoded_dir}")

        # 重打包
        rebuilt = self.repack(decoded_dir, output_apk)

        # 签名
        self.sign(rebuilt, keystore)

        logger.info(f"重打包完成: {rebuilt}")
        return rebuilt


__all__ = ["Repacker"]
