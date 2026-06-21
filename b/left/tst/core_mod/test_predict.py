"""预测模块单元测试"""
import pytest
from root.left.app.left.src.core_mod.predict import (
    LowLevelPredictor, MidLevelPredictor, HighLevelPredictor, PredictionModule,
)
from root.left.app.left.src.utils_main.constants import PredictionLevel
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestLowLevelPredictor:
    """测试LowLevelPredictor"""

    def test_normal_fit_predict(self) -> None:
        pred = LowLevelPredictor({})
        pred.fit("cpu", 50.0)
        pred.fit("cpu", 55.0)
        result = pred.predict("cpu")
        assert result is not None
        assert result["target_metric"] == "cpu"

    def test_empty_predict(self) -> None:
        pred = LowLevelPredictor({})
        assert pred.predict("cpu") is None

    def test_boundary_batch(self) -> None:
        pred = LowLevelPredictor({})
        pred.fit("cpu", 50.0)
        pred.fit("cpu", 55.0)
        result = pred.predict_batch({"cpu": 50.0})
        assert len(result) == 1

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            LowLevelPredictor(None)

    def test_confidence_range(self) -> None:
        pred = LowLevelPredictor({})
        for i in range(15):
            pred.fit("cpu", float(i))
        result = pred.predict("cpu")
        assert 0.0 <= result["confidence"] <= 1.0

    def test_predict_value_range(self) -> None:
        pred = LowLevelPredictor({})
        pred.fit("cpu", 50.0)
        pred.fit("cpu", 55.0)
        result = pred.predict("cpu")
        assert isinstance(result["predicted_value"], float)


class TestMidLevelPredictor:
    """测试MidLevelPredictor"""

    def test_normal_fit_predict(self) -> None:
        pred = MidLevelPredictor({"window_size": 5})
        for i in range(10):
            pred.fit("cpu", float(i))
        result = pred.predict("cpu")
        assert result is not None

    def test_empty_predict(self) -> None:
        pred = MidLevelPredictor({})
        assert pred.predict("cpu") is None

    def test_boundary_small_window(self) -> None:
        pred = MidLevelPredictor({"window_size": 3, "horizon": 1})
        for i in range(10):
            pred.fit("cpu", float(i))
        result = pred.predict("cpu")
        assert result is not None

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            MidLevelPredictor(None)

    def test_extract_features_short(self) -> None:
        pred = MidLevelPredictor({})
        features = pred._extract_features([1.0, 2.0])
        assert len(features) == 5

    def test_ridge_solve(self) -> None:
        import numpy as np
        pred = MidLevelPredictor({})
        x = np.array([[1.0, 2.0], [2.0, 3.0], [3.0, 4.0]])
        y = np.array([1.0, 2.0, 3.0])
        coef = pred._ridge_solve(x, y)
        assert len(coef) == 2


class TestHighLevelPredictor:
    """测试HighLevelPredictor"""

    def test_normal_fit_predict(self) -> None:
        pred = HighLevelPredictor({"n_clusters": 3})
        for i in range(60):
            pred.fit([float(i % 10), float(i % 5)])
        result = pred.predict([5.0, 2.0])
        assert result is not None

    def test_empty_predict(self) -> None:
        pred = HighLevelPredictor({})
        assert pred.predict([1.0, 2.0]) is None

    def test_boundary_not_initialized(self) -> None:
        pred = HighLevelPredictor({})
        pred.fit([1.0, 2.0])
        assert pred.predict([1.0, 2.0]) is None

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            HighLevelPredictor(None)

    def test_discretize_state(self) -> None:
        pred = HighLevelPredictor({"n_clusters": 2})
        pred.cluster_centers = __import__("numpy").array([[0.0, 0.0], [10.0, 10.0]])
        pred.initialized = True
        result = pred._discretize_state([0.1, 0.1])
        assert result in [0, 1]

    def test_update_clusters(self) -> None:
        pred = HighLevelPredictor({"n_clusters": 2})
        for i in range(10):
            pred.fit([float(i), float(i)])
        pred._update_clusters()
        assert pred.initialized is True


class TestPredictionModule:
    """测试PredictionModule"""

    def test_normal_predict(self) -> None:
        mod = PredictionModule({})
        state = {"system_metrics": {"cpu_percent": 50.0}, "feature_vector": [0.5, 0.5]}
        result = mod.predict(state)
        assert PredictionLevel.LOW in result

    def test_empty_state(self) -> None:
        mod = PredictionModule({})
        result = mod.predict({})
        assert result[PredictionLevel.LOW] == []

    def test_boundary_evaluate(self) -> None:
        mod = PredictionModule({})
        preds = {PredictionLevel.LOW: [{"target_metric": "cpu_percent", "predicted_value": 50.0, "level": PredictionLevel.LOW}]}
        actual = {"system_metrics": {"cpu_percent": 55.0}}
        errors = mod.evaluate(preds, actual)
        assert len(errors) == 1

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            PredictionModule(None)

    def test_average_error_empty(self) -> None:
        mod = PredictionModule({})
        assert mod.get_average_error() == 1.0

    def test_compute_error(self) -> None:
        mod = PredictionModule({})
        pred = {"target_metric": "cpu", "predicted_value": 100.0, "level": PredictionLevel.LOW}
        actual = {"system_metrics": {"cpu": 90.0}}
        error = mod._compute_error(pred, actual)
        assert error["error_rate"] > 0.0
