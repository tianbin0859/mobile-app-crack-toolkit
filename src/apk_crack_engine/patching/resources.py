"""资源修改模块."""

import shutil
from pathlib import Path
from typing import Optional
from apk_crack_engine.core.logger import logger


class ResourcePatcher:
    """资源文件修改器."""

    def __init__(self, decoded_dir: Path) -> None:
        self.decoded_dir = decoded_dir
        self.res_dir = decoded_dir / "res"

    def change_app_name(self, new_name: str) -> bool:
        """修改应用名称.

        Args:
            new_name: 新名称

        Returns:
            是否成功
        """
        strings_path = self.res_dir / "values" / "strings.xml"
        if not strings_path.exists():
            return False

        try:
            content = strings_path.read_text(encoding="utf-8")
            content = re.sub(
                r'(<string name="app_name">)([^<]+)(</string>)',
                rf'\g<1>{new_name}\g<3>',
                content
            )
            strings_path.write_text(content, encoding="utf-8")
            logger.info(f"应用名称已修改: {new_name}")
            return True
        except Exception as e:
            logger.warning(f"修改应用名称失败: {e}")
            return False

    def replace_icon(self, icon_path: Path) -> int:
        """替换图标.

        Args:
            icon_path: 新图标路径

        Returns:
            替换的文件数
        """
        if not self.res_dir.exists() or not icon_path.exists():
            return 0

        count = 0
        for icon_file in self.res_dir.rglob("*.png"):
            if "ic_launcher" in icon_file.name or "logo" in icon_file.name:
                try:
                    shutil.copy2(icon_path, icon_file)
                    count += 1
                    logger.info(f"替换图标: {icon_file}")
                except Exception as e:
                    logger.warning(f"替换图标失败 {icon_file}: {e}")

        return count

    def patch_vip_strings(self) -> int:
        """Patch VIP 相关字符串.

        Returns:
            修改的文件数
        """
        strings_path = self.res_dir / "values" / "strings.xml"
        if not strings_path.exists():
            return 0

        replacements = [
            ("未开通", "已开通"),
            ("未激活", "已激活"),
            ("免费版", "专业版"),
            ("试用版", "正式版"),
            ("普通用户", "VIP用户"),
        ]

        try:
            content = strings_path.read_text(encoding="utf-8")
            original = content
            for old, new in replacements:
                content = content.replace(old, new)

            if content != original:
                strings_path.write_text(content, encoding="utf-8")
                logger.info("VIP 字符串已 Patch")
                return 1
        except Exception as e:
            logger.warning(f"Patch VIP 字符串失败: {e}")

        return 0


# 需要导入 re
import re  # noqa: E402

__all__ = ["ResourcePatcher"]
