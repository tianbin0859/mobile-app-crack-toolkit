"""授权服务器模块."""

from typing import Optional, Dict, Any
from datetime import datetime
from apk_crack_engine.license.generator import LicenseGenerator, LicenseValidator
from apk_crack_engine.core.logger import logger


class LicenseServer:
    """授权验证服务器."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080,
                 secret_key: Optional[str] = None):
        self.host = host
        self.port = port
        self.generator = LicenseGenerator(secret_key)
        self.validator = LicenseValidator(secret_key)
        self._stats: Dict[str, Any] = {
            "total_activations": 0,
            "total_verifications": 0,
            "licenses": {},
        }

    def activate(self, license_key: str, device_id: str) -> Dict[str, Any]:
        """激活卡密.

        Args:
            license_key: 卡密
            device_id: 设备ID

        Returns:
            激活结果
        """
        result = self.validator.validate(license_key, device_id)
        self._stats["total_activations"] += 1

        if result["valid"]:
            self._stats["licenses"][license_key] = {
                "device_id": device_id,
                "activated_at": datetime.now().isoformat(),
                "status": "active",
            }
            logger.info(f"服务器激活成功: {device_id}")

        return {
            "success": result["valid"],
            "message": result["message"],
            "timestamp": datetime.now().isoformat(),
        }

    def verify(self, license_key: str, device_id: Optional[str] = None) -> Dict[str, Any]:
        """验证卡密.

        Args:
            license_key: 卡密
            device_id: 设备ID

        Returns:
            验证结果
        """
        result = self.validator.validate(license_key, device_id)
        self._stats["total_verifications"] += 1
        return {
            "valid": result["valid"],
            "message": result["message"],
        }

    def heartbeat(self, license_key: str, device_id: str) -> Dict[str, Any]:
        """心跳检测.

        Args:
            license_key: 卡密
            device_id: 设备ID

        Returns:
            心跳结果
        """
        return self.verify(license_key, device_id)

    def disable(self, license_key: str) -> Dict[str, Any]:
        """禁用卡密.

        Args:
            license_key: 卡密

        Returns:
            操作结果
        """
        if license_key in self._stats["licenses"]:
            self._stats["licenses"][license_key]["status"] = "disabled"
            logger.info(f"卡密已禁用: {license_key}")
            return {"success": True, "message": "卡密已禁用"}
        return {"success": False, "message": "卡密不存在"}

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息.

        Returns:
            统计信息
        """
        return {
            "total_activations": self._stats["total_activations"],
            "total_verifications": self._stats["total_verifications"],
            "active_licenses": sum(
                1 for l in self._stats["licenses"].values()
                if l.get("status") == "active"
            ),
        }


__all__ = ["LicenseServer"]
