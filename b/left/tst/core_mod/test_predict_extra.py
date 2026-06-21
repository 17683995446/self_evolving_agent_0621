"""预测模块补充测试"""
from root.left.app.left.src.core_mod.predict import (
    LowLevelPredictor, MidLevelPredictor, HighLevelPredictor, PredictionModule,
)


class TestLowLevelPredictorExtra:
    """测试LowLevelPredictor额外路径"""

    def test_predict_single_data(self) -> None:
        pred = LowLevelPredictor({})
        pred.fit("cpu", 50.0)
        assert pred.predict("cpu") is None

    def test_predict_batch_empty(self) -> None:
        pred = LowLevelPredictor({})
        result = pred.predict_batch({})
        assert result == []


class TestMidLevelPredictorExtra:
    """测试MidLevelPredictor额外路径"""

    def test_predict_no_model(self) -> None:
        pred = MidLevelPredictor({})
        assert pred.predict("cpu") is None


class TestHighLevelPredictorExtra:
    """测试HighLevelPredictor额外路径"""

    def test_predict_not_initialized(self) -> None:
        pred = HighLevelPredictor({})
        assert pred.predict([1.0, 2.0]) is None


class TestPredictionModuleExtra:
    """测试PredictionModule额外路径"""

    def test_evaluate_empty(self) -> None:
        mod = PredictionModule({})
        result = mod.evaluate({}, {})
        assert result == []

    def test_get_average_error_with_history(self) -> None:
        mod = PredictionModule({})
        mod.error_history["cpu"] = [0.1, 0.2]
        result = mod.get_average_error()
        assert abs(result - 0.15) < 0.001
