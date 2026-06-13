"""ADB 封装工具, 统一所有 ADB 调用."""

import shutil
import subprocess
from typing import List, Optional, Tuple
from apk_crack_engine.core.config import settings
from apk_crack_engine.core.exceptions import ADBError
from apk_crack_engine.core.logger import logger


class ADBClient:
    """ADB 客户端封装."""

    def __init__(self) -> None:
        self.executable = settings.adb_executable
        self.timeout = settings.adb_timeout
        self.retries = settings.adb_retries
        self._check_executable()

    def _check_executable(self) -> None:
        """检查 ADB 可执行文件."""
        if not shutil.which(self.executable):
            raise ADBError(f"ADB 未安装或未在 PATH 中: {self.executable}")

    def _run(self, args: List[str], timeout: Optional[int] = None) -> subprocess.CompletedProcess:
        """执行 ADB 命令, 带重试机制."""
        cmd = [self.executable] + args
        timeout = timeout or self.timeout
        last_error: Optional[Exception] = None

        for attempt in range(self.retries):
            try:
                logger.debug(f"ADB 执行: {' '.join(cmd)} (尝试 {attempt + 1}/{self.retries})")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                if result.returncode == 0:
                    return result
                # 某些错误不需要重试
                if "device unauthorized" in result.stderr.lower():
                    raise ADBError("设备未授权, 请确认 USB 调试授权弹窗")
                if "no devices" in result.stderr.lower():
                    raise ADBError("无设备连接")
                last_error = ADBError(f"ADB 命令失败: {result.stderr}")
            except subprocess.TimeoutExpired:
                last_error = ADBError(f"ADB 命令超时 ({timeout}s)")
                logger.warning(f"ADB 超时, 重试... ({attempt + 1}/{self.retries})")
            except Exception as e:
                last_error = e
                logger.warning(f"ADB 错误: {e}, 重试... ({attempt + 1}/{self.retries})")

        raise last_error or ADBError("ADB 命令失败, 重试已耗尽")

    def devices(self) -> List[Tuple[str, str]]:
        """获取已连接设备列表.

        Returns:
            设备列表, 每项为 (device_id, status)
        """
        result = self._run(["devices"])
        devices = []
        for line in result.stdout.strip().split("\n")[1:]:
            if line.strip() and "\t" in line:
                device_id, status = line.split("\t", 1)
                devices.append((device_id.strip(), status.strip()))
        return devices

    def is_device_connected(self) -> bool:
        """检查是否有设备连接."""
        devices = self.devices()
        return any(status == "device" for _, status in devices)

    def shell(self, command: str, timeout: Optional[int] = None) -> str:
        """执行 shell 命令.

        Args:
            command: shell 命令
            timeout: 超时时间

        Returns:
            命令输出
        """
        result = self._run(["shell", command], timeout=timeout)
        return result.stdout

    def pull(self, remote_path: str, local_path: str, timeout: Optional[int] = None) -> None:
        """从设备拉取文件.

        Args:
            remote_path: 设备端路径
            local_path: 本地路径
            timeout: 超时时间
        """
        self._run(["pull", remote_path, local_path], timeout=timeout)
        logger.info(f"拉取文件: {remote_path} -> {local_path}")

    def push(self, local_path: str, remote_path: str, timeout: Optional[int] = None) -> None:
        """推送文件到设备.

        Args:
            local_path: 本地路径
            remote_path: 设备端路径
            timeout: 超时时间
        """
        self._run(["push", local_path, remote_path], timeout=timeout)
        logger.info(f"推送文件: {local_path} -> {remote_path}")

    def install(self, apk_path: str, timeout: Optional[int] = None) -> None:
        """安装 APK.

        Args:
            apk_path: APK 路径
            timeout: 超时时间
        """
        self._run(["install", apk_path], timeout=timeout)
        logger.info(f"安装 APK: {apk_path}")

    def pm_path(self, package_name: str) -> Optional[str]:
        """获取应用 APK 路径.

        Args:
            package_name: 包名

        Returns:
            APK 路径, 未找到返回 None
        """
        result = self._run(["shell", f"pm path {package_name}"])
        if "package:" in result.stdout:
            return result.stdout.replace("package:", "").strip()
        return None

    def dumpsys_package(self, package_name: str) -> str:
        """获取应用信息.

        Args:
            package_name: 包名

        Returns:
            dumpsys 输出
        """
        return self.shell(f"dumpsys package {package_name}")

    def ps(self, grep: Optional[str] = None) -> str:
        """获取进程列表.

        Args:
            grep: 过滤字符串

        Returns:
            进程列表
        """
        cmd = "ps"
        if grep:
            cmd += f" | grep {grep}"
        return self.shell(cmd)

    def is_frida_server_running(self) -> bool:
        """检查 frida-server 是否运行."""
        result = self.ps("frida-server")
        return "frida-server" in result

    def start_frida_server(self) -> None:
        """启动 frida-server."""
        path = settings.frida_server_path
        self.shell(f"{path} &")
        logger.info(f"启动 frida-server: {path}")

    def connect(self, ip: str, port: int = 5555) -> bool:
        """连接远程设备 (云手机).

        Args:
            ip: IP 地址
            port: 端口

        Returns:
            是否连接成功
        """
        result = self._run(["connect", f"{ip}:{port}"])
        success = "connected" in result.stdout or "already connected" in result.stdout
        if success:
            logger.info(f"连接云手机成功: {ip}:{port}")
        else:
            logger.warning(f"连接云手机失败: {result.stderr}")
        return success

    def disconnect(self, ip: str, port: int = 5555) -> None:
        """断开远程设备.

        Args:
            ip: IP 地址
            port: 端口
        """
        self._run(["disconnect", f"{ip}:{port}"])
        logger.info(f"断开云手机: {ip}:{port}")


# 全局 ADB 客户端实例
adb = ADBClient()

__all__ = ["ADBClient", "adb"]
