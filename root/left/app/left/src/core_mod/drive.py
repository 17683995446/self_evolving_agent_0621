"""驱力引擎模块"""
from typing import Any, Dict, Final, List, Optional

from root.left.app.left.src.utils_main.constants import DriveType
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class SafeDriveCalculator:
    """安全驱力计算器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.thresholds: Dict[str, float] = config.get("thresholds", {
            "cpu_critical": 90.0,
            "memory_critical": 90.0,
        })
        self.risk_weights: Dict[str, float] = config.get("risk_weights", {
            "cpu_high": 0.5,
            "memory_high": 0.5,
        })

    def calculate(self, state: Dict[str, Any]) -> float:
        metrics = state.get("system_metrics", {})
        risk = self._calc_risk(metrics)
        safe = max(0.0, 1.0 - risk)
        logger.debug(f"SafeDrive: risk={risk:.4f} safe={safe:.4f}", "drive")
        return safe

    def _calc_risk(self, metrics: Dict[str, float]) -> float:
        risk = 0.0
        risk += self._metric_risk(metrics, "cpu_percent")
        risk += self._metric_risk(metrics, "memory_percent")
        return min(risk, 1.0)

    def _metric_risk(
        self, metrics: Dict[str, float], name: str
    ) -> float:
        value = metrics.get(name, 0.0)
        threshold = self.thresholds.get(f"{name.split('_')[0]}_critical", 90.0)
        if value >= threshold:
            return self.risk_weights.get(f"{name.split('_')[0]}_high", 0.5)
        return 0.0


class GainDriveCalculator:
    """收益驱力计算器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.error_history: List[float] = []
        self.max_history: int = int(config.get("max_history", 100))

    def calculate(
        self, state: Dict[str, Any], prediction_error: Optional[float]
    ) -> float:
        features = state.get("feature_vector", [])
        coverage = self._estimate_coverage(features)
        error_trend = self._calc_error_trend(prediction_error)
        stagnation = self._check_stagnation(features)
        gain = 0.4 * error_trend + 0.3 * coverage - 0.1 * stagnation
        result = float(max(0.0, min(1.0, gain)))
        logger.debug(f"GainDrive: coverage={coverage:.4f} error_trend={error_trend:.4f} gain={result:.4f}", "drive")
        return result

    def _estimate_coverage(self, features: List[float]) -> float:
        if not features:
            return 0.0
        return float(len([f for f in features if f != 0]) / len(features))

    def _calc_error_trend(
        self, prediction_error: Optional[float]
    ) -> float:
        if prediction_error is None:
            return 0.5
        self.error_history.append(prediction_error)
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)
        return float(min(1.0, prediction_error * 2))

    def _check_stagnation(self, features: List[float]) -> float:
        if len(self.error_history) < 10:
            return 0.0
        recent = self.error_history[-10:]
        variance = sum((x - sum(recent) / len(recent)) ** 2 for x in recent) / len(recent)
        return float(min(1.0, variance))


class EffDriveCalculator:
    """能效驱力计算器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.agent_cpu_limit: float = float(config.get("agent_cpu_limit", 20.0))
        self.agent_memory_limit: float = float(config.get("agent_memory_limit", 20.0))

    def calculate(
        self, state: Dict[str, Any],
        agent_cpu: float, agent_memory: float
    ) -> float:
        metrics = state.get("system_metrics", {})
        system_load = metrics.get("cpu_percent", 0.0) / 100.0
        agent_load = (agent_cpu / max(self.agent_cpu_limit, 1.0))
        total_load = system_load + agent_load
        result = float(max(0.0, 1.0 - total_load))
        logger.debug(f"EffDrive: system_load={system_load:.4f} agent_load={agent_load:.4f} eff={result:.4f}", "drive")
        return result


class DynamicWeightAdjuster:
    """动态权重调整器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.weights: Dict[DriveType, float] = {
            DriveType.SAFE: 0.4,
            DriveType.GAIN: 0.3,
            DriveType.EFF: 0.3,
        }
        self.learning_rate: float = float(config.get("learning_rate", 0.1))

    def adjust(
        self, state: Dict[str, Any],
        rewards: Dict[DriveType, float]
    ) -> Dict[DriveType, float]:
        for drive_type, reward in rewards.items():
            self._update_weight(drive_type, reward)
        self._normalize_weights()
        logger.debug(f"Weights adjusted: safe={self.weights[DriveType.SAFE]:.4f} gain={self.weights[DriveType.GAIN]:.4f} eff={self.weights[DriveType.EFF]:.4f}", "drive")
        return self.weights.copy()

    def _update_weight(
        self, drive_type: DriveType, reward: float
    ) -> None:
        current = self.weights[drive_type]
        self.weights[drive_type] = current + self.learning_rate * reward

    def _normalize_weights(self) -> None:
        total = sum(self.weights.values())
        if total > 0:
            for key in self.weights:
                self.weights[key] /= total


class ScenarioDetector:
    """场景检测器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config

    def detect(
        self, state: Dict[str, Any],
        gaps: Dict[DriveType, float]
    ) -> str:
        metrics = state.get("system_metrics", {})
        if self._is_emergency(metrics):
            logger.warning("Emergency scenario detected", "drive")
            return "emergency"
        if self._is_resource_tight(metrics):
            logger.info("Resource tight scenario", "drive")
            return "resource_tight"
        if self._is_stable(gaps):
            return "stable_idle"
        return "normal"

    def _is_emergency(self, metrics: Dict[str, float]) -> bool:
        return metrics.get("cpu_percent", 0) > 95.0

    def _is_resource_tight(self, metrics: Dict[str, float]) -> bool:
        return metrics.get("memory_percent", 0) > 85.0

    def _is_stable(self, gaps: Dict[DriveType, float]) -> bool:
        return all(g < 0.1 for g in gaps.values())


class DriveEngine:
    """驱力引擎主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self._init_components(config)
        logger.info("DriveEngine initialized", "drive")

    def _init_components(self, config: Dict[str, Any]) -> None:
        self.safe_calc = SafeDriveCalculator(config.get("safe", {}))
        self.gain_calc = GainDriveCalculator(config.get("gain", {}))
        self.eff_calc = EffDriveCalculator(config.get("eff", {}))
        self.weight_adjuster = DynamicWeightAdjuster(config.get("weights", {}))
        self.scenario_detector = ScenarioDetector(config.get("scenario", {}))

    def compute(
        self, state: Dict[str, Any],
        prediction_error: Optional[float],
        performance_history: List[float],
        agent_cpu: float = 0.0,
        agent_memory: float = 0.0
    ) -> Dict[str, Any]:
        safe_drive = self.safe_calc.calculate(state)
        gain_drive = self.gain_calc.calculate(state, prediction_error)
        eff_drive = self.eff_calc.calculate(state, agent_cpu, agent_memory)
        rewards = self._build_rewards(safe_drive, gain_drive, eff_drive)
        weights = self.weight_adjuster.adjust(state, rewards)
        gaps = self._calc_gaps(safe_drive, gain_drive, eff_drive, weights)
        scenario = self.scenario_detector.detect(state, gaps)
        result = self._build_result(gaps, weights, rewards, scenario)
        logger.info(f"Drive computed: scenario={scenario} total_reward={result['total_reward']:.4f}", "drive")
        return result

    def _build_rewards(
        self, safe: float, gain: float, eff: float
    ) -> Dict[DriveType, float]:
        return {
            DriveType.SAFE: safe,
            DriveType.GAIN: gain,
            DriveType.EFF: eff,
        }

    def _calc_gaps(
        self, safe: float, gain: float, eff: float,
        weights: Dict[DriveType, float]
    ) -> Dict[DriveType, float]:
        min_gap: float = 0.001
        return {
            DriveType.SAFE: max(min_gap, (1.0 - safe) * weights[DriveType.SAFE]),
            DriveType.GAIN: max(min_gap, (1.0 - gain) * weights[DriveType.GAIN]),
            DriveType.EFF: max(min_gap, (1.0 - eff) * weights[DriveType.EFF]),
        }

    def _build_result(
        self, gaps: Dict[DriveType, float],
        weights: Dict[DriveType, float],
        rewards: Dict[DriveType, float],
        scenario: str
    ) -> Dict[str, Any]:
        total_reward = sum(rewards.values()) / 3.0
        return {
            "gaps": gaps,
            "weights": weights,
            "rewards": rewards,
            "scenario": scenario,
            "total_reward": total_reward,
        }

    def should_interrupt(self, drive_state: Dict[str, Any]) -> bool:
        gaps = drive_state.get("gaps", {})
        safe_gap = gaps.get(DriveType.SAFE, 0)
        should = safe_gap > 0.7
        if should:
            logger.warning(f"Interrupt triggered: safe_gap={safe_gap:.4f}", "drive")
        return should

    def get_state(self) -> Dict[str, Any]:
        """获取驱力引擎状态"""
        return {
            "has_safe_calc": hasattr(self.safe_calc, "calculate"),
            "has_gain_calc": hasattr(self.gain_calc, "calculate"),
            "has_eff_calc": hasattr(self.eff_calc, "calculate"),
            "has_weight_adjuster": hasattr(self.weight_adjuster, "adjust"),
            "has_scenario_detector": hasattr(self.scenario_detector, "detect"),
        }

    def reset(self) -> None:
        """重置驱力引擎"""
        logger.debug("[DriveEngine.reset] called", "drive")
        self._init_components(self.config)

    def health_check(self) -> bool:
        """健康检查"""
        logger.debug("[DriveEngine.health_check] called", "drive")
        return True
