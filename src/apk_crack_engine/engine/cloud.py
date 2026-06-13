"""云手机引擎."""

import time
from typing import Optional
from apk_crack_engine.core.models import CrackResult
from apk_crack_engine.core.logger import logger
from apk_crack_engine.engine.base import CrackEngine
from apk_crack_engine.utils.adb import adb


class CloudEngine(CrackEngine):
    """云手机连接引擎."""

    def __init__(self, package_name: str, apk_path: Optional[str] = None,
                 ip: str = "", port: int = 5555) -> None:
        super().__init__(package_name, apk_path)
        self.ip = ip
        self.port = port

    @property
    def name(self) -> str:
        return "cloud_phone"

    @property
    def success_rate(self) -> float:
        return 0.85

    def is_available(self) -> bool:
        """检查云手机是否可连接."""
        if not self.ip:
            return False
        return adb.connect(self.ip, self.port)

    def crack(self) -> CrackResult:
        """执行云手机破解 (实际调用 OnlineEngine).

        Returns:
            破解结果
        """
        start = time.time()
        logger.info(f"开始云手机破解: {self.package_name} @ {self.ip}:{self.port}")

        try:
            # 连接云手机
            if not adb.connect(self.ip, self.port):
                return CrackResult(
                    success=False,
                    method=self.name,
                    duration=time.time() - start,
                    error=f"无法连接云手机 {self.ip}:{self.port}",
                )

            # 连接成功后使用在线引擎
            from apk_crack_engine.engine.online import OnlineEngine
            online = OnlineEngine(self.package_name, self.apk_path)
            result = online.crack()
            result.method = f"{self.name}_{result.method}"
            return result

        except Exception as e:
            duration = time.time() - start
            return CrackResult(
                success=False,
                method=self.name,
                duration=duration,
                error=str(e),
            )

    def disconnect(self) -> None:
        """断开云手机."""
        if self.ip:
            adb.disconnect(self.ip, self.port)


__all__ = ["CloudEngine"]
