"""核心数据模型."""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum
from datetime import datetime


class CrackStatus(Enum):
    """破解状态."""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    PENDING = "pending"


class IntegrityLevel(Enum):
    """完整性等级."""

    COMPLETE = "complete"  # 90-100
    MOSTLY_COMPLETE = "mostly_complete"  # 70-89
    PARTIAL = "partial"  # 50-69
    INCOMPLETE = "incomplete"  # 0-49


@dataclass
class CrackResult:
    """破解结果."""

    success: bool
    method: str
    duration: float
    error: Optional[str] = None
    output_path: Optional[str] = None
    status: CrackStatus = CrackStatus.PENDING


@dataclass
class VerificationPoint:
    """验证点."""

    type: str  # java, native, network, shared_prefs
    class_name: Optional[str] = None
    method_name: Optional[str] = None
    description: str = ""
    suggested_strategy: str = ""


@dataclass
class AnalysisReport:
    """分析报告."""

    package_name: str
    version: Optional[str] = None
    min_sdk: Optional[int] = None
    target_sdk: Optional[int] = None
    shell_type: str = "none"
    obfuscator: str = "none"
    anti_debug: List[str] = field(default_factory=list)
    anti_hook: List[str] = field(default_factory=list)
    root_detection: List[str] = field(default_factory=list)
    verification_points: List[VerificationPoint] = field(default_factory=list)
    suggested_strategy: str = ""
    success_rate_estimate: float = 0.0


@dataclass
class IntegrityCheckResult:
    """完整性检查结果."""

    check_name: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "normal"  # normal, critical, minor


@dataclass
class CrackReport:
    """完整破解报告."""

    package_name: str
    timestamp: datetime = field(default_factory=datetime.now)
    result: Optional[CrackResult] = None
    analysis: Optional[AnalysisReport] = None
    integrity_score: int = 0
    integrity_level: IntegrityLevel = IntegrityLevel.INCOMPLETE
    integrity_checks: List[IntegrityCheckResult] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典."""
        return {
            "package_name": self.package_name,
            "timestamp": self.timestamp.isoformat(),
            "result": {
                "success": self.result.success if self.result else False,
                "method": self.result.method if self.result else "",
                "duration": self.result.duration if self.result else 0,
                "error": self.result.error if self.result else None,
                "output_path": self.result.output_path if self.result else None,
            },
            "integrity_score": self.integrity_score,
            "integrity_level": self.integrity_level.value,
            "recommendation": self.recommendation,
        }
