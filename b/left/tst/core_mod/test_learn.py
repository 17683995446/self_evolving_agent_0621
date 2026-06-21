"""自适应学习模块单元测试"""
import pytest

from root.left.app.left.src.core_mod.learn import (
    IncrementalSGDRegressor, AutoFeatureEngineer,
    ModelSelector, OverfitDetector, AdaptiveLearner,
)
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestIncrementalSGDRegressor:
    """测试增量SGD"""

    def test_normal_fit_predict(self) -> None:
        sgd = IncrementalSGDRegressor({"learning_rate": 0.1})
        for _ in range(100):
            sgd.partial_fit([1.0, 2.0], 5.0)
        pred = sgd.predict([1.0, 2.0])
        assert abs(pred - 5.0) < 1.0

    def test_weights_converge(self) -> None:
        sgd = IncrementalSGDRegressor({"learning_rate": 0.001, "regularization": 0.01})
        for i in range(1000):
            x = [float(i % 10), float((i + 1) % 10)]
            y = 2.0 * x[0] + 3.0 * x[1] + 1.0
            sgd.partial_fit(x, y)
        pred = sgd.predict([5.0, 5.0])
        assert abs(pred - 26.0) < 3.0

    def test_uninitialized_predict(self) -> None:
        sgd = IncrementalSGDRegressor({})
        assert sgd.predict([1.0, 2.0]) == 0.0

    def test_get_weights(self) -> None:
        sgd = IncrementalSGDRegressor({})
        sgd.partial_fit([1.0], 2.0)
        state = sgd.get_weights()
        assert state["n_samples"] == 1
        assert len(state["weights"]) == 1

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            IncrementalSGDRegressor(None)


class TestAutoFeatureEngineer:
    """测试自动特征工程"""

    def test_normal_transform(self) -> None:
        fe = AutoFeatureEngineer({"max_degree": 2})
        result = fe.fit_transform([1.0, 2.0])
        assert len(result) > 2

    def test_polynomial_features(self) -> None:
        fe = AutoFeatureEngineer({"max_degree": 2, "include_interactions": False})
        result = fe.fit_transform([2.0])
        assert 4.0 in result

    def test_interaction_features(self) -> None:
        fe = AutoFeatureEngineer({"max_degree": 2, "include_interactions": True})
        result = fe.fit_transform([2.0, 3.0])
        assert 6.0 in result

    def test_standardize(self) -> None:
        fe = AutoFeatureEngineer({})
        result = fe.fit_transform([1.0, 2.0])
        assert all(isinstance(v, float) for v in result)


class TestModelSelector:
    """测试模型选择器"""

    def test_aic_selection(self) -> None:
        ms = ModelSelector({"criterion": "aic"})
        score = ms.evaluate("m1", sse=10.0, n_params=3, n_samples=100)
        assert isinstance(score, float)
        assert score != float('inf')

    def test_bic_selection(self) -> None:
        ms = ModelSelector({"criterion": "bic"})
        score = ms.evaluate("m1", sse=10.0, n_params=3, n_samples=100)
        assert isinstance(score, float)
        assert score != float('inf')

    def test_select_best(self) -> None:
        ms = ModelSelector({})
        candidates = [
            {"name": "m1", "score": 10.0},
            {"name": "m2", "score": 5.0},
        ]
        assert ms.select_best(candidates) == "m2"

    def test_select_best_empty(self) -> None:
        ms = ModelSelector({})
        assert ms.select_best([]) is None

    def test_invalid_n_samples(self) -> None:
        ms = ModelSelector({})
        score = ms.evaluate("m1", sse=10.0, n_params=10, n_samples=5)
        assert score == float('inf')


class TestOverfitDetector:
    """测试过拟合检测器"""

    def test_normal_no_overfit(self) -> None:
        od = OverfitDetector({"threshold": 0.5})
        for _ in range(20):
            od.add_errors(0.1, 0.12)
        assert od.is_overfitting() is False

    def test_overfit_detected(self) -> None:
        od = OverfitDetector({"threshold": 0.1})
        for _ in range(20):
            od.add_errors(0.05, 0.2)
        assert od.is_overfitting() is True

    def test_not_enough_data(self) -> None:
        od = OverfitDetector({})
        od.add_errors(0.1, 1.0)
        assert od.is_overfitting() is False

    def test_get_gap(self) -> None:
        od = OverfitDetector({})
        for _ in range(20):
            od.add_errors(0.1, 0.2)
        gap = od.get_gap()
        assert abs(gap - 0.1) < 0.01


class TestAdaptiveLearner:
    """测试自适应学习器"""

    def test_normal_learn(self) -> None:
        learner = AdaptiveLearner({})
        record = learner.learn([1.0, 2.0], 5.0)
        assert "train_error" in record

    def test_predict_after_learn(self) -> None:
        learner = AdaptiveLearner({"sgd": {"learning_rate": 0.01}})
        for _ in range(200):
            learner.learn([1.0, 2.0], 5.0)
        pred = learner.predict([1.0, 2.0])
        assert abs(pred - 5.0) < 1.0

    def test_overfit_detection(self) -> None:
        learner = AdaptiveLearner({"overfit": {"threshold": 0.01}})
        for _ in range(20):
            learner.learn([1.0], 2.0, validation_target=5.0)
        assert learner.check_overfitting() is True

    def test_learning_state(self) -> None:
        learner = AdaptiveLearner({})
        learner.learn([1.0], 2.0)
        state = learner.get_learning_state()
        assert "sgd" in state
        assert "history_size" in state

    def test_history_bounded(self) -> None:
        learner = AdaptiveLearner({"max_history": 5})
        for _ in range(10):
            learner.learn([1.0], 2.0)
        assert len(learner.history) <= 5

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            AdaptiveLearner(None)
