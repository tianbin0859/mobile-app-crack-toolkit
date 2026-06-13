#!/usr/bin/env python3
"""
APK Crack Engine 自进化追踪器
L1数据收集 → L2批量反思 → L3规则优化 → L4验证门控 → Slow Update

基于微软 SkillOpt 论文设计
"""

import os
import json
from typing import List, Dict, Optional
from datetime import datetime

DEFAULT_EVO_DIR = os.path.expanduser(
    "~/.hermes/skills/software-development/apk-crack-engine/.evolution"
)

SLOW_UPDATE_START = "<!-- SLOW_UPDATE_START -->"
SLOW_UPDATE_END = "<!-- SLOW_UPDATE_END -->"


class EvolutionTracker:
    """APK Crack Engine 自进化追踪器"""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or DEFAULT_EVO_DIR
        os.makedirs(self.data_dir, exist_ok=True)

        self.data_file = os.path.join(self.data_dir, "sessions.jsonl")
        self.stats_file = os.path.join(self.data_dir, "stats.json")
        self.rules_file = os.path.join(self.data_dir, "rules.json")
        self.gate_file = os.path.join(self.data_dir, "gate_history.jsonl")
        self.slow_update_file = os.path.join(self.data_dir, "slow_update.md")
        self.rejected_buffer_file = os.path.join(self.data_dir, "rejected_buffer.jsonl")
        self._ensure_files()

    def _ensure_files(self):
        for f in [self.data_file, self.gate_file, self.rejected_buffer_file]:
            if not os.path.exists(f):
                open(f, 'a').close()
        for f in [self.stats_file, self.rules_file]:
            if not os.path.exists(f):
                with open(f, 'w') as fh:
                    json.dump({}, fh)

    # ====== L1: 数据收集 ======

    def record_session(self, apk_name: str, module: str, success: bool,
                       duration: float, method_used: str, errors: list, notes: str):
        """记录一次破解会话"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "apk_name": apk_name,
            "module": module,
            "success": success,
            "duration": duration,
            "method_used": method_used,
            "errors": errors,
            "notes": notes
        }
        with open(self.data_file, 'a') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    def record_rejected_edit(self, edit_proposal: dict):
        """记录被拒绝的编辑（负反馈记忆）"""
        record = {
            "timestamp": datetime.now().isoformat(),
            **edit_proposal
        }
        with open(self.rejected_buffer_file, 'a') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    def is_rejected_before(self, field: str, new_value) -> bool:
        """检查该修改是否曾被拒绝"""
        if not os.path.exists(self.rejected_buffer_file):
            return False
        with open(self.rejected_buffer_file, 'r') as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    if record.get('field') == field and record.get('new') == new_value:
                        return True
        return False

    # ====== L2: 批量反思 ======

    def analyze(self) -> dict:
        """分析历史破解数据"""
        if not os.path.exists(self.data_file):
            return {}

        sessions = []
        with open(self.data_file, 'r') as f:
            for line in f:
                if line.strip():
                    sessions.append(json.loads(line))

        if not sessions:
            return {}

        total = len(sessions)
        successes = sum(1 for s in sessions if s.get('success', False))
        success_rate = successes / total if total > 0 else 0
        durations = [s.get('duration', 30) for s in sessions]
        avg_duration = sum(durations) / len(durations)

        # 按模块统计
        module_stats = {}
        for s in sessions:
            mod = s.get('module', 'unknown')
            if mod not in module_stats:
                module_stats[mod] = {"total": 0, "success": 0}
            module_stats[mod]["total"] += 1
            if s.get('success'):
                module_stats[mod]["success"] += 1

        return {
            "total_sessions": total,
            "success_rate": round(success_rate, 2),
            "avg_duration_sec": round(avg_duration, 2),
            "module_stats": module_stats,
            "recent_sessions": len(sessions[-10:])
        }

    def minibatch_reflect(self, batch_size: int = 5) -> List[dict]:
        """批量反思：分析最近N次破解"""
        if not os.path.exists(self.data_file):
            return []

        sessions = []
        with open(self.data_file, 'r') as f:
            for line in f:
                if line.strip():
                    sessions.append(json.loads(line))

        if len(sessions) < batch_size:
            return []

        recent = sessions[-batch_size:]
        reflections = []

        # 分析错误模式
        error_patterns = {}
        for s in recent:
            for e in s.get('errors', []):
                error_type = e.split(':')[0] if ':' in e else e[:30]
                error_patterns[error_type] = error_patterns.get(error_type, 0) + 1

        for error_type, count in sorted(error_patterns.items(), key=lambda x: -x[1]):
            if count >= 2:
                reflections.append({
                    "type": "error_pattern",
                    "pattern": error_type,
                    "frequency": count,
                    "suggestion": f"针对 '{error_type}' 添加防御处理",
                    "priority": "high" if count >= 3 else "medium"
                })

        # 成功率趋势
        success_count = sum(1 for s in recent if s.get('success'))
        success_rate = success_count / len(recent)
        if success_rate < 0.5:
            reflections.append({
                "type": "success_regression",
                "success_rate": round(success_rate, 2),
                "suggestion": "成功率下降，建议尝试替代方案或更新工具",
                "priority": "high"
            })

        # 模块效果分析
        module_stats = {}
        for s in recent:
            mod = s.get('module', 'unknown')
            if mod not in module_stats:
                module_stats[mod] = {"total": 0, "success": 0}
            module_stats[mod]["total"] += 1
            if s.get('success'):
                module_stats[mod]["success"] += 1

        for mod, stats in module_stats.items():
            rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
            if rate < 0.3 and stats["total"] >= 2:
                reflections.append({
                    "type": "module_weakness",
                    "module": mod,
                    "success_rate": round(rate, 2),
                    "suggestion": f"模块 '{mod}' 成功率低，需要优化策略",
                    "priority": "medium"
                })

        return reflections

    def should_evolve(self, session_threshold: int = 10) -> bool:
        """判断是否触发进化"""
        stats = self.analyze()
        return stats.get('total_sessions', 0) >= session_threshold

    # ====== L3: 规则优化 ======

    def get_dynamic_budget(self) -> int:
        """学习率调度"""
        total = 0
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                for line in f:
                    if line.strip():
                        total += 1

        if total < 20:
            return 6
        elif total < 50:
            return 4
        else:
            return 2

    def optimize_rules(self) -> dict:
        """基于分析优化破解规则"""
        stats = self.analyze()
        if not stats:
            return {}

        dynamic_budget = self.get_dynamic_budget()
        candidate_changes = []

        # 规则1: 成功率过低
        if stats.get('success_rate', 0) < 0.5:
            candidate_changes.append({
                "field": "default_method",
                "old": "frida",
                "new": "multi",
                "reason": f"成功率 {stats['success_rate']:.0%} 过低，默认使用多方法组合"
            })

        # 规则2: 耗时过长
        if stats.get('avg_duration_sec', 30) > 300:
            candidate_changes.append({
                "field": "timeout_default",
                "old": 300,
                "new": 180,
                "reason": f"平均耗时 {stats['avg_duration_sec']:.1f}s 过长，缩短超时"
            })

        # 规则3: 特定模块成功率低
        module_stats = stats.get('module_stats', {})
        for mod, mod_stat in module_stats.items():
            rate = mod_stat["success"] / mod_stat["total"] if mod_stat["total"] > 0 else 0
            if rate < 0.3 and mod_stat["total"] >= 3:
                candidate_changes.append({
                    "field": f"module_{mod}_strategy",
                    "old": "default",
                    "new": "aggressive",
                    "reason": f"模块 '{mod}' 成功率 {rate:.0%}，切换激进策略"
                })

        # 负反馈过滤
        filtered = [c for c in candidate_changes
                    if not self.is_rejected_before(c['field'], c['new'])]

        # 修改预算限制
        if len(filtered) > dynamic_budget:
            priority_map = {"success_rate": 0, "avg_duration_sec": 1, "module_weakness": 2}
            def prio(c):
                for k, p in priority_map.items():
                    if k in c.get('reason', ''):
                        return p
                return 99
            filtered.sort(key=prio)
            selected = filtered[:dynamic_budget]
            dropped = filtered[dynamic_budget:]
        else:
            selected = filtered
            dropped = []

        rules = {
            "default_method": "frida",
            "timeout_default": 300,
            "edit_budget": dynamic_budget,
            "changes_applied": len(selected),
            "changes_dropped": len(dropped),
            "last_updated": datetime.now().isoformat(),
            "change_log": [{"field": c["field"], "from": c["old"], "to": c["new"], "reason": c["reason"]} for c in selected]
        }

        if dropped:
            rules["dropped_changes"] = [{"field": c["field"], "reason": c["reason"]} for c in dropped]

        with open(self.rules_file, 'w') as f:
            json.dump(rules, f, indent=2, ensure_ascii=False)

        return rules

    def get_rules(self) -> dict:
        """获取当前规则"""
        if os.path.exists(self.rules_file):
            with open(self.rules_file, 'r') as f:
                return json.load(f)
        return self.optimize_rules()

    # ====== L4: 验证门控 ======

    def evaluate_gate(self, candidate_skill: str, candidate_score: float,
                      current_skill: str, current_score: float,
                      best_skill: str, best_score: float, best_step: int,
                      global_step: int) -> dict:
        """验证门控"""
        if candidate_score > current_score:
            if candidate_score > best_score:
                result = {
                    "action": "accept_new_best",
                    "current_skill": candidate_skill,
                    "current_score": candidate_score,
                    "best_skill": candidate_skill,
                    "best_score": candidate_score,
                    "best_step": global_step,
                    "reason": f"候选 {candidate_score:.2f} > 最佳 {best_score:.2f}"
                }
            else:
                result = {
                    "action": "accept",
                    "current_skill": candidate_skill,
                    "current_score": candidate_score,
                    "best_skill": best_skill,
                    "best_score": best_score,
                    "best_step": best_step,
                    "reason": f"候选 {candidate_score:.2f} > 当前 {current_score:.2f}"
                }
        else:
            result = {
                "action": "reject",
                "current_skill": current_skill,
                "current_score": current_score,
                "best_skill": best_skill,
                "best_score": best_score,
                "best_step": best_step,
                "reason": f"候选 {candidate_score:.2f} <= 当前 {current_score:.2f}"
            }

        self._record_gate(result)
        return result

    def _record_gate(self, result: dict):
        record = {"timestamp": datetime.now().isoformat(), **result}
        with open(self.gate_file, 'a') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    def get_gate_stats(self) -> dict:
        """获取门控统计"""
        if not os.path.exists(self.gate_file):
            return {"total": 0, "accept_rate": 0, "new_best_rate": 0}

        decisions = []
        with open(self.gate_file, 'r') as f:
            for line in f:
                if line.strip():
                    decisions.append(json.loads(line))

        total = len(decisions)
        if total == 0:
            return {"total": 0, "accept_rate": 0, "new_best_rate": 0}

        accepts = sum(1 for d in decisions if d["action"] in ["accept", "accept_new_best"])
        new_bests = sum(1 for d in decisions if d["action"] == "accept_new_best")

        return {
            "total": total,
            "accept_rate": round(accepts / total, 2),
            "new_best_rate": round(new_bests / total, 2),
            "recent_10": decisions[-10:]
        }

    # ====== Slow Update ======

    def inject_slow_update_field(self, skill_content: str) -> str:
        """注入受保护区域"""
        if SLOW_UPDATE_START in skill_content and SLOW_UPDATE_END in skill_content:
            return skill_content
        return skill_content.rstrip() + f"\n\n{SLOW_UPDATE_START}\n{SLOW_UPDATE_END}\n"

    def extract_slow_update_field(self, skill_content: str) -> str:
        """提取受保护区域"""
        start = skill_content.find(SLOW_UPDATE_START)
        end = skill_content.find(SLOW_UPDATE_END)
        if start == -1 or end == -1:
            return ""
        return skill_content[start + len(SLOW_UPDATE_START):end].strip()

    def replace_slow_update_field(self, skill_content: str, new_content: str) -> str:
        """替换受保护区域"""
        skill_content = self.inject_slow_update_field(skill_content)
        start = skill_content.find(SLOW_UPDATE_START)
        end = skill_content.find(SLOW_UPDATE_END)
        inner_start = start + len(SLOW_UPDATE_START)
        return skill_content[:inner_start] + "\n" + new_content + "\n" + skill_content[end:]

    def run_slow_update(self, prev_skill: str, curr_skill: str,
                        comparison_data: List[dict]) -> Optional[str]:
        """跨Epoch纵向对比"""
        if not comparison_data:
            return None

        improvements = []
        regressions = []
        persistent_failures = []

        for item in comparison_data:
            prev_score = item.get('prev_score', 0)
            curr_score = item.get('curr_score', 0)
            task = item.get('task', 'unknown')
            diff = curr_score - prev_score

            if diff > 0.1:
                improvements.append(f"- {task}: {prev_score:.2f} → {curr_score:.2f} (+{diff:.2f})")
            elif diff < -0.1:
                regressions.append(f"- {task}: {prev_score:.2f} → {curr_score:.2f} ({diff:.2f})")
            elif curr_score < 0.5:
                persistent_failures.append(f"- {task}: 持续低分 {curr_score:.2f}")

        guidance = ["## 优化器长期经验（自动维护）", "",
                    f"> 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]

        if improvements:
            guidance.extend(["### ✅ 已验证有效的改进"] + improvements[:5] + [""])
        if regressions:
            guidance.extend(["### ⚠️ 已验证的退化"] + regressions[:5] + [""])
        if persistent_failures:
            guidance.extend(["### 🔴 持续失败模式"] + persistent_failures[:5] + [""])

        content = "\n".join(guidance)
        with open(self.slow_update_file, 'w') as f:
            f.write(content)
        return content

    def get_slow_update_content(self) -> str:
        """获取Slow Update内容"""
        if os.path.exists(self.slow_update_file):
            with open(self.slow_update_file, 'r') as f:
                return f.read()
        return ""


# 全局追踪器实例
tracker = EvolutionTracker()
