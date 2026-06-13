"""Frida 封装工具, 统一设备连接和脚本注入."""

import time
from typing import Optional, Callable, Any
from apk_crack_engine.core.config import settings
from apk_crack_engine.core.exceptions import FridaError
from apk_crack_engine.core.logger import logger

try:
    import frida
    FRIDA_AVAILABLE = True
except ImportError:
    FRIDA_AVAILABLE = False
    frida = None  # type: ignore


class FridaClient:
    """Frida 客户端封装."""

    def __init__(self) -> None:
        self.timeout = settings.frida_timeout
        self.retries = settings.frida_retries
        self._device: Optional[Any] = None
        self._session: Optional[Any] = None

    @property
    def is_available(self) -> bool:
        """Frida 是否可用."""
        return FRIDA_AVAILABLE

    def get_device(self) -> Any:
        """获取 USB 设备.

        Returns:
            Frida 设备对象

        Raises:
            FridaError: Frida 未安装或设备未连接
        """
        if not FRIDA_AVAILABLE:
            raise FridaError("Frida 未安装, 请运行: pip install frida-tools")

        if self._device is None:
            try:
                self._device = frida.get_usb_device(timeout=self.timeout)
                logger.info(f"连接 Frida 设备: {self._device}")
            except Exception as e:
                raise FridaError(f"连接 Frida 设备失败: {e}")

        return self._device

    def spawn(self, package_name: str) -> int:
        """启动应用.

        Args:
            package_name: 包名

        Returns:
            PID
        """
        device = self.get_device()
        try:
            pid = device.spawn([package_name])
            logger.info(f"启动应用: {package_name} (PID: {pid})")
            return pid
        except Exception as e:
            raise FridaError(f"启动应用失败: {e}")

    def attach(self, target: Any) -> Any:
        """附加到进程.

        Args:
            target: PID 或包名

        Returns:
            Frida 会话
        """
        device = self.get_device()
        try:
            session = device.attach(target)
            self._session = session
            logger.info(f"附加到: {target}")
            return session
        except Exception as e:
            raise FridaError(f"附加失败: {e}")

    def spawn_and_attach(self, package_name: str) -> Any:
        """启动并附加.

        Args:
            package_name: 包名

        Returns:
            Frida 会话
        """
        device = self.get_device()
        pid = self.spawn(package_name)
        session = device.attach(pid)
        self._session = session
        return session

    def create_script(self, session: Any, js_code: str,
                      on_message: Optional[Callable] = None) -> Any:
        """创建脚本.

        Args:
            session: Frida 会话
            js_code: JavaScript 代码
            on_message: 消息回调

        Returns:
            Frida 脚本
        """
        script = session.create_script(js_code)
        if on_message:
            script.on("message", on_message)
        return script

    def load_script(self, session: Any, js_code: str,
                    on_message: Optional[Callable] = None) -> Any:
        """加载并执行脚本.

        Args:
            session: Frida 会话
            js_code: JavaScript 代码
            on_message: 消息回调

        Returns:
            Frida 脚本
        """
        script = self.create_script(session, js_code, on_message)
        script.load()
        logger.info("Frida 脚本已加载")
        return script

    def resume(self, pid: int) -> None:
        """恢复进程.

        Args:
            pid: 进程 ID
        """
        device = self.get_device()
        device.resume(pid)
        logger.info(f"恢复进程: {pid}")

    def detach(self) -> None:
        """分离会话."""
        if self._session:
            self._session.detach()
            self._session = None
            logger.info("Frida 会话已分离")

    def run_with_retry(self, package_name: str, js_code: str,
                       on_message: Optional[Callable] = None) -> Any:
        """带重试的完整执行流程.

        Args:
            package_name: 包名
            js_code: JavaScript 代码
            on_message: 消息回调

        Returns:
            Frida 脚本
        """
        last_error: Optional[Exception] = None
        for attempt in range(self.retries):
            try:
                session = self.spawn_and_attach(package_name)
                script = self.load_script(session, js_code, on_message)
                self.resume(self.spawn(package_name))
                return script
            except Exception as e:
                last_error = e
                logger.warning(f"Frida 执行失败: {e}, 重试... ({attempt + 1}/{self.retries})")
                time.sleep(2 ** attempt)  # 指数退避

        raise FridaError(f"Frida 执行失败, 重试已耗尽: {last_error}")


# 全局 Frida 客户端实例
frida_client = FridaClient()

__all__ = ["FridaClient", "frida_client", "FRIDA_AVAILABLE"]
