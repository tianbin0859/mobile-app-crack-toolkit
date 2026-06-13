"""离线修改引擎."""

import time
from pathlib import Path
from typing import Optional
from apk_crack_engine.core.models import CrackResult
from apk_crack_engine.core.config import settings
from apk_crack_engine.core.logger import logger
from apk_crack_engine.core.exceptions import CrackFailedError
from apk_crack_engine.engine.base import CrackEngine
from apk_crack_engine.utils.apk_utils import apk_utils
from apk_crack_engine.patching.smali import SmaliPatcher
from apk_crack_engine.patching.manifest import ManifestPatcher
from apk_crack_engine.patching.resources import ResourcePatcher
from apk_crack_engine.patching.repack import Repacker


class OfflineEngine(CrackEngine):
    """离线 APK 修改引擎."""

    @property
    def name(self) -> str:
        return "offline_patch"

    @property
    def success_rate(self) -> float:
        return 0.80

    def is_available(self) -> bool:
        """检查是否可用 (需要 apktool + java)."""
        import shutil
        return shutil.which("apktool") is not None and shutil.which("java") is not None

    def crack(self) -> CrackResult:
        """执行离线破解.

        Returns:
            破解结果
        """
        start = time.time()
        logger.info(f"开始离线破解: {self.package_name}")

        try:
            # 1. 获取 APK
            apk_path = self._get_apk()

            # 2. 反编译
            decoded_dir = apk_utils.decode_apk(apk_path)

            # 3. Patch Smali
            patcher = SmaliPatcher(decoded_dir / "smali")
            patcher.patch_all_vip_methods()
            patcher.patch_all_expired_methods()
            patcher.patch_all_user_type_methods("premium")

            # 4. Patch Manifest
            manifest = ManifestPatcher(decoded_dir)
            manifest.enable_debuggable()
            manifest.remove_network_security_config()

            # 5. Patch Resources
            resources = ResourcePatcher(decoded_dir)
            resources.patch_vip_strings()

            # 6. 重打包+签名
            repacker = Repacker()
            output_apk = settings.work_dir / f"{self.package_name}_cracked.apk"
            final_apk = repacker.full_repack(decoded_dir, output_apk)

            duration = time.time() - start
            logger.info(f"离线破解完成: {final_apk}")

            return CrackResult(
                success=True,
                method=self.name,
                duration=duration,
                output_path=str(final_apk),
            )

        except Exception as e:
            duration = time.time() - start
            logger.error(f"离线破解失败: {e}")
            return CrackResult(
                success=False,
                method=self.name,
                duration=duration,
                error=str(e),
            )

    def _get_apk(self) -> Path:
        """获取 APK 文件.

        Returns:
            APK 路径
        """
        if self.apk_path:
            apk = Path(self.apk_path)
            if apk.exists():
                return apk

        # 尝试从设备拉取
        try:
            return apk_utils.pull_apk(self.package_name)
        except Exception as e:
            raise CrackFailedError(f"无法获取 APK: {e}")


__all__ = ["OfflineEngine"]
