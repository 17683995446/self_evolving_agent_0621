"""驱力引擎模块单元测试"""
import pytest
from root.left.app.left.src.core_mod.drive import (
    SafeDriveCalculator, GainDriveCalculator, EffDriveCalculator,
    DynamicWeightAdjuster, DriveEngine,
)
from root.left.app.left.src.utils_main.constants import DriveType
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestSafeDriveCalculator:
    """测试SafeDriveCalculator"""

    def test_normal_low_risk(self) -> None:
        calc = SafeDriveCalculator({"thresholds": {"cpu_critical": 90.0}})
        state = {"system_metrics": {"cpu_percent": 50.0}}
        assert calc.calculate(state) == 1.0

    def test_empty_state(self) -> None:
        calc = SafeDriveCalculator({})
        assert calc.calculate({}) == 1.0

    def test_boundary_critical(self) -> None:
        calc = SafeDriveCalculator({"thresholds": {"cpu_critical": 80.0}})
        state = {"system_metrics": {"cpu_percent": 80.0}}
        result = calc.calculate(state)
        assert result == 0.5

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            SafeDriveCalculator(None)

    def test_high_risk(self) -> None:
        calc = SafeDriveCalculator({"risk_weights": {"cpu_high": 0.5}})
        state = {"system_metrics": {"cpu_percent": 90.0}}
        result = calc.calculate(state)
        assert result < 1.0

    def test_memory_risk(self) -> None:
        calc = SafeDriveCalculator({"thresholds": {"memory_critical": 80.0}})
        state = {"system_metrics": {"memory_percent": 90.0}}
        result = calc.calculate(state)
        assert result < 1.0


class TestGainDriveCalculator:
    """测试GainDriveCalculator"""

    def test_normal_none_error(self) -> None:
        calc = GainDriveCalculator({})
        state = {"feature_vector": [1.0, 2.0]}
        result = calc.calculate(state, None)
        assert 0.0 <= result <= 1.0

    def test_empty_state(self) -> None:
        calc = GainDriveCalculator({})
        result = calc.calculate({}, None)
        assert 0.0 <= result <= 1.0

    def test_boundary_empty_feature(self) -> None:
        calc = GainDriveCalculator({})
        state = {"feature_vector": []}
        result = calc.calculate(state, None)
        assert result == 0.2

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            GainDriveCalculator(None)

    def test_error_trend(self) -> None:
        calc = GainDriveCalculator({})
        calc._calc_error_trend(0.1)
        calc._calc_error_trend(0.2)
        result = calc._calc_error_trend(0.3)
        assert 0.0 <= result <= 1.0


class TestEffDriveCalculator:
    """测试EffDriveCalculator"""

    def test_normal_low_usage(self) -> None:
        calc = EffDriveCalculator({"agent_cpu_limit": 20.0})
        state = {"system_metrics": {"cpu_percent": 10.0}}
        result = calc.calculate(state, 5.0, 5.0)
        assert result > 0.5

    def test_empty_state(self) -> None:
        calc = EffDriveCalculator({})
        result = calc.calculate({}, 0.0, 0.0)
        assert result == 1.0

    def test_boundary_max_usage(self) -> None:
        calc = EffDriveCalculator({"agent_cpu_limit": 20.0})
        state = {}
        result = calc.calculate(state, 20.0, 20.0)
        assert result <= 0.5

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            EffDriveCalculator(None)

    def test_high_usage(self) -> None:
        calc = EffDriveCalculator({"agent_cpu_limit": 20.0})
        state = {"system_metrics": {"cpu_percent": 50.0}}
        result = calc.calculate(state, 30.0, 30.0)
        assert result < 0.5


class TestDynamicWeightAdjuster:
    """测试DynamicWeightAdjuster"""

    def test_normal_adjust(self) -> None:
        adj = DynamicWeightAdjuster({})
        state = {"system_metrics": {"cpu_percent": 50.0}}
        rewards = {DriveType.SAFE: 0.5, DriveType.GAIN: 0.5, DriveType.EFF: 0.5}
        weights = adj.adjust(state, rewards)
        assert abs(sum(weights.values()) - 1.0) < 0.01

    def test_empty_rewards(self) -> None:
        adj = DynamicWeightAdjuster({})
        weights = adj.adjust({}, {})
        assert abs(sum(weights.values()) - 1.0) < 0.01

    def test_boundary_emergency(self) -> None:
        adj = DynamicWeightAdjuster({})
        state = {}
        rewards = {DriveType.SAFE: 0.1, DriveType.GAIN: 0.5, DriveType.EFF: 0.5}
        weights = adj.adjust(state, rewards)
        assert weights[DriveType.SAFE] > weights[DriveType.GAIN]

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            DynamicWeightAdjuster(None)


class TestDriveEngine:
    """测试DriveEngine"""

    def test_normal_compute(self) -> None:
        engine = DriveEngine({})
        state = {"system_metrics": {"cpu_percent": 50.0}}
        result = engine.compute(state, 0.1, {})
        assert "gaps" in result

    def test_empty_state(self) -> None:
        engine = DriveEngine({})
        result = engine.compute({}, None, {})
        assert "rewards" in result

    def test_boundary_interrupt(self) -> None:
        engine = DriveEngine({})
        drive_state = {"gaps": {DriveType.SAFE: 0.8}}
        assert engine.should_interrupt(drive_state) is True

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            DriveEngine(None)

    def test_no_interrupt(self) -> None:
        engine = DriveEngine({})
        drive_state = {"gaps": {DriveType.SAFE: 0.4}}
        assert engine.should_interrupt(drive_state) is False

    def test_total_reward_range(self) -> None:
        engine = DriveEngine({})
        state = {"system_metrics": {"cpu_percent": 50.0}}
        result = engine.compute(state, 0.1, {})
        assert 0.0 <= result["total_reward"] <= 1.0
