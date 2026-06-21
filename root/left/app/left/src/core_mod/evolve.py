"""进化模块"""
import copy
import time
from typing import Any, Dict, Final, List, Optional

from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class Snapshot:
    """快照实体"""

    def __init__(
        self,
        snapshot_id: str,
        config: Dict[str, Any],
        performance: float
    ) -> None:
        Validator.require_type(snapshot_id, str, "snapshot_id")
        Validator.require_type(config, dict, "config")
        Validator.require_type(performance, (int, float), "performance")
        self.snapshot_id: str = snapshot_id
        self.config: Dict[str, Any] = copy.deepcopy(config)
        self.performance: float = float(performance)
        self.timestamp: float = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "config": self.config,
            "performance": self.performance,
            "timestamp": self.timestamp,
        }


class SnapshotManager:
    """快照管理器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.max_snapshots: int = int(config.get("max_snapshots", 5))
        self.rollback_threshold: float = float(
            config.get("rollback_threshold", 0.1)
        )
        self.snapshots: List[Snapshot] = []
        self.best_performance: float = 0.0

    def save(self, config: Dict[str, Any], performance: float) -> None:
        Validator.require_type(config, dict, "config")
        Validator.require_type(performance, (int, float), "performance")
        self._create_snapshot(config, performance)
        self._trim_snapshots()
        self._update_best(performance)

    def _create_snapshot(
        self, config: Dict[str, Any], performance: float
    ) -> None:
        snapshot_id = f"snap_{int(time.time() * 1000)}"
        snapshot = Snapshot(snapshot_id, config, performance)
        self.snapshots.append(snapshot)
        logger.info(f"Snapshot saved: {snapshot_id} perf={performance:.4f}", "evolution")

    def _trim_snapshots(self) -> None:
        if len(self.snapshots) > self.max_snapshots:
            removed = self.snapshots.pop(0)
            logger.debug(f"Snapshot trimmed: {removed.snapshot_id}", "evolution")

    def _update_best(self, performance: float) -> None:
        if performance > self.best_performance:
            self.best_performance = performance
            logger.info(f"New best performance: {performance:.4f}", "evolution")

    def should_rollback(self, current_performance: float) -> bool:
        Validator.require_type(
            current_performance, (int, float), "current_performance"
        )
        if not self.snapshots:
            return False
        drop = self.best_performance - current_performance
        should = drop > self.rollback_threshold
        if should:
            logger.warning(f"Rollback triggered: drop={drop:.4f}", "evolution")
        return should

    def get_best_snapshot(self) -> Optional[Snapshot]:
        if not self.snapshots:
            return None
        return max(self.snapshots, key=lambda s: s.performance)

    def get_snapshot_count(self) -> int:
        return len(self.snapshots)


class RefactorEngine:
    """重构引擎"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.error_threshold: float = float(
            config.get("error_threshold", 0.3)
        )
        self.stagnation_rounds: int = int(
            config.get("stagnation_rounds", 100)
        )

    def analyze(
        self, performance_history: List[float], error_rate: float
    ) -> Dict[str, Any]:
        Validator.require_type(
            performance_history, list, "performance_history"
        )
        Validator.require_type(error_rate, (int, float), "error_rate")
        return self._analyze_internal(performance_history, error_rate)

    def _analyze_internal(
        self, performance_history: List[float], error_rate: float
    ) -> Dict[str, Any]:
        needs_refactor = self._check_error(error_rate)
        reason = ""
        if needs_refactor:
            reason = "high_error_rate"
            logger.warning(f"High error rate detected: {error_rate:.4f}", "evolution")
        elif self._check_stagnation(performance_history):
            needs_refactor = True
            reason = "performance_decline"
            logger.info("Performance stagnation detected", "evolution")
        return {"needs_refactor": needs_refactor, "reason": reason}

    def _check_error(self, error_rate: float) -> bool:
        return error_rate > self.error_threshold

    def _check_stagnation(
        self, performance_history: List[float]
    ) -> bool:
        if len(performance_history) < self.stagnation_rounds:
            return False
        recent = performance_history[-self.stagnation_rounds:]
        trend = (recent[-1] - recent[0]) / len(recent)
        return trend < 0

    def generate_adjustments(
        self, current_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        Validator.require_type(current_config, dict, "current_config")
        new_config = copy.deepcopy(current_config)
        exploration = new_config.get("exploration", {})
        current_ratio = exploration.get("base_exploration_ratio", 0.3)
        new_ratio = round(min(0.5, current_ratio + 0.05), 2)
        exploration["base_exploration_ratio"] = new_ratio
        logger.info(f"Adjustment: exploration_ratio {current_ratio} -> {new_ratio}", "evolution")
        return new_config


class FeatureEngine:
    """特征引擎"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config

    def detect_gap(
        self, predictions: Dict[str, Any], actual: Dict[str, Any]
    ) -> float:
        Validator.require_type(predictions, dict, "predictions")
        Validator.require_type(actual, dict, "actual")
        gaps = self._collect_gaps(predictions, actual)
        if not gaps:
            return 0.0
        avg_gap = float(sum(gaps) / len(gaps))
        logger.debug(f"Average prediction gap: {avg_gap:.4f}", "evolution")
        return avg_gap

    def _collect_gaps(
        self, predictions: Dict[str, Any], actual: Dict[str, Any]
    ) -> List[float]:
        gaps: List[float] = []
        for level, preds in predictions.items():
            for pred in preds:
                gap = self._calc_single_gap(pred, actual)
                gaps.append(gap)
        return gaps

    def _calc_single_gap(
        self, pred: Dict[str, Any], actual: Dict[str, Any]
    ) -> float:
        metric = pred.get("target_metric", "")
        predicted_value = pred.get("predicted_value", 0.0)
        actual_value = actual.get("system_metrics", {}).get(
            metric, predicted_value
        )
        return abs(predicted_value - actual_value)

    def propose_feature(
        self, gap: float, threshold: float
    ) -> Optional[str]:
        Validator.require_type(gap, (int, float), "gap")
        Validator.require_type(threshold, (int, float), "threshold")
        if gap > threshold:
            logger.info(f"Feature proposed: enhance_prediction_model (gap={gap:.4f})", "evolution")
            return "enhance_prediction_model"
        return None


class ReviewEngine:
    """评审引擎"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config

    def review_adjustments(
        self,
        proposed_config: Dict[str, Any],
        current_performance: float,
        previous_performance: float
    ) -> bool:
        Validator.require_type(proposed_config, dict, "proposed_config")
        Validator.require_type(
            current_performance, (int, float), "current_performance"
        )
        Validator.require_type(
            previous_performance, (int, float), "previous_performance"
        )
        threshold = previous_performance * 0.9
        approved = current_performance >= threshold
        logger.info(f"Review: current={current_performance:.4f} threshold={threshold:.4f} approved={approved}", "evolution")
        return approved


class EvolutionModule:
    """进化模块主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self._init_engines(config)
        self.gap_threshold: float = float(
            config.get("gap_threshold", 0.1)
        )
        self.adjustment_history: List[Dict[str, Any]] = []

    def _init_engines(self, config: Dict[str, Any]) -> None:
        snapshot_config: Dict[str, Any] = config.get("snapshot", {})
        snapshot_config["rollback_threshold"] = config.get(
            "rollback_threshold", 0.1
        )
        self.snapshot_manager = SnapshotManager(snapshot_config)
        self.refactor = RefactorEngine(config.get("refactor", {}))
        self.feature = FeatureEngine(config.get("feature", {}))
        self.review = ReviewEngine(config.get("review", {}))

    def evolve(
        self,
        current_config: Dict[str, Any],
        performance_history: List[float],
        predictions: Dict[str, Any],
        actual_state: Dict[str, Any],
        error_rate: float
    ) -> Dict[str, Any]:
        self._validate_evolve_inputs(
            current_config, performance_history,
            predictions, actual_state, error_rate
        )
        current_performance = self._get_current_performance(
            performance_history
        )
        self.snapshot_manager.save(current_config, current_performance)
        return self._process_evolution(
            current_config, performance_history,
            predictions, actual_state, current_performance, error_rate
        )

    def _validate_evolve_inputs(
        self,
        current_config: Dict[str, Any],
        performance_history: List[float],
        predictions: Dict[str, Any],
        actual_state: Dict[str, Any],
        error_rate: float
    ) -> None:
        Validator.require_type(current_config, dict, "current_config")
        Validator.require_type(
            performance_history, list, "performance_history"
        )
        Validator.require_type(predictions, dict, "predictions")
        Validator.require_type(actual_state, dict, "actual_state")
        Validator.require_type(error_rate, (int, float), "error_rate")

    def _get_current_performance(
        self, performance_history: List[float]
    ) -> float:
        return performance_history[-1] if performance_history else 0.0

    def _process_evolution(
        self,
        current_config: Dict[str, Any],
        performance_history: List[float],
        predictions: Dict[str, Any],
        actual_state: Dict[str, Any],
        current_performance: float,
        error_rate: float
    ) -> Dict[str, Any]:
        refactor_result = self.refactor.analyze(performance_history, error_rate)
        gap = self.feature.detect_gap(predictions, actual_state)
        proposed_feature = self.feature.propose_feature(gap, self.gap_threshold)
        proposed_config, approved = self._evaluate_refactor(
            current_config, performance_history, current_performance, refactor_result
        )
        self._record_adjustment(refactor_result, gap, proposed_feature, approved, proposed_config)
        return self._build_result(approved, current_config, proposed_config, gap)

    def _evaluate_refactor(
        self,
        current_config: Dict[str, Any],
        performance_history: List[float],
        current_performance: float,
        refactor_result: Dict[str, Any]
    ) -> tuple:
        proposed_config = None
        approved = False
        if refactor_result["needs_refactor"]:
            proposed_config = self.refactor.generate_adjustments(
                current_config
            )
            prev_perf = self._get_prev_performance(performance_history)
            approved = self.review.review_adjustments(
                proposed_config, current_performance, prev_perf
            )
        return proposed_config, approved

    def _get_prev_performance(
        self, performance_history: List[float]
    ) -> float:
        if len(performance_history) > 1:
            return performance_history[-2]
        return performance_history[-1] if performance_history else 0.0

    def _record_adjustment(
        self,
        refactor_result: Dict[str, Any],
        gap: float,
        proposed_feature: Optional[str],
        approved: bool,
        proposed_config: Optional[Dict[str, Any]]
    ) -> None:
        adjustment = self._build_adjustment(refactor_result, gap, proposed_feature, approved, proposed_config)
        self.adjustment_history.append(adjustment)
        self._trim_history()

    def _build_adjustment(
        self, refactor_result: Dict[str, Any], gap: float,
        proposed_feature: Optional[str], approved: bool,
        proposed_config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        return {
            "loop_time": time.time(),
            "refactor_reason": refactor_result.get("reason", ""),
            "gap": gap,
            "proposed_feature": proposed_feature,
            "approved": approved,
            "proposed_config": proposed_config,
        }

    def _trim_history(self) -> None:
        if len(self.adjustment_history) > 1000:
            self.adjustment_history.pop(0)

    def _build_result(
        self,
        approved: bool,
        current_config: Dict[str, Any],
        proposed_config: Optional[Dict[str, Any]],
        gap: float
    ) -> Dict[str, Any]:
        new_config = proposed_config if approved else current_config
        return {
            "should_adjust": approved,
            "new_config": new_config,
            "gap": gap,
            "snapshot_count": self.snapshot_manager.get_snapshot_count(),
        }

    def should_rollback(self, current_performance: float) -> bool:
        Validator.require_type(
            current_performance, (int, float), "current_performance"
        )
        return self.snapshot_manager.should_rollback(current_performance)

    def get_best_snapshot(self) -> Optional[Dict[str, Any]]:
        snapshot = self.snapshot_manager.get_best_snapshot()
        if snapshot is None:
            return None
        return snapshot.to_dict()

    def get_adjustment_stats(self) -> Dict[str, Any]:
        total = len(self.adjustment_history)
        approved = sum(
            1 for a in self.adjustment_history if a.get("approved")
        )
        return {"total": total, "approved": approved}

    def get_state(self) -> Dict[str, Any]:
        """获取进化模块状态"""
        return {
            "adjustment_history_len": len(self.adjustment_history),
            "gap_threshold": self.gap_threshold,
            "snapshot_count": self.snapshot_manager.get_snapshot_count(),
            "adjustment_stats": self.get_adjustment_stats(),
        }

    def reset(self) -> None:
        """重置进化模块"""
        logger.debug("[EvolutionModule.reset] called", "evolution")
        self.adjustment_history.clear()
        self._init_engines(self.config)

    def health_check(self) -> bool:
        """健康检查"""
        logger.debug("[EvolutionModule.health_check] called", "evolution")
        return True
