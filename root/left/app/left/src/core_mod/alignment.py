"""价值对齐与伦理约束模块"""
import copy
from typing import Any, Dict, Final, List, Optional

import numpy as np

from root.left.app.left.src.utils_main.exceptions import ValidationError
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class ValueAlignment:
    """价值对齐器（定义核心价值，评估行为符合度）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[ValueAlignment.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.values: Dict[str, float] = dict(config.get("values", {
            "safety": 1.0,
            "fairness": 1.0,
            "transparency": 0.8,
            "privacy": 0.9,
        }))
        self.min_score: float = float(config.get("min_score", 0.6))
        self.history: List[Dict[str, Any]] = []
        self.max_history: int = int(config.get("max_history", 500))
        logger.info(f"ValueAlignment initialized values={list(self.values.keys())}", "alignment")

    def evaluate(self, action: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[ValueAlignment.evaluate] start")
        Validator.require_type(action, dict, "action")
        scores: Dict[str, float] = {}
        for name, weight in self.values.items():
            score = self._score_dimension(action, name)
            scores[name] = score * weight
        total = float(np.mean(list(scores.values()))) if scores else 0.0
        aligned = total >= self.min_score
        record = {
            "scores": scores,
            "total": total,
            "aligned": aligned,
            "action_id": action.get("id", "unknown"),
        }
        self._add_history(record)
        logger.debug(f"[ValueAlignment.evaluate] total={total:.4f} aligned={aligned}")
        return record

    def _score_dimension(self, action: Dict[str, Any], dimension: str) -> float:
        logger.debug(f"[ValueAlignment._score_dimension] dim={dimension}")
        metadata = action.get("metadata", {})
        flagged = metadata.get("flagged_dimensions", [])
        if dimension in flagged:
            return 0.0
        return 1.0

    def _add_history(self, record: Dict[str, Any]) -> None:
        self.history.append(record)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        logger.debug(f"[ValueAlignment._add_history] size={len(self.history)}")

    def get_alignment_rate(self) -> float:
        if not self.history:
            return 1.0
        aligned_count = sum(1 for r in self.history if r.get("aligned"))
        rate = aligned_count / len(self.history)
        logger.debug(f"[ValueAlignment.get_alignment_rate] rate={rate:.4f}")
        return float(rate)

    def get_state(self) -> Dict[str, Any]:
        return {
            "values": self.values.copy(),
            "min_score": self.min_score,
            "alignment_rate": self.get_alignment_rate(),
            "history_size": len(self.history),
        }


class EthicalConstraint:
    """伦理约束引擎（规则检查，行为拦截）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[EthicalConstraint.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.rules: List[Dict[str, Any]] = list(config.get("rules", [
            {"id": "no_harm", "pattern": "harm", "action": "block"},
            {"id": "no_deception", "pattern": "deceive", "action": "block"},
            {"id": "privacy_protect", "pattern": "leak", "action": "warn"},
        ]))
        self.violations: List[Dict[str, Any]] = []
        self.max_violations: int = int(config.get("max_violations", 1000))
        logger.info(f"EthicalConstraint initialized rules={len(self.rules)}", "alignment")

    def check(self, action: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[EthicalConstraint.check] start")
        Validator.require_type(action, dict, "action")
        description = str(action.get("description", ""))
        blocked = False
        triggered: List[str] = []
        for rule in self.rules:
            pattern = str(rule.get("pattern", ""))
            if pattern and pattern in description.lower():
                triggered.append(rule["id"])
                if rule.get("action") == "block":
                    blocked = True
                logger.warning(f"[EthicalConstraint.check] rule={rule['id']} triggered", "alignment")
        result = {
            "allowed": not blocked,
            "triggered_rules": triggered,
            "action_id": action.get("id", "unknown"),
        }
        if triggered:
            self._record_violation(result)
        logger.debug(f"[EthicalConstraint.check] allowed={result['allowed']} triggered={len(triggered)}")
        return result

    def _record_violation(self, result: Dict[str, Any]) -> None:
        self.violations.append(copy.deepcopy(result))
        if len(self.violations) > self.max_violations:
            self.violations.pop(0)
        logger.debug(f"[EthicalConstraint._record_violation] count={len(self.violations)}")

    def add_rule(self, rule: Dict[str, Any]) -> None:
        logger.debug(f"[EthicalConstraint.add_rule] id={rule.get('id')}")
        Validator.require_type(rule, dict, "rule")
        if "id" not in rule or "pattern" not in rule:
            raise ValidationError("rule must contain 'id' and 'pattern'")
        self.rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        logger.debug(f"[EthicalConstraint.remove_rule] id={rule_id}")
        original = len(self.rules)
        self.rules = [r for r in self.rules if r.get("id") != rule_id]
        removed = len(self.rules) < original
        logger.debug(f"[EthicalConstraint.remove_rule] removed={removed}")
        return removed

    def get_state(self) -> Dict[str, Any]:
        return {
            "rule_count": len(self.rules),
            "violation_count": len(self.violations),
            "rules": [r["id"] for r in self.rules],
        }


class BiasDetector:
    """偏差检测器（统计偏差、历史偏差分析）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[BiasDetector.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.threshold: float = float(config.get("threshold", 0.2))
        self.min_samples: int = int(config.get("min_samples", 10))
        self.group_stats: Dict[str, Dict[str, List[float]]] = {}
        logger.info(f"BiasDetector initialized threshold={self.threshold}", "alignment")

    def record(self, group: str, outcome: float) -> None:
        logger.debug(f"[BiasDetector.record] group={group} outcome={outcome}")
        if group not in self.group_stats:
            self.group_stats[group] = {"outcomes": []}
        self.group_stats[group]["outcomes"].append(outcome)
        if len(self.group_stats[group]["outcomes"]) > 1000:
            self.group_stats[group]["outcomes"].pop(0)
        logger.debug(f"[BiasDetector.record] count={len(self.group_stats[group]['outcomes'])}")

    def detect(self) -> Optional[Dict[str, Any]]:
        logger.debug("[BiasDetector.detect] start")
        if len(self.group_stats) < 2:
            logger.debug("[BiasDetector.detect] insufficient groups")
            return None
        means: Dict[str, float] = {}
        for group, stats in self.group_stats.items():
            outcomes = stats["outcomes"]
            if len(outcomes) < self.min_samples:
                logger.debug(f"[BiasDetector.detect] group={group} insufficient samples")
                return None
            means[group] = float(np.mean(outcomes))
        if not means:
            return None
        max_mean = max(means.values())
        min_mean = min(means.values())
        gap = max_mean - min_mean
        biased = gap > self.threshold
        result = {
            "biased": biased,
            "gap": gap,
            "group_means": means,
            "threshold": self.threshold,
        }
        if biased:
            logger.warning(f"[BiasDetector.detect] BIAS DETECTED gap={gap:.4f}", "alignment")
        logger.debug(f"[BiasDetector.detect] gap={gap:.4f} biased={biased}")
        return result

    def get_state(self) -> Dict[str, Any]:
        return {
            "group_count": len(self.group_stats),
            "threshold": self.threshold,
            "min_samples": self.min_samples,
        }


class FairnessAuditor:
    """公平性审计器（群体公平性、机会均等）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[FairnessAuditor.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.epsilon: float = float(config.get("epsilon", 0.05))
        self.decisions: List[Dict[str, Any]] = []
        self.max_decisions: int = int(config.get("max_decisions", 1000))
        logger.info(f"FairnessAuditor initialized epsilon={self.epsilon}", "alignment")

    def audit(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[FairnessAuditor.audit] start")
        Validator.require_type(decision, dict, "decision")
        group = str(decision.get("group", "default"))
        outcome = bool(decision.get("outcome", False))
        self.decisions.append({"group": group, "outcome": outcome})
        if len(self.decisions) > self.max_decisions:
            self.decisions.pop(0)
        rates = self._compute_rates()
        if len(rates) < 2:
            return {"fair": True, "rates": rates, "groups": list(rates.keys())}
        max_rate = max(rates.values())
        min_rate = min(rates.values())
        fair = (max_rate - min_rate) <= self.epsilon
        if not fair:
            logger.warning(f"[FairnessAuditor.audit] UNFAIR max={max_rate:.4f} min={min_rate:.4f}", "alignment")
        logger.debug(f"[FairnessAuditor.audit] fair={fair} groups={len(rates)}")
        return {"fair": fair, "rates": rates, "groups": list(rates.keys())}

    def _compute_rates(self) -> Dict[str, float]:
        logger.debug("[FairnessAuditor._compute_rates] start")
        group_counts: Dict[str, int] = {}
        group_positive: Dict[str, int] = {}
        for d in self.decisions:
            g = d["group"]
            group_counts[g] = group_counts.get(g, 0) + 1
            if d["outcome"]:
                group_positive[g] = group_positive.get(g, 0) + 1
        rates = {}
        for g in group_counts:
            rates[g] = group_positive.get(g, 0) / group_counts[g]
        logger.debug(f"[FairnessAuditor._compute_rates] rates={rates}")
        return rates

    def get_state(self) -> Dict[str, Any]:
        return {
            "decision_count": len(self.decisions),
            "epsilon": self.epsilon,
            "rates": self._compute_rates(),
        }


class AlignmentModule:
    """价值对齐与伦理约束主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[AlignmentModule.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.value_alignment = ValueAlignment(config.get("value_alignment", {}))
        logger.debug("[AlignmentModule.__init__] value_alignment created")
        self.ethical = EthicalConstraint(config.get("ethical", {}))
        logger.debug("[AlignmentModule.__init__] ethical created")
        self.bias = BiasDetector(config.get("bias", {}))
        logger.debug("[AlignmentModule.__init__] bias created")
        self.fairness = FairnessAuditor(config.get("fairness", {}))
        logger.debug("[AlignmentModule.__init__] fairness created")
        logger.info("AlignmentModule initialized", "alignment")

    def review_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[AlignmentModule.review_action] start")
        Validator.require_type(action, dict, "action")
        ethical_result = self.ethical.check(action)
        value_result = self.value_alignment.evaluate(action)
        approved = ethical_result["allowed"] and value_result["aligned"]
        result = {
            "approved": approved,
            "ethical": ethical_result,
            "value_alignment": value_result,
        }
        logger.info(f"[AlignmentModule.review_action] approved={approved}", "alignment")
        return result

    def record_outcome(self, group: str, outcome: float) -> None:
        logger.debug(f"[AlignmentModule.record_outcome] group={group}")
        self.bias.record(group, outcome)

    def audit_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[AlignmentModule.audit_decision] start")
        return self.fairness.audit(decision)

    def check_bias(self) -> Optional[Dict[str, Any]]:
        logger.debug("[AlignmentModule.check_bias] start")
        return self.bias.detect()

    def get_state(self) -> Dict[str, Any]:
        return {
            "value_alignment": self.value_alignment.get_state(),
            "ethical": self.ethical.get_state(),
            "bias": self.bias.get_state(),
            "fairness": self.fairness.get_state(),
        }
