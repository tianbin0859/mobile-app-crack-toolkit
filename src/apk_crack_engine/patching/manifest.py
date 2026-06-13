"""Manifest 修改模块."""

import re
from pathlib import Path
from typing import Optional
from apk_crack_engine.core.logger import logger


class ManifestPatcher:
    """AndroidManifest.xml 修改器."""

    def __init__(self, decoded_dir: Path) -> None:
        self.decoded_dir = decoded_dir
        self.manifest_path = decoded_dir / "AndroidManifest.xml"

    def enable_debuggable(self) -> bool:
        """启用调试模式.

        Returns:
            是否成功
        """
        if not self.manifest_path.exists():
            return False

        try:
            content = self.manifest_path.read_text(encoding="utf-8")
            content = content.replace(
                'android:debuggable="false"',
                'android:debuggable="true"'
            )
            # 如果没有 debuggable 属性, 添加
            if 'android:debuggable' not in content:
                content = content.replace(
                    '<application',
                    '<application android:debuggable="true"'
                )

            self.manifest_path.write_text(content, encoding="utf-8")
            logger.info("已启用调试模式")
            return True
        except Exception as e:
            logger.warning(f"启用调试模式失败: {e}")
            return False

    def remove_network_security_config(self) -> bool:
        """移除网络安全配置.

        Returns:
            是否成功
        """
        if not self.manifest_path.exists():
            return False

        try:
            content = self.manifest_path.read_text(encoding="utf-8")
            content = re.sub(
                r'android:networkSecurityConfig="@xml/[^"]+"',
                '',
                content
            )
            self.manifest_path.write_text(content, encoding="utf-8")
            logger.info("已移除网络安全配置")
            return True
        except Exception as e:
            logger.warning(f"移除网络安全配置失败: {e}")
            return False

    def change_package_name(self, new_package: str) -> Optional[str]:
        """修改包名.

        Args:
            new_package: 新包名

        Returns:
            旧包名, 失败返回 None
        """
        if not self.manifest_path.exists():
            return None

        try:
            content = self.manifest_path.read_text(encoding="utf-8")
            match = re.search(r'package="([^"]+)"', content)
            if not match:
                return None

            old_package = match.group(1)
            content = content.replace(
                f'package="{old_package}"',
                f'package="{new_package}"'
            )
            self.manifest_path.write_text(content, encoding="utf-8")
            logger.info(f"包名已修改: {old_package} -> {new_package}")
            return old_package
        except Exception as e:
            logger.warning(f"修改包名失败: {e}")
            return None

    def remove_ad_permissions(self) -> int:
        """移除广告相关权限.

        Returns:
            移除的权限数
        """
        if not self.manifest_path.exists():
            return 0

        ad_permissions = [
            "android.permission.ACCESS_ADSERVICES",
            "com.google.android.gms.permission.AD_ID",
        ]

        try:
            content = self.manifest_path.read_text(encoding="utf-8")
            original = content
            for perm in ad_permissions:
                content = re.sub(
                    rf'<uses-permission[^>]*\s+android:name="{re.escape(perm)}"[^>]*/>\s*',
                    '',
                    content
                )

            if content != original:
                self.manifest_path.write_text(content, encoding="utf-8")
                count = original.count("uses-permission") - content.count("uses-permission")
                logger.info(f"移除 {count} 个广告权限")
                return max(0, count)
        except Exception as e:
            logger.warning(f"移除广告权限失败: {e}")

        return 0

    def add_permission(self, permission: str) -> bool:
        """添加权限.

        Args:
            permission: 权限名

        Returns:
            是否成功
        """
        if not self.manifest_path.exists():
            return False

        try:
            content = self.manifest_path.read_text(encoding="utf-8")
            if permission in content:
                return True  # 已存在

            # 在 </manifest> 前添加
            perm_line = f'    <uses-permission android:name="{permission}" />\n'
            content = content.replace("</manifest>", perm_line + "</manifest>")
            self.manifest_path.write_text(content, encoding="utf-8")
            logger.info(f"添加权限: {permission}")
            return True
        except Exception as e:
            logger.warning(f"添加权限失败: {e}")
            return False


__all__ = ["ManifestPatcher"]
