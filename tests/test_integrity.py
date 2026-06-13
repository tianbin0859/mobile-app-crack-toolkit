"""测试完整性校验模块."""

import pytest
import tempfile
from pathlib import Path
from apk_crack_engine.integrity.checker import IntegrityChecker, CheckStatus, check_integrity


def test_integrity_nonexistent_file():
    """测试不存在的文件."""
    checker = IntegrityChecker(Path("/nonexistent/file.apk"))
    report = checker.run_all_checks()
    assert report["integrity_score"] == 0
    assert report["critical_fails"] >= 1


def test_integrity_empty_file():
    """测试空文件."""
    with tempfile.NamedTemporaryFile(suffix=".apk", delete=False) as f:
        f.write(b"")
        path = f.name

    try:
        checker = IntegrityChecker(Path(path))
        report = checker.run_all_checks()
        assert report["integrity_score"] < 50
        assert report["critical_fails"] >= 1
    finally:
        Path(path).unlink(missing_ok=True)


def test_integrity_small_file():
    """测试小文件."""
    with tempfile.NamedTemporaryFile(suffix=".apk", delete=False) as f:
        f.write(b"PK\x03\x04" + b"x" * 100)
        path = f.name

    try:
        checker = IntegrityChecker(Path(path))
        report = checker.run_all_checks()
        # 小文件应有警告
        assert report["warnings"] >= 1
    finally:
        Path(path).unlink(missing_ok=True)


def test_check_status_values():
    """测试 CheckStatus 枚举."""
    assert CheckStatus.PASS.value == "pass"
    assert CheckStatus.FAIL.value == "fail"
    assert CheckStatus.WARN.value == "warn"


def test_check_result_creation():
    """测试 CheckResult 创建."""
    from apk_crack_engine.integrity.checker import CheckResult
    result = CheckResult(
        check_name="test",
        status=CheckStatus.PASS,
        message="test message",
    )
    assert result.check_name == "test"
    assert result.status == CheckStatus.PASS
    assert result.severity == "normal"


def test_check_result_with_details():
    """测试带详情的 CheckResult."""
    from apk_crack_engine.integrity.checker import CheckResult
    result = CheckResult(
        check_name="test",
        status=CheckStatus.FAIL,
        message="failed",
        details={"key": "value"},
        severity="critical",
    )
    assert result.details["key"] == "value"
    assert result.severity == "critical"
