"""环境感知模块"""
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from typing import Any, Dict, Final, List, Optional

import numpy as np

from root.left.app.left.src.utils_main.constants import MetricType
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class BaseCollector(ABC):
    """采集器抽象基类"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.enabled: bool = bool(config.get("enabled", True))
        self.sample_interval: float = float(config.get("interval", 1.0))
        self.history: deque = deque(
            maxlen=int(config.get("history_size", 1000))
        )
        self.last_collect_time: float = 0.0

    @abstractmethod
    def collect(self) -> List[Any]:
        raise NotImplementedError

    @abstractmethod
    def validate(self, metrics: List[Any]) -> bool:
        raise NotImplementedError

    def should_collect(self) -> bool:
        import time
        elapsed = time.time() - self.last_collect_time
        return elapsed >= self.sample_interval


class SystemCollector(BaseCollector):
    """系统层采集器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.cpu_count: int = self._get_cpu_count()

    def _get_cpu_count(self) -> int:
        try:
            import psutil
            return psutil.cpu_count() or 1
        except ImportError:
            logger.warning("psutil not available", "sensory")
            return 1

    def collect(self) -> List[Any]:
        import time
        if not self.should_collect():
            return []
        timestamp = time.time()
        metrics = self._fetch_metrics(timestamp)
        self.last_collect_time = timestamp
        logger.debug(f"SystemCollector collected {len(metrics)} metrics", "sensory")
        return metrics

    def _fetch_metrics(self, timestamp: float) -> List[Any]:
        metrics: List[Any] = []
        try:
            import psutil
            metrics.append(self._build_cpu_metric(timestamp, psutil))
            metrics.append(self._build_memory_metric(timestamp, psutil))
        except Exception as error:
            logger.error(f"Collection failed: {error}", "sensory")
        return metrics

    def _build_cpu_metric(
        self, timestamp: float, psutil: Any
    ) -> Dict[str, Any]:
        value = float(psutil.cpu_percent(interval=0.1))
        logger.debug(f"CPU metric: {value}%", "sensory")
        return {
            "metric_type": MetricType.SYSTEM,
            "name": "cpu_percent",
            "value": value,
            "timestamp": timestamp,
            "source": "psutil",
        }

    def _build_memory_metric(
        self, timestamp: float, psutil: Any
    ) -> Dict[str, Any]:
        memory = psutil.virtual_memory()
        value = float(memory.percent)
        logger.debug(f"Memory metric: {value}%", "sensory")
        return {
            "metric_type": MetricType.SYSTEM,
            "name": "memory_percent",
            "value": value,
            "timestamp": timestamp,
            "source": "psutil",
        }

    def validate(self, metrics: List[Any]) -> bool:
        for metric in metrics:
            if metric.get("name") == "cpu_percent":
                value = metric.get("value", 0)
                if not (0 <= value <= 100):
                    logger.warning(f"Invalid cpu_percent: {value}", "sensory")
                    return False
        return True


class StateNormalizer:
    """状态标准化处理器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.running_stats: defaultdict = defaultdict(
            lambda: {"mean": 0.0, "var": 1.0, "count": 0}
        )
        self.feature_order: List[str] = config.get(
            "feature_order",
            ["cpu_percent", "memory_percent"]
        )

    def update_stats(self, metric_name: str, value: float) -> None:
        Validator.require_type(metric_name, str, "metric_name")
        stats = self.running_stats[metric_name]
        self._apply_welford(stats, value)

    def _apply_welford(
        self, stats: Dict[str, Any], value: float
    ) -> None:
        count = stats["count"]
        new_count = count + 1
        delta = value - stats["mean"]
        new_mean = stats["mean"] + delta / new_count
        delta2 = value - new_mean
        new_var = self._calc_var(stats, count, delta, delta2, new_count)
        self._update_stats(stats, new_mean, new_var, new_count)

    def _calc_var(
        self, stats: Dict[str, Any], count: int,
        delta: float, delta2: float, new_count: int
    ) -> float:
        if new_count <= 1:
            return 1.0
        return (stats["var"] * count + delta * delta2) / new_count

    def _update_stats(
        self, stats: Dict[str, Any], mean: float, var: float, count: int
    ) -> None:
        stats["mean"] = mean
        stats["var"] = var
        stats["count"] = count

    def normalize(self, metric_name: str, value: float) -> float:
        stats = self.running_stats[metric_name]
        if stats["count"] < 2:
            return 0.0
        std = np.sqrt(stats["var"]) + 1e-8
        result = float((value - stats["mean"]) / std)
        logger.debug(f"Normalize {metric_name}: raw={value:.4f} norm={result:.4f}", "sensory")
        return result

    def clip_outliers(self, value: float) -> float:
        return float(np.clip(value, -3.0, 3.0))


class NoiseFilter:
    """噪声过滤器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.ema_alpha: float = float(config.get("ema_alpha", 0.3))
        Validator.require_range(self.ema_alpha, 0.01, 0.99, "ema_alpha")
        self.ema_values: Dict[str, float] = {}

    def apply_ema(self, metric_name: str, value: float) -> float:
        Validator.require_type(metric_name, str, "metric_name")
        if metric_name not in self.ema_values:
            self.ema_values[metric_name] = value
            logger.debug(f"EMA init {metric_name}={value:.4f}", "sensory")
            return value
        prev = self.ema_values[metric_name]
        ema = self.ema_alpha * value + (1 - self.ema_alpha) * prev
        self.ema_values[metric_name] = ema
        logger.debug(f"EMA {metric_name}: raw={value:.4f} ema={ema:.4f}", "sensory")
        return ema


class SensoryModule:
    """环境感知模块主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.collectors: Dict[str, BaseCollector] = {}
        self.normalizer = StateNormalizer(config.get("normalizer", {}))
        self.noise_filter = NoiseFilter(config.get("noise_filter", {}))
        self.current_state: Optional[Dict[str, Any]] = None
        self.state_history: deque = deque(maxlen=10000)
        self._init_collectors()
        logger.info("SensoryModule initialized", "sensory")

    def _init_collectors(self) -> None:
        configs = self.config.get("collectors", {})
        if configs.get("system", {}).get("enabled", True):
            self.collectors["system"] = SystemCollector(
                configs.get("system", {})
            )

    def perceive(self) -> Dict[str, Any]:
        import time
        timestamp = time.time()
        metrics = self._collect_all()
        state = self._build_state(timestamp, metrics)
        self.current_state = state
        self.state_history.append(state)
        logger.info(f"Perceived state: metrics={len(metrics)} features={len(state.get('feature_vector', []))}", "sensory")
        return state

    def _build_state(
        self, timestamp: float, metrics: List[Any]
    ) -> Dict[str, Any]:
        categorized = self._categorize_metrics(metrics)
        features = self._build_features(categorized)
        return {
            "timestamp": timestamp,
            "system_metrics": categorized.get("system", {}),
            "feature_vector": features,
        }

    def _collect_all(self) -> List[Any]:
        all_metrics: List[Any] = []
        for name, collector in self.collectors.items():
            try:
                metrics = collector.collect()
                if collector.validate(metrics):
                    all_metrics.extend(metrics)
            except Exception as error:
                logger.error(f"Collector {name} error: {error}", "sensory")
        return all_metrics

    def _categorize_metrics(
        self, metrics: List[Any]
    ) -> Dict[str, Dict[str, float]]:
        categorized: Dict[str, Dict[str, float]] = defaultdict(dict)
        for metric in metrics:
            key = metric["metric_type"].value
            name = metric["name"]
            categorized[key][name] = metric["value"]
            self.normalizer.update_stats(name, metric["value"])
        return categorized

    def _build_features(
        self, categorized: Dict[str, Dict[str, float]]
    ) -> List[float]:
        feature_vector: List[float] = []
        for feature_name in self.normalizer.feature_order:
            value = categorized.get("system", {}).get(feature_name, 0.0)
            filtered = self.noise_filter.apply_ema(feature_name, value)
            normalized = self.normalizer.normalize(feature_name, filtered)
            clipped = self.normalizer.clip_outliers(normalized)
            feature_vector.append(clipped)
        return feature_vector

    def get_current_state(self) -> Optional[Dict[str, Any]]:
        return self.current_state

    def get_state(self) -> Dict[str, Any]:
        """获取感知模块状态"""
        return {
            "collector_count": len(self.collectors),
            "state_history_len": len(self.state_history),
            "has_current_state": self.current_state is not None,
        }

    def reset(self) -> None:
        """重置感知模块"""
        logger.debug("[SensoryModule.reset] called", "sensory")
        self.current_state = None
        self.state_history.clear()
        self.normalizer = StateNormalizer(self.config.get("normalizer", {}))
        self.noise_filter = NoiseFilter(self.config.get("noise_filter", {}))
        self._init_collectors()

    def health_check(self) -> bool:
        """健康检查"""
        logger.debug("[SensoryModule.health_check] called", "sensory")
        return True
