"""驱力引擎补充测试"""
from root.left.app.left.src.core_mod.drive import (
    EffDriveCalculator, DynamicWeightAdjuster, ScenarioDetector,
)


class TestEffDriveCalculatorExtra:
    """测试EffDriveCalculator额外路径"""

    def test_empty_state(self) -> None:
        calc = EffDriveCalculator({})
        result = calc.calculate({}, 0.0, 0.0)
        assert result == 1.0


class TestDynamicWeightAdjusterExtra:
    """测试DynamicWeightAdjuster额外路径"""

    def test_normalize_weights_zero(self) -> None:
        adj = DynamicWeightAdjuster({})
        adj.weights = {}
        adj._normalize_weights()
        assert adj.weights == {}


class TestScenarioDetectorExtra:
    """测试ScenarioDetector额外路径"""

    def test_detect_emergency(self) -> None:
        det = ScenarioDetector({})
        state = {"system_metrics": {"cpu_percent": 96.0}}
        result = det.detect(state, {})
        assert result == "emergency"

    def test_detect_resource_tight(self) -> None:
        det = ScenarioDetector({})
        state = {"system_metrics": {"memory_percent": 86.0}}
        result = det.detect(state, {})
        assert result == "resource_tight"

    def test_detect_stable(self) -> None:
        det = ScenarioDetector({})
        state = {"system_metrics": {"cpu_percent": 50.0}}
        result = det.detect(state, {"safe": 0.05, "gain": 0.05})
        assert result == "stable_idle"
