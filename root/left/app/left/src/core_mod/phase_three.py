"""Phase 3 核心"""
from typing import Any, Dict, Final, List

from root.left.app.left.src.core_mod.evolve import EvolutionModule
from root.left.app.left.src.utils_main.constants import PredictionLevel
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class PhaseThreeCore:
    """Phase 3 整合核心"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.evolution = EvolutionModule(config.get("evolution", {}))
        self.performance_history: List[float] = []
        self.max_history: int = int(config.get("max_history", 200))
        logger.info(f"PhaseThreeCore initialized max_history={self.max_history}", "phase3")

    def step(
        self,
        current_config: Dict[str, Any],
        phase1_result: Dict[str, Any],
        phase2_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        Validator.require_type(current_config, dict, "current_config")
        Validator.require_type(phase1_result, dict, "phase1_result")
        Validator.require_type(phase2_result, dict, "phase2_result")
        performance = phase1_result.get("performance", 0.0)
        self.performance_history.append(performance)
        if len(self.performance_history) > self.max_history:
            removed = self.performance_history.pop(0)
            logger.debug(f"Phase3 trimmed oldest performance={removed:.4f}", "phase3")
        error_rate = self._get_error_rate(phase1_result)
        logger.info(f"Phase3 step: performance={performance:.4f} error_rate={error_rate:.4f}", "phase3")
        evolution_result = self._evolve(
            current_config, phase1_result, error_rate
        )
        return self._build_result(performance, evolution_result)

    def _evolve(
        self, current_config: Dict[str, Any],
        phase1_result: Dict[str, Any], error_rate: float
    ) -> Dict[str, Any]:
        predictions = phase1_result.get("predictions", {})
        state = phase1_result.get("state", {})
        return self.evolution.evolve(
            current_config,
            self.performance_history,
            predictions,
            state,
            error_rate
        )

    def _build_result(
        self, performance: float, evolution_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {
            "evolution_result": evolution_result,
            "performance_history": self.performance_history.copy(),
            "should_rollback": self.evolution.should_rollback(performance),
            "best_snapshot": self.evolution.get_best_snapshot(),
        }

    def _get_error_rate(self, phase1_result: Dict[str, Any]) -> float:
        predictions = phase1_result.get("predictions", {})
        state = phase1_result.get("state", {})
        errors = self._collect_errors(predictions, state)
        if not errors:
            return 0.0
        avg_error = float(sum(errors) / len(errors))
        logger.debug(f"Prediction errors: count={len(errors)} avg={avg_error:.4f}", "phase3")
        return avg_error

    def _collect_errors(
        self, predictions: Dict[str, Any], state: Dict[str, Any]
    ) -> List[float]:
        errors: List[float] = []
        for level in PredictionLevel:
            preds = predictions.get(level, [])
            for pred in preds:
                error = self._calc_single_error(pred, state)
                errors.append(error)
        return errors

    def _calc_single_error(
        self, pred: Dict[str, Any], state: Dict[str, Any]
    ) -> float:
        metric = pred.get("target_metric", "")
        predicted_value = pred.get("predicted_value", 0.0)
        actual_value = state.get("system_metrics", {}).get(metric, predicted_value)
        error = abs(predicted_value - actual_value) / max(abs(actual_value), 1e-8)
        return min(error, 10.0)

    def get_state(self) -> Dict[str, Any]:
        """获取 Phase 3 状态"""
        return {
            "history_len": len(self.performance_history),
            "max_history": self.max_history,
            "has_evolution": hasattr(self.evolution, "evolve"),
        }

    def reset(self) -> None:
        """重置 Phase 3"""
        logger.debug("[PhaseThreeCore.reset] called", "phase3")
        self.performance_history.clear()
        if hasattr(self.evolution, "reset") and callable(getattr(self.evolution, "reset")):
            self.evolution.reset()

    def health_check(self) -> bool:
        """健康检查"""
        logger.debug("[PhaseThreeCore.health_check] called", "phase3")
        return self.evolution.health_check() and self.max_history > 0
