"""效果验证器

在执行动作前后采集关键指标，评估动作是否产生预期效果。
"""
from typing import Any, Dict, Final, List, Optional

from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class EffectVerifier:
    """效果验证器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[EffectVerifier.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.metrics: Dict[str, List[float]] = {}
        self.max_points: int = int(config.get("max_points", 10))
        logger.info(f"EffectVerifier initialized max_points={self.max_points}", "effect")

    def capture_before(self, name: str, value: float) -> None:
        logger.debug(f"[EffectVerifier.capture_before] {name}={value}", "effect")
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)
        if len(self.metrics[name]) > self.max_points:
            self.metrics[name].pop(0)

    def capture_after(self, name: str, value: float) -> Dict[str, Any]:
        logger.debug(f"[EffectVerifier.capture_after] {name}={value}", "effect")
        before = self._get_before(name)
        delta = value - before if before is not None else 0.0
        improvement = self._evaluate(name, before, value)
        result = {
            "metric": name,
            "before": before,
            "after": value,
            "delta": delta,
            "improved": improvement,
        }
        self.capture_before(name, value)
        logger.info(f"[EffectVerifier.capture_after] result={result}", "effect")
        return result

    def _get_before(self, name: str) -> Optional[float]:
        series = self.metrics.get(name, [])
        if len(series) < 2:
            return series[0] if series else None
        return series[-2]

    def _evaluate(self, name: str, before: Optional[float], after: float) -> bool:
        if before is None:
            return True
        lower_is_better = any(keyword in name for keyword in ["error", "latency", "cpu", "memory", "disk"])
        if lower_is_better:
            return after < before
        return after > before

    def get_summary(self) -> Dict[str, Any]:
        return {
            "metrics": list(self.metrics.keys()),
            "latest": {name: values[-1] if values else None for name, values in self.metrics.items()},
        }

    def get_state(self) -> Dict[str, Any]:
        """获取验证器状态"""
        return {
            "max_points": self.max_points,
            "metric_count": len(self.metrics),
            "summary": self.get_summary(),
        }

    def reset(self) -> None:
        """重置验证器"""
        logger.debug("[EffectVerifier.reset] called", "effect")
        self.metrics.clear()

    def health_check(self) -> bool:
        """健康检查"""
        logger.debug("[EffectVerifier.health_check] called", "effect")
        return self.max_points > 0
