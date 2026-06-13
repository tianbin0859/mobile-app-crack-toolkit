"""Pydantic 配置模型, 支持热重载."""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """APK Crack Engine 配置."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ACE_",
        case_sensitive=False,
        extra="ignore",
    )

    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_dir: Path = Field(default=Path.home() / ".apk_crack_engine" / "logs", description="日志目录")
    log_max_size: int = Field(default=10, description="日志文件最大大小(MB)")
    log_backups: int = Field(default=5, description="日志备份数量")

    # ADB 配置
    adb_path: Optional[str] = Field(default=None, description="ADB 可执行文件路径")
    adb_timeout: int = Field(default=10, description="ADB 默认超时(秒)")
    adb_retries: int = Field(default=3, description="ADB 重试次数")

    # Frida 配置
    frida_server_path: str = Field(default="/data/local/tmp/frida-server", description="Frida-server 路径")
    frida_timeout: int = Field(default=30, description="Frida 默认超时(秒)")
    frida_retries: int = Field(default=3, description="Frida 重试次数")

    # APK 工具配置
    apktool_path: str = Field(default="apktool", description="apktool 路径")
    java_path: str = Field(default="java", description="Java 路径")
    apksigner_path: str = Field(default="apksigner", description="apksigner 路径")
    work_dir: Path = Field(default=Path("/tmp/apk_crack_engine"), description="临时工作目录")

    # 签名配置
    keystore_path: Path = Field(default=Path("/tmp/debug.keystore"), description="密钥库路径")
    keystore_password: str = Field(default="", description="密钥库密码")
    key_alias: str = Field(default="androiddebugkey", description="密钥别名")
    key_password: str = Field(default="", description="密钥密码")

    # 网络配置
    http_timeout: int = Field(default=10, description="HTTP 请求默认超时(秒)")
    http_retries: int = Field(default=3, description="HTTP 重试次数")
    http_proxy: Optional[str] = Field(default=None, description="HTTP 代理")

    # 授权服务器配置
    license_server_url: str = Field(default="http://localhost:8080", description="授权服务器地址")
    license_server_port: int = Field(default=8080, description="授权服务器端口")
    license_secret_key: str = Field(default="", description="授权加密密钥")

    # 破解引擎配置
    max_retries: int = Field(default=3, description="最大重试次数")
    timeout_per_round: int = Field(default=300, description="每轮超时时间(秒)")
    success_threshold: float = Field(default=0.8, description="成功率阈值")
    auto_fix_env: bool = Field(default=True, description="自动修复环境")
    parallel_mode: bool = Field(default=False, description="并行批量破解模式")
    max_workers: int = Field(default=4, description="最大并行工作者数")

    # 进化追踪配置
    evo_dir: Path = Field(default=Path.home() / ".apk_crack_engine" / "evolution", description="进化数据目录")
    evo_threshold: int = Field(default=10, description="触发进化的会话阈值")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保目录存在
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.evo_dir.mkdir(parents=True, exist_ok=True)

    @property
    def adb_executable(self) -> str:
        """获取 ADB 可执行文件路径."""
        return self.adb_path or "adb"

    @property
    def keystore_password_safe(self) -> str:
        """安全获取密钥库密码, 优先环境变量."""
        # 优先从环境变量获取, 避免硬编码
        return os.environ.get("ACE_KEYSTORE_PASSWORD", self.keystore_password) or "android"

    @property
    def key_password_safe(self) -> str:
        """安全获取密钥密码."""
        return os.environ.get("ACE_KEY_PASSWORD", self.key_password) or "android"


# 全局配置实例
settings = Settings()
