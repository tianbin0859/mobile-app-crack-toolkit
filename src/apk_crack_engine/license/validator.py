"""授权验证模块."""

from typing import Optional, Dict, Any
from apk_crack_engine.license.generator import LicenseValidator
from apk_crack_engine.core.logger import logger


class LicenseManager:
    """授权管理器."""

    def __init__(self, secret_key: Optional[str] = None):
        self.validator = LicenseValidator(secret_key)

    def activate(self, license_key: str, device_id: Optional[str] = None) -> tuple:
        """激活卡密.

        Args:
            license_key: 卡密
            device_id: 设备ID

        Returns:
            (是否成功, 消息)
        """
        result = self.validator.validate(license_key, device_id)
        if result["valid"]:
            logger.info(f"卡密激活成功: {device_id}")
            return True, result["message"]
        else:
            logger.warning(f"卡密激活失败: {result['message']}")
            return False, result["message"]

    def verify(self, license_key: str, device_id: Optional[str] = None) -> tuple:
        """验证卡密状态.

        Args:
            license_key: 卡密
            device_id: 设备ID

        Returns:
            (是否有效, 消息)
        """
        result = self.validator.validate(license_key, device_id)
        return result["valid"], result["message"]

    def get_license_info(self, license_key: str) -> Optional[Dict[str, Any]]:
        """获取卡密信息.

        Args:
            license_key: 卡密

        Returns:
            卡密信息
        """
        return self.validator.get_info(license_key)


__all__ = ["LicenseManager"]
