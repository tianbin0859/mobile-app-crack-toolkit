"""授权管理模块."""

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from apk_crack_engine.core.config import settings
from apk_crack_engine.core.logger import logger


class LicenseCrypto:
    """授权加密工具."""

    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or settings.license_secret_key or "default_secret"
        self._fernet = self._create_fernet()

    def _create_fernet(self) -> Fernet:
        """创建 Fernet 实例."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"apk_crack_engine_salt",
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.secret_key.encode()))
        return Fernet(key)

    def encrypt(self, data: Dict[str, Any]) -> str:
        """加密数据.

        Args:
            data: 数据字典

        Returns:
            加密字符串
        """
        json_str = json.dumps(data, ensure_ascii=False)
        return self._fernet.encrypt(json_str.encode()).decode()

    def decrypt(self, token: str) -> Optional[Dict[str, Any]]:
        """解密数据.

        Args:
            token: 加密字符串

        Returns:
            数据字典, 失败返回 None
        """
        try:
            decrypted = self._fernet.decrypt(token.encode())
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.warning(f"解密失败: {e}")
            return None


class LicenseGenerator:
    """卡密生成器."""

    def __init__(self, secret_key: Optional[str] = None):
        self.crypto = LicenseCrypto(secret_key)

    def generate(self, days: int = 30, machine_bind: bool = True,
                 device_id: Optional[str] = None) -> str:
        """生成卡密.

        Args:
            days: 有效天数
            machine_bind: 是否绑定机器
            device_id: 设备ID

        Returns:
            卡密字符串
        """
        expires = datetime.now() + timedelta(days=days)
        data = {
            "type": "license",
            "created_at": datetime.now().isoformat(),
            "expires_at": expires.isoformat(),
            "machine_bind": machine_bind,
            "device_id": device_id,
            "nonce": secrets.token_hex(8),
        }
        token = self.crypto.encrypt(data)
        # 格式化: ACE-XXXX-XXXX-XXXX
        formatted = self._format_token(token)
        logger.info(f"生成卡密: {formatted} (有效期 {days} 天)")
        return formatted

    def generate_batch(self, count: int, days: int = 30,
                       machine_bind: bool = True) -> list:
        """批量生成卡密.

        Args:
            count: 数量
            days: 有效天数
            machine_bind: 是否绑定机器

        Returns:
            卡密列表
        """
        licenses = []
        for _ in range(count):
            licenses.append(self.generate(days, machine_bind))
        logger.info(f"批量生成 {count} 个卡密")
        return licenses

    def _format_token(self, token: str) -> str:
        """格式化卡密.

        Args:
            token: 原始 token

        Returns:
            格式化后的卡密
        """
        # 使用 Base32 编码便于输入
        import base64
        b32 = base64.b32encode(token.encode()).decode()
        # 分组: ACE-XXXX-XXXX-XXXX
        parts = [b32[i:i+4] for i in range(0, min(24, len(b32)), 4)]
        return "ACE-" + "-".join(parts[:4])


class LicenseValidator:
    """卡密验证器."""

    def __init__(self, secret_key: Optional[str] = None):
        self.crypto = LicenseCrypto(secret_key)
        self._used_licenses: set = set()
        self._device_bindings: Dict[str, str] = {}  # device_id -> license

    def validate(self, license_key: str, device_id: Optional[str] = None) -> Dict[str, Any]:
        """验证卡密.

        Args:
            license_key: 卡密
            device_id: 设备ID

        Returns:
            验证结果
        """
        # 解析卡密
        raw = license_key.replace("ACE-", "").replace("-", "")
        try:
            import base64
            token = base64.b32decode(raw.encode()).decode()
        except Exception:
            return {"valid": False, "message": "卡密格式错误"}

        data = self.crypto.decrypt(token)
        if not data:
            return {"valid": False, "message": "卡密无效或已损坏"}

        # 检查是否已使用
        if token in self._used_licenses:
            # 检查是否是同一设备
            if device_id and data.get("device_id") == device_id:
                return {"valid": True, "message": "卡密已激活 (同一设备)"}
            return {"valid": False, "message": "卡密已被其他设备使用"}

        # 检查过期时间
        expires = datetime.fromisoformat(data["expires_at"])
        if datetime.now() > expires:
            return {"valid": False, "message": "卡密已过期"}

        # 检查机器绑定
        if data.get("machine_bind") and device_id:
            if data.get("device_id") and data["device_id"] != device_id:
                return {"valid": False, "message": "卡密已绑定其他设备"}
            # 绑定设备
            data["device_id"] = device_id

        # 标记已使用
        self._used_licenses.add(token)
        if device_id:
            self._device_bindings[device_id] = token

        remaining = expires - datetime.now()
        return {
            "valid": True,
            "message": f"授权有效 | 剩余: {remaining.days} 天",
            "expires_at": data["expires_at"],
            "device_id": device_id,
        }

    def get_info(self, license_key: str) -> Optional[Dict[str, Any]]:
        """获取卡密信息 (不验证).

        Args:
            license_key: 卡密

        Returns:
            卡密信息
        """
        raw = license_key.replace("ACE-", "").replace("-", "")
        try:
            import base64
            token = base64.b32decode(raw.encode()).decode()
            return self.crypto.decrypt(token)
        except Exception:
            return None


__all__ = ["LicenseCrypto", "LicenseGenerator", "LicenseValidator"]
