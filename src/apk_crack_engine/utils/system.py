"""系统检测工具."""

import shutil
import sys
from typing import Dict, List
from apk_crack_engine.core.logger import logger


class SystemChecker:
    """系统环境检测器."""

    # 需要检测的工具列表
    REQUIRED_TOOLS = [
        "adb",
        "java",
        "apktool",
    ]

    OPTIONAL_TOOLS = [
        "apksigner",
        "keytool",
        "python3",
        "pip3",
    ]

    def check_all(self) -> Dict[str, dict]:
        """检测所有工具.

        Returns:
            检测结果字典
        """
        results = {}
        for tool in self.REQUIRED_TOOLS:
            results[tool] = self._check_tool(tool, required=True)
        for tool in self.OPTIONAL_TOOLS:
            results[tool] = self._check_tool(tool, required=False)
        return results

    def _check_tool(self, name: str, required: bool = False) -> dict:
        """检测单个工具.

        Args:
            name: 工具名
            required: 是否必需

        Returns:
            检测结果
        """
        path = shutil.which(name)
        result = {
            "name": name,
            "installed": path is not None,
            "path": path,
            "required": required,
        }

        if path:
            logger.info(f"✓ {name}: {path}")
        else:
            level = "error" if required else "warning"
            getattr(logger, level)(f"✗ {name}: 未安装{' (必需)' if required else ''}")

        return result

    def get_missing_required(self) -> List[str]:
        """获取未安装的必需工具.

        Returns:
            未安装的工具列表
        """
        results = self.check_all()
        return [name for name, info in results.items()
                if info["required"] and not info["installed"]]

    def is_ready(self) -> bool:
        """检查环境是否就绪.

        Returns:
            是否所有必需工具都已安装
        """
        return len(self.get_missing_required()) == 0

    def print_report(self) -> None:
        """打印环境检测报告."""
        results = self.check_all()
        print("=" * 50)
        print("环境检测报告")
        print("=" * 50)

        for name, info in results.items():
            status = "✓" if info["installed"] else "✗"
            req = " [必需]" if info["required"] else ""
            print(f"{status} {name}{req}: {info['path'] or '未安装'}")

        missing = self.get_missing_required()
        if missing:
            print(f"\n⚠️ 缺少必需工具: {', '.join(missing)}")
        else:
            print("\n✅ 环境就绪")
        print("=" * 50)


def check_python_version() -> bool:
    """检查 Python 版本.

    Returns:
        是否满足最低要求 (>=3.9)
    """
    version = sys.version_info
    if version < (3, 9):
        logger.error(f"Python 版本过低: {version.major}.{version.minor}, 需要 >= 3.9")
        return False
    logger.info(f"Python 版本: {version.major}.{version.minor}.{version.micro}")
    return True


# 全局检测器实例
checker = SystemChecker()

__all__ = ["SystemChecker", "checker", "check_python_version"]
