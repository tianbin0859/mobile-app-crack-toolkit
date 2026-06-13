"""测试配置模块."""

import pytest
from apk_crack_engine.core.config import Settings
from apk_crack_engine.core.models import CrackResult, CrackStatus


def test_settings_default():
    """测试默认配置."""
    settings = Settings()
    assert settings.log_level == "INFO"
    assert settings.adb_timeout == 10
    assert settings.max_retries == 3


def test_crack_result():
    """测试 CrackResult 模型."""
    result = CrackResult(success=True, method="test", duration=1.0)
    assert result.success is True
    assert result.status == CrackStatus.PENDING


def test_crack_result_failed():
    """测试失败的 CrackResult."""
    result = CrackResult(
        success=False,
        method="test",
        duration=1.0,
        error="test error",
    )
    assert result.success is False
    assert result.error == "test error"
