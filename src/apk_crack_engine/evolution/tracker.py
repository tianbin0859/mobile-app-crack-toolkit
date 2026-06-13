"""自进化追踪模块."""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from apk_crack_engine.core.config import settings
from apk_crack_engine.core.logger import logger


class EvolutionTracker:
    """自进化追踪器."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or settings.evo_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.data_file = self.data_dir / "sessions.jsonl"
        self.stats_file = self.data_dir / "stats.json"
        self.rules_file = self.data_dir / "rules.json"
        self._ensure_files()

    def _ensure_files(self) -> None:
        """确保文件存在."""
        for f in [self.data_file]:
            if not f.exists():
                f.touch()
        for f in [self.stats_file, self.rules_file]:
            if not f.exists():
                f.write_text("{}")

    def record_session(self, apk_name: str, module: str, success: bool,
                       duration: float, method_used: str, errors: List[str],
                       notes: str = "") -> None:
        """记录破解会话.

        Args:
            apk_name: APK 名称
            module: 模块
            success: 是否成功
            duration: 耗时
            method_used: 使用的方法
            errors: 错误列表
            notes: 备注
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "apk_name": apk_name,
            "module": module,
            "success": success,
            "duration": duration,
            "method_used": method_used,
            "errors": errors,
            "notes": notes,
        }
        with open(self.data_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.debug(f"记录会话: {apk_name} ({module}) - {'成功' if success else '失败'}")

    def analyze(self) -> Dict[str, Any]:
        """分析历史数据.

        Returns:
            分析结果
        """
        if not self.data_file.exists():
            return {}

        sessions = []
        with open(self.data_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        sessions.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        if not sessions:
            return {}

        total = len(sessions)
        successes = sum(1 for s in sessions if s.get("success"))
        success_rate = successes / total if total > 0 else 0
        durations = [s.get("duration", 30) for s in sessions]
        avg_duration = sum(durations) / len(durations) if durations else 0

        # 按模块统计
        module_stats: Dict[str, Dict[str, int]] = {}
        for s in sessions:
            mod = s.get("module", "unknown")
            if mod not in module_stats:
                module_stats[mod] = {"total": 0, "success": 0}
            module_stats[mod]["total"] += 1
            if s.get("success"):
                module_stats[mod]["success"] += 1

        return {
            "total_sessions": total,
            "success_rate": round(success_rate, 2),
            "avg_duration_sec": round(avg_duration, 2),
            "module_stats": module_stats,
            "recent_sessions": len(sessions[-10:]),
        }

    def minibatch_reflect(self, batch_size: int = 5) -> List[Dict[str, Any]]:
        """批量反思.

        Args:
            batch_size: 批次大小

        Returns:
            反思结果列表
        """
        if not self.data_file.exists():
            return []

        sessions = []
        with open(self.data_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        sessions.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        if len(sessions) < batch_size:
            return []

        recent = sessions[-batch_size:]
        reflections = []

        # 分析错误模式
        error_patterns: Dict[str, int] = {}
        for s in recent:
            for e in s.get("errors", []):
                error_type = e.split(":")[0] if ":" in e else e[:30]
                error_patterns[error_type] = error_patterns.get(error_type, 0) + 1

        for error_type, count in sorted(error_patterns.items(), key=lambda x: -x[1]):
            if count >= 2:
                reflections.append({
                    "type": "error_pattern",
                    "pattern": error_type,
                    "frequency": count,
                    "suggestion": f"针对 '{error_type}' 添加防御处理",
                    "priority": "high" if count >= 3 else "medium",
                })

        # 成功率趋势
        success_count = sum(1 for s in recent if s.get("success"))
        success_rate = success_count / len(recent)
        if success_rate < 0.5:
            reflections.append({
                "type": "success_regression",
                "success_rate": round(success_rate, 2),
                "suggestion": "成功率下降，建议尝试替代方案",
                "priority": "high",
            })

        return reflections

    def should_evolve(self, threshold: int = 10) -> bool:
        """判断是否触发进化.

        Args:
            threshold: 会话阈值

        Returns:
            是否触发
        """
        stats = self.analyze()
        return stats.get("total_sessions", 0) >= threshold

    def optimize_rules(self) -> Dict[str, Any]:
        """优化规则.

        Returns:
            优化后的规则
        """
        stats = self.analyze()
        if not stats:
            return {}

        changes = []

        # 成功率过低
        if stats.get("success_rate", 0) < 0.5:
            changes.append({
                "field": "default_method",
                "old": "frida",
                "new": "multi",
                "reason": f"成功率 {stats['success_rate']:.0%} 过低",
            })

        # 耗时过长
        if stats.get("avg_duration_sec", 30) > 300:
            changes.append({
                "field": "timeout_default",
                "old": 300,
                "new": 180,
                "reason": f"平均耗时 {stats['avg_duration_sec']:.1f}s",
            })

        rules = {
            "default_method": "frida",
            "timeout_default": 300,
            "changes": changes,
            "last_updated": datetime.now().isoformat(),
        }

        with open(self.rules_file, "w", encoding="utf-8") as f:
            json.dump(rules, f, indent=2, ensure_ascii=False)

        return rules

    def get_rules(self) -> Dict[str, Any]:
        """获取当前规则.

        Returns:
            规则字典
        """
        if self.rules_file.exists():
            with open(self.rules_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return self.optimize_rules()


__all__ = ["EvolutionTracker"]
