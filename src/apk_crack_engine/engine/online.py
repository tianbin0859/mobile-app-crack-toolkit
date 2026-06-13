"""在线 Frida 引擎."""

import time
from typing import Optional
from apk_crack_engine.core.models import CrackResult
from apk_crack_engine.core.logger import logger
from apk_crack_engine.core.exceptions import CrackFailedError
from apk_crack_engine.engine.base import CrackEngine
from apk_crack_engine.utils.frida_utils import FRIDA_AVAILABLE
from apk_crack_engine.utils.adb import adb
from apk_crack_engine.hooking.vip import VIPHook
from apk_crack_engine.hooking.network import NetworkBypassHook
from apk_crack_engine.hooking.lua import LuaExtractor
from apk_crack_engine.hooking.anti_detect import AntiDetectHook


class OnlineEngine(CrackEngine):
    """在线 Frida 注入引擎."""

    @property
    def name(self) -> str:
        return "frida_hook"

    @property
    def success_rate(self) -> float:
        return 0.90

    def is_available(self) -> bool:
        """检查是否可用 (需要 Frida + 设备连接)."""
        if not FRIDA_AVAILABLE:
            return False
        if not adb.is_device_connected():
            return False
        return True

    def crack(self, mode: str = "vip") -> CrackResult:
        """执行在线破解.

        Args:
            mode: 破解模式 (vip/network/lua/anti_detect)

        Returns:
            破解结果
        """
        start = time.time()
        logger.info(f"开始在线破解: {self.package_name} (模式: {mode})")

        try:
            # 确保 frida-server 运行
            if not adb.is_frida_server_running():
                logger.info("启动 frida-server...")
                adb.start_frida_server()
                time.sleep(2)

            # 根据模式选择 Hook
            if mode == "vip":
                hook = VIPHook(self.package_name)
            elif mode == "network":
                hook = NetworkBypassHook(self.package_name)
            elif mode == "lua":
                hook = LuaExtractor(self.package_name)
            elif mode == "anti_detect":
                hook = AntiDetectHook(self.package_name)
            else:
                raise CrackFailedError(f"未知破解模式: {mode}")

            success = hook.run()
            duration = time.time() - start

            if success:
                logger.info(f"在线破解成功: {self.package_name}")
                return CrackResult(
                    success=True,
                    method=f"{self.name}_{mode}",
                    duration=duration,
                )
            else:
                raise CrackFailedError("Hook 注入失败")

        except Exception as e:
            duration = time.time() - start
            logger.error(f"在线破解失败: {e}")
            return CrackResult(
                success=False,
                method=self.name,
                duration=duration,
                error=str(e),
            )


__all__ = ["OnlineEngine"]
