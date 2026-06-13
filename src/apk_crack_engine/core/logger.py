"""loguru 日志配置, 支持轮转."""

import sys
from pathlib import Path
from loguru import logger
from apk_crack_engine.core.config import settings


def setup_logging() -> None:
    """配置日志系统."""
    # 移除默认的 stderr handler
    logger.remove()

    # 添加控制台输出
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )

    # 添加文件输出, 带轮转
    log_file = settings.log_dir / "apk_crack_engine.log"
    logger.add(
        str(log_file),
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation=f"{settings.log_max_size} MB",
        retention=settings.log_backups,
        encoding="utf-8",
        enqueue=True,  # 异步写入, 避免阻塞
        backtrace=True,
        diagnose=True,
    )

    # 添加错误日志单独文件
    error_log = settings.log_dir / "error.log"
    logger.add(
        str(error_log),
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}",
        rotation="10 MB",
        retention=5,
        encoding="utf-8",
        enqueue=True,
    )

    logger.info(f"日志系统已初始化, 日志目录: {settings.log_dir}")


# 导出配置好的 logger
__all__ = ["logger", "setup_logging"]
