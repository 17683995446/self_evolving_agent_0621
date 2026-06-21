"""预测模块"""
from typing import Any, Dict, Final, List, Optional

import numpy as np

from root.left.app.left.src.utils_main.constants import PredictionLevel
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class LowLevelPredictor:
    """低层预测器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.ema_alpha: float = float(config.get("ema_alpha", 0.3))
        self.data: Dict[str, List[float]] = {}
        self.max_data_points: int = int(config.get("max_data_points", 1000))

    def fit(self, metric_name: str, value: float) -> None:
        Validator.require_type(metric_name, str, "metric_name")
        Validator.require_type(value, (int, float), "value")
        self._add_data_point(metric_name, value)

    def _add_data_point(self, metric_name: str, value: float) -> None:
        if metric_name not in self.data:
            self.data[metric_name] = []
        self.data[metric_name].append(value)
        if len(self.data[metric_name]) > self.max_data_points:
            self.data[metric_name].pop(0)

    def predict(self, metric_name: str) -> Optional[Dict[str, Any]]:
        Validator.require_type(metric_name, str, "metric_name")
        data = self.data.get(metric_name, [])
        if len(data) < 2:
            return None
        return self._calc_prediction(metric_name, data)

    def _calc_prediction(
        self, metric_name: str, data: List[float]
    ) -> Dict[str, Any]:
        ema = self._calc_ema(data)
        trend = self._calc_trend(data)
        predicted = ema + trend
        confidence = self._calc_confidence(data)
        logger.debug(f"LowLevel predict {metric_name}: ema={ema:.4f} trend={trend:.4f} pred={predicted:.4f}", "predict")
        return self._build_result(metric_name, predicted, confidence)

    def _calc_ema(self, data: List[float]) -> float:
        ema = data[0]
        for value in data[1:]:
            ema = self.ema_alpha * value + (1 - self.ema_alpha) * ema
        return ema

    def _calc_trend(self, data: List[float]) -> float:
        if len(data) < 10:
            return 0.0
        recent = data[-10:]
        return float(recent[-1] - recent[0]) / len(recent)

    def _calc_confidence(self, data: List[float]) -> float:
        return float(min(1.0, len(data) / 100.0))

    def _build_result(
        self, metric_name: str, predicted: float, confidence: float
    ) -> Dict[str, Any]:
        return {
            "target_metric": metric_name,
            "predicted_value": predicted,
            "confidence": confidence,
            "level": PredictionLevel.LOW,
        }

    def predict_batch(
        self, current_metrics: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for metric_name in current_metrics:
            pred = self.predict(metric_name)
            if pred is not None:
                results.append(pred)
        logger.debug(f"LowLevel batch predict: {len(results)}/{len(current_metrics)} metrics", "predict")
        return results


class MidLevelPredictor:
    """中层预测器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.window_size: int = int(config.get("window_size", 10))
        self.horizon: int = int(config.get("horizon", 3))
        self.data: Dict[str, List[float]] = {}
        self.models: Dict[str, Any] = {}

    def fit(self, metric_name: str, value: float) -> None:
        Validator.require_type(metric_name, str, "metric_name")
        if metric_name not in self.data:
            self.data[metric_name] = []
        self.data[metric_name].append(value)
        self._train_model(metric_name)

    def _train_model(self, metric_name: str) -> None:
        window = self.data[metric_name]
        if len(window) < self.window_size + self.horizon:
            return
        x_matrix, y_vector = self._build_training_data(window)
        if len(x_matrix) < 3:
            return
        self.models[metric_name] = self._ridge_solve(x_matrix, y_vector)
        logger.debug(f"MidLevel model trained: {metric_name} samples={len(x_matrix)}", "predict")

    def _build_training_data(
        self, window: List[float]
    ) -> tuple:
        x_matrix: List[List[float]] = []
        y_vector: List[float] = []
        for i in range(len(window) - self.horizon):
            features = self._extract_features(window[max(0, i - self.window_size):i])
            x_matrix.append(features)
            y_vector.append(window[i + self.horizon])
        return x_matrix, y_vector

    def _extract_features(self, window: List[float]) -> List[float]:
        if not window:
            return [0.0] * 5
        return self._build_features(window)

    def _build_features(self, window: List[float]) -> List[float]:
        mean = float(np.mean(window))
        std = float(np.std(window)) + 1e-8
        diff = float(window[-1] - window[0]) if len(window) > 1 else 0.0
        return [mean, std, float(window[-1]), diff, float(len(window))]

    def _ridge_solve(
        self, x_matrix: List[List[float]], y_vector: List[float]
    ) -> Any:
        x = np.array(x_matrix)
        y = np.array(y_vector)
        xtx = x.T @ x + 0.1 * np.eye(x.shape[1])
        xty = x.T @ y
        try:
            return np.linalg.solve(xtx, xty)
        except np.linalg.LinAlgError:
            logger.warning("Singular matrix in ridge solve, using pseudo-inverse", "predict")
            return np.linalg.pinv(xtx) @ xty

    def predict(self, metric_name: str) -> Optional[Dict[str, Any]]:
        Validator.require_type(metric_name, str, "metric_name")
        model = self.models.get(metric_name)
        if model is None:
            return None
        window = self.data.get(metric_name, [])
        features = self._extract_features(window[-self.window_size:])
        predicted = float(np.dot(model, features))
        logger.debug(f"MidLevel predict {metric_name}: pred={predicted:.4f}", "predict")
        return self._build_result(metric_name, predicted)

    def _build_result(
        self, metric_name: str, predicted: float
    ) -> Dict[str, Any]:
        return {
            "target_metric": metric_name,
            "predicted_value": predicted,
            "confidence": 0.5,
            "level": PredictionLevel.MID,
        }


class HighLevelPredictor:
    """高层预测器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.n_clusters: int = int(config.get("n_clusters", 5))
        self.data: List[List[float]] = []
        self.cluster_centers: Optional[Any] = None
        self.initialized: bool = False
        self.min_samples: int = int(config.get("min_samples", 50))

    def fit(self, feature_vector: List[float]) -> None:
        Validator.require_type(feature_vector, list, "feature_vector")
        self.data.append(feature_vector)
        if len(self.data) >= self.min_samples:
            self._update_clusters()

    def _update_clusters(self) -> None:
        data_array = np.array(self.data)
        self.cluster_centers = self._kmeans(data_array, self.n_clusters)
        self.initialized = True
        logger.info(f"HighLevel clusters updated: n={self.n_clusters} samples={len(self.data)}", "predict")

    def _kmeans(
        self, data: Any, k: int, max_iter: int = 10
    ) -> Any:
        n_samples = len(data)
        if n_samples < k:
            logger.warning(f"Not enough samples ({n_samples}) for k={k}, using all samples as centers", "predict")
            return data.copy()
        indices = np.random.choice(n_samples, k, replace=False)
        centers = data[indices].copy()
        return self._kmeans_loop(data, centers, k, max_iter)

    def _kmeans_loop(
        self, data: Any, centers: Any, k: int, max_iter: int
    ) -> Any:
        for _ in range(max_iter):
            labels = self._assign_labels(data, centers)
            new_centers = self._update_centers(data, labels, k)
            if np.allclose(centers, new_centers):
                break
            centers = new_centers
        return centers

    def _assign_labels(self, data: Any, centers: Any) -> Any:
        distances = np.sqrt(((data[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2))
        return np.argmin(distances, axis=1)

    def _update_centers(
        self, data: Any, labels: Any, k: int
    ) -> Any:
        centers = np.zeros((k, data.shape[1]))
        for i in range(k):
            mask = labels == i
            if mask.any():
                centers[i] = data[mask].mean(axis=0)
        return centers

    def predict(
        self, feature_vector: List[float]
    ) -> Optional[Dict[str, Any]]:
        Validator.require_type(feature_vector, list, "feature_vector")
        if not self.initialized or self.cluster_centers is None:
            return None
        state = self._discretize_state(feature_vector)
        logger.debug(f"HighLevel predict: state={state}", "predict")
        return self._build_result(state)

    def _discretize_state(self, feature_vector: List[float]) -> int:
        distances = np.sqrt(((self.cluster_centers - feature_vector) ** 2).sum(axis=1))
        return int(np.argmin(distances))

    def _build_result(self, state: int) -> Dict[str, Any]:
        return {
            "target_metric": "system_state",
            "predicted_value": state,
            "confidence": 0.3,
            "level": PredictionLevel.HIGH,
        }


class PredictionModule:
    """预测模块主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.low_level = LowLevelPredictor(config.get("low_level", {}))
        self.mid_level = MidLevelPredictor(config.get("mid_level", {}))
        self.high_level = HighLevelPredictor(config.get("high_level", {}))
        self.error_history: Dict[str, List[float]] = {}
        logger.info("PredictionModule initialized", "predict")

    def predict(self, state: Dict[str, Any]) -> Dict[PredictionLevel, List[Dict[str, Any]]]:
        Validator.require_type(state, dict, "state")
        metrics = state.get("system_metrics", {})
        feature_vector = state.get("feature_vector", [])
        return self._do_predict(metrics, feature_vector)

    def _do_predict(
        self, metrics: Dict[str, float], feature_vector: List[float]
    ) -> Dict[PredictionLevel, List[Dict[str, Any]]]:
        low_preds = self.low_level.predict_batch(metrics)
        self._fit_mid_level(metrics)
        mid_preds = self._predict_mid_level(metrics)
        self.high_level.fit(feature_vector)
        high_pred = self.high_level.predict(feature_vector)
        result = self._build_predictions(low_preds, mid_preds, high_pred)
        logger.info(f"Predictions: low={len(low_preds)} mid={len(mid_preds)} high={1 if high_pred else 0}", "predict")
        return result

    def _fit_mid_level(self, metrics: Dict[str, float]) -> None:
        for name, value in metrics.items():
            self.mid_level.fit(name, value)

    def _predict_mid_level(
        self, metrics: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for name in metrics:
            pred = self.mid_level.predict(name)
            if pred is not None:
                results.append(pred)
        return results

    def _build_predictions(
        self, low: List[Dict[str, Any]],
        mid: List[Dict[str, Any]],
        high: Optional[Dict[str, Any]]
    ) -> Dict[PredictionLevel, List[Dict[str, Any]]]:
        result: Dict[PredictionLevel, List[Dict[str, Any]]] = {
            PredictionLevel.LOW: low,
            PredictionLevel.MID: mid,
            PredictionLevel.HIGH: [high] if high else [],
        }
        return result

    def evaluate(
        self, predictions: Dict[PredictionLevel, List[Dict[str, Any]]],
        actual_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        errors: List[Dict[str, Any]] = []
        for level, preds in predictions.items():
            for pred in preds:
                error = self._compute_error(pred, actual_state)
                errors.append(error)
        logger.info(f"Evaluation: {len(errors)} predictions evaluated", "predict")
        return errors

    def _compute_error(
        self, pred: Dict[str, Any], actual_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        metric = pred.get("target_metric", "")
        predicted_value = pred.get("predicted_value", 0.0)
        actual_value = self._get_actual(metric, actual_state, predicted_value)
        error = abs(predicted_value - actual_value)
        error_rate = error / max(abs(actual_value), 1e-8)
        return {
            "metric": metric,
            "predicted": predicted_value,
            "actual": actual_value,
            "error": error,
            "error_rate": min(error_rate, 10.0),
        }

    def _get_actual(
        self, metric: str, actual_state: Dict[str, Any], default: float
    ) -> float:
        return actual_state.get("system_metrics", {}).get(metric, default)

    def get_average_error(self) -> float:
        if not self.error_history:
            return 1.0
        all_errors = []
        for errors in self.error_history.values():
            all_errors.extend(errors)
        if not all_errors:
            return 1.0
        return float(sum(all_errors) / len(all_errors))

    def get_state(self) -> Dict[str, Any]:
        """获取预测模块状态"""
        total_errors = sum(len(v) for v in self.error_history.values())
        return {
            "error_history_keys": list(self.error_history.keys()),
            "error_history_total": total_errors,
        }

    def reset(self) -> None:
        """重置预测模块"""
        logger.debug("[PredictionModule.reset] called", "predict")
        self.error_history.clear()
        self.low_level = LowLevelPredictor(self.config.get("low_level", {}))
        self.mid_level = MidLevelPredictor(self.config.get("mid_level", {}))
        self.high_level = HighLevelPredictor(self.config.get("high_level", {}))

    def health_check(self) -> bool:
        """健康检查"""
        logger.debug("[PredictionModule.health_check] called", "predict")
        return True
