"""测试分析模块."""

import pytest
from pathlib import Path
from apk_crack_engine.analysis.shell_detector import ShellDetector, shell_detector
from apk_crack_engine.analysis.apk_analyzer import APKAnalyzer


def test_shell_detector_known_types():
    """测试壳检测器已知类型."""
    types = shell_detector.get_all_shell_types()
    assert "360" in types
    assert "腾讯" in types
    assert "VMP" in types


def test_shell_detector_from_so():
    """测试通过 SO 文件检测壳."""
    so_files = ["libjiagu.so", "libjiagu_art.so"]
    result = shell_detector.detect_from_so(so_files)
    assert result == "360"


def test_shell_detector_none():
    """测试无壳检测."""
    so_files = ["libnormal.so", "libutils.so"]
    result = shell_detector.detect_from_so(so_files)
    assert result == "none"


def test_shell_detector_unknown():
    """测试未知壳."""
    so_files = ["libunknown_protect.so"]
    result = shell_detector.detect_from_so(so_files)
    assert result == "none"


def test_shell_info():
    """测试壳信息获取."""
    info = shell_detector.get_shell_info("360")
    assert info["known"] is True
    assert "libjiagu" in info["patterns"]


def test_shell_info_unknown():
    """测试未知壳信息."""
    info = shell_detector.get_shell_info("unknown")
    assert info["known"] is False


class TestAPKAnalyzer:
    """APKAnalyzer 测试."""

    def test_init(self):
        """测试初始化."""
        analyzer = APKAnalyzer("com.test.app")
        assert analyzer.package_name == "com.test.app"
        assert analyzer.apk_path is None

    def test_init_with_path(self):
        """测试带路径初始化."""
        path = Path("/tmp/test.apk")
        analyzer = APKAnalyzer("com.test.app", path)
        assert analyzer.apk_path == path
