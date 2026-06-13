"""引擎基类."""

from abc import ABC, abstractmethod
from typing import Optional
from apk_crack_engine.core.models import CrackResult


class CrackEngine(ABC):
    """破解引擎抽象基类."""

    def __init__(self, package_name: str, apk_path: Optional[str] = None) -> None:
        self.package_name = package_name
        self.apk_path = apk_path

    @abstractmethod
    def crack(self) -> CrackResult:
        """执行破解.

        Returns:
            破解结果
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查引擎是否可用.

        Returns:
            是否可用
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """引擎名称."""
        pass

    @property
    @abstractmethod
    def success_rate(self) -> float:
        """预估成功率."""
        pass


__all__ = ["CrackEngine"]
