"""自我建模与元认知模块"""
import copy
from typing import Any, Dict, Final, List

import numpy as np

from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class SelfModel:
    """自我模型（追踪自身能力、资源、历史表现）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[SelfModel.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.capabilities: Dict[str, float] = dict(config.get("capabilities", {
            "prediction": 0.5,
            "decision": 0.5,
            "learning": 0.5,
        }))
        self.resources: Dict[str, float] = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "task_capacity": float(config.get("task_capacity", 100)),
        }
        self.performance_log: List[float] = []
        self.max_log: int = int(config.get("max_log", 500))
        logger.info(f"SelfModel initialized capabilities={list(self.capabilities.keys())}", "selfaware")

    def update_capability(self, name: str, score: float) -> None:
        logger.debug(f"[SelfModel.update_capability] name={name} score={score:.4f}")
        Validator.require_type(name, str, "name")
        self.capabilities[name] = float(np.clip(score, 0.0, 1.0))

    def update_resource(self, name: str, value: float) -> None:
        logger.debug(f"[SelfModel.update_resource] name={name} value={value:.4f}")
        self.resources[name] = value

    def record_performance(self, performance: float) -> None:
        logger.debug(f"[SelfModel.record_performance] perf={performance:.4f}")
        self.performance_log.append(float(performance))
        if len(self.performance_log) > self.max_log:
            self.performance_log.pop(0)
        logger.debug(f"[SelfModel.record_performance] log_size={len(self.performance_log)}")

    def get_trend(self) -> float:
        if len(self.performance_log) < 2:
            return 0.0
        recent = np.mean(self.performance_log[-10:])
        older = np.mean(self.performance_log[:10]) if len(self.performance_log) >= 10 else self.performance_log[0]
        trend = recent - older
        logger.debug(f"[SelfModel.get_trend] trend={trend:.4f}")
        return float(trend)

    def get_state(self) -> Dict[str, Any]:
        return {
            "capabilities": self.capabilities.copy(),
            "resources": self.resources.copy(),
            "performance_log_size": len(self.performance_log),
            "trend": self.get_trend(),
        }


class ConfidenceEstimator:
    """置信度估计器（基于预测一致性评估置信度）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[ConfidenceEstimator.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.prediction_history: Dict[str, List[float]] = {}
        self.max_history: int = int(config.get("max_history", 50))
        self.confidence_threshold: float = float(config.get("confidence_threshold", 0.7))
        logger.info(f"ConfidenceEstimator initialized threshold={self.confidence_threshold}", "selfaware")

    def record_prediction(self, task_id: str, predicted: float, actual: float) -> None:
        logger.debug(f"[ConfidenceEstimator.record_prediction] task={task_id}")
        if task_id not in self.prediction_history:
            self.prediction_history[task_id] = []
        error = abs(predicted - actual)
        self.prediction_history[task_id].append(error)
        if len(self.prediction_history[task_id]) > self.max_history:
            self.prediction_history[task_id].pop(0)
        logger.debug(f"[ConfidenceEstimator.record_prediction] errors={len(self.prediction_history[task_id])}")

    def estimate(self, task_id: str) -> float:
        logger.debug(f"[ConfidenceEstimator.estimate] task={task_id}")
        errors = self.prediction_history.get(task_id, [])
        if not errors:
            return 0.5
        mean_error = float(np.mean(errors))
        confidence = float(np.exp(-mean_error))
        logger.debug(f"[ConfidenceEstimator.estimate] confidence={confidence:.4f}")
        return confidence

    def is_confident(self, task_id: str) -> bool:
        return self.estimate(task_id) >= self.confidence_threshold

    def get_state(self) -> Dict[str, Any]:
        return {
            "tracked_tasks": len(self.prediction_history),
            "confidence_threshold": self.confidence_threshold,
        }


class IntrospectionEngine:
    """内省引擎（分析决策过程、识别认知偏差）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[IntrospectionEngine.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.decision_log: List[Dict[str, Any]] = []
        self.max_log: int = int(config.get("max_log", 200))
        self.bias_patterns: Dict[str, Any] = dict(config.get("bias_patterns", {
            "overconfidence": {"threshold": 0.9, "count": 0},
            "neglect": {"threshold": 0.1, "count": 0},
        }))
        logger.info(f"IntrospectionEngine initialized patterns={list(self.bias_patterns.keys())}", "selfaware")

    def log_decision(self, decision: Dict[str, Any]) -> None:
        logger.debug("[IntrospectionEngine.log_decision] start")
        Validator.require_type(decision, dict, "decision")
        self.decision_log.append(copy.deepcopy(decision))
        if len(self.decision_log) > self.max_log:
            self.decision_log.pop(0)
        logger.debug(f"[IntrospectionEngine.log_decision] log_size={len(self.decision_log)}")

    def analyze(self) -> Dict[str, Any]:
        logger.debug("[IntrospectionEngine.analyze] start")
        if len(self.decision_log) < 5:
            return {"biases_detected": [], "recommendation": "insufficient data"}
        detected: List[str] = []
        recent = self.decision_log[-10:]
        confidences = [d.get("confidence", 0.5) for d in recent]
        avg_conf = float(np.mean(confidences))
        if avg_conf > self.bias_patterns["overconfidence"]["threshold"]:
            detected.append("overconfidence")
            self.bias_patterns["overconfidence"]["count"] += 1
        if avg_conf < self.bias_patterns["neglect"]["threshold"]:
            detected.append("neglect")
            self.bias_patterns["neglect"]["count"] += 1
        result = {
            "biases_detected": detected,
            "avg_confidence": avg_conf,
            "recommendation": "reduce exploration" if "overconfidence" in detected else "increase exploration" if "neglect" in detected else "maintain",
        }
        logger.debug(f"[IntrospectionEngine.analyze] detected={detected}")
        return result

    def get_state(self) -> Dict[str, Any]:
        return {
            "decision_log_size": len(self.decision_log),
            "bias_patterns": {k: v["count"] for k, v in self.bias_patterns.items()},
        }


class MetaCognition:
    """元认知控制器（监控认知过程、调整策略）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[MetaCognition.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.strategy: str = str(config.get("strategy", "balanced"))
        self.adjustment_history: List[Dict[str, Any]] = []
        self.max_history: int = int(config.get("max_history", 100))
        self.strategies: List[str] = ["conservative", "balanced", "aggressive"]
        logger.info(f"MetaCognition initialized strategy={self.strategy}", "selfaware")

    def evaluate_and_adjust(self, self_model: SelfModel, confidence: ConfidenceEstimator) -> Dict[str, Any]:
        logger.debug("[MetaCognition.evaluate_and_adjust] start")
        trend = self_model.get_trend()
        cap = self_model.capabilities.get("prediction", 0.5)
        old_strategy = self.strategy
        if trend < -0.1 or cap < 0.3:
            self.strategy = "conservative"
        elif trend > 0.1 and cap > 0.7:
            self.strategy = "aggressive"
        else:
            self.strategy = "balanced"
        changed = old_strategy != self.strategy
        record = {
            "old_strategy": old_strategy,
            "new_strategy": self.strategy,
            "trend": trend,
            "capability": cap,
            "changed": changed,
        }
        self.adjustment_history.append(record)
        if len(self.adjustment_history) > self.max_history:
            self.adjustment_history.pop(0)
        logger.info(f"[MetaCognition.evaluate_and_adjust] strategy={self.strategy} changed={changed}", "selfaware")
        return record

    def get_state(self) -> Dict[str, Any]:
        return {
            "current_strategy": self.strategy,
            "adjustment_count": len(self.adjustment_history),
            "available_strategies": self.strategies,
        }


class SelfAwarenessModule:
    """自我建模与元认知主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[SelfAwarenessModule.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.self_model = SelfModel(config.get("self_model", {}))
        logger.debug("[SelfAwarenessModule.__init__] self_model created")
        self.confidence = ConfidenceEstimator(config.get("confidence", {}))
        logger.debug("[SelfAwarenessModule.__init__] confidence created")
        self.introspection = IntrospectionEngine(config.get("introspection", {}))
        logger.debug("[SelfAwarenessModule.__init__] introspection created")
        self.meta = MetaCognition(config.get("meta", {}))
        logger.debug("[SelfAwarenessModule.__init__] meta created")
        logger.info("SelfAwarenessModule initialized", "selfaware")

    def observe_outcome(self, task_id: str, predicted: float, actual: float, performance: float) -> Dict[str, Any]:
        logger.debug(f"[SelfAwarenessModule.observe_outcome] task={task_id}")
        self.confidence.record_prediction(task_id, predicted, actual)
        self.self_model.record_performance(performance)
        conf = self.confidence.estimate(task_id)
        result = {
            "task_id": task_id,
            "confidence": conf,
            "is_confident": self.confidence.is_confident(task_id),
        }
        logger.debug(f"[SelfAwarenessModule.observe_outcome] confidence={conf:.4f}")
        return result

    def reflect(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[SelfAwarenessModule.reflect] start")
        self.introspection.log_decision(decision)
        analysis = self.introspection.analyze()
        adjustment = self.meta.evaluate_and_adjust(self.self_model, self.confidence)
        return {
            "introspection": analysis,
            "adjustment": adjustment,
        }

    def update_capability(self, name: str, score: float) -> None:
        logger.debug(f"[SelfAwarenessModule.update_capability] name={name}")
        self.self_model.update_capability(name, score)

    def update_resource(self, name: str, value: float) -> None:
        logger.debug(f"[SelfAwarenessModule.update_resource] name={name}")
        self.self_model.update_resource(name, value)

    def get_state(self) -> Dict[str, Any]:
        return {
            "self_model": self.self_model.get_state(),
            "confidence": self.confidence.get_state(),
            "introspection": self.introspection.get_state(),
            "meta": self.meta.get_state(),
        }
