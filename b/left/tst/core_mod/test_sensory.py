"""感知模块单元测试"""
import pytest
from root.left.app.left.src.core_mod.sensory import (
    SystemCollector, StateNormalizer, NoiseFilter, SensoryModule,
)
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestSystemCollector:
    """测试SystemCollector"""

    def test_normal_init(self) -> None:
        collector = SystemCollector({"enabled": True, "interval": 1.0})
        assert collector.enabled is True

    def test_empty_config(self) -> None:
        collector = SystemCollector({})
        assert collector.enabled is True

    def test_boundary_zero_interval(self) -> None:
        collector = SystemCollector({"interval": 0.0})
        assert collector.sample_interval == 0.0

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            SystemCollector(None)

    def test_collect_returns_list(self) -> None:
        collector = SystemCollector({"enabled": True, "interval": 0.0})
        result = collector.collect()
        assert isinstance(result, list)

    def test_validate_normal(self) -> None:
        collector = SystemCollector({})
        metrics = [{"name": "cpu_percent", "value": 50.0}]
        assert collector.validate(metrics) is True

    def test_validate_out_of_range(self) -> None:
        collector = SystemCollector({})
        metrics = [{"name": "cpu_percent", "value": 150.0}]
        assert collector.validate(metrics) is False


class TestStateNormalizer:
    """测试StateNormalizer"""

    def test_normal_init(self) -> None:
        norm = StateNormalizer({"feature_order": ["cpu"]})
        assert norm.feature_order == ["cpu"]

    def test_empty_config(self) -> None:
        norm = StateNormalizer({})
        assert "cpu_percent" in norm.feature_order

    def test_boundary_normalize_low_count(self) -> None:
        norm = StateNormalizer({})
        result = norm.normalize("cpu", 50.0)
        assert result == 0.0

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            StateNormalizer(None)

    def test_update_stats(self) -> None:
        norm = StateNormalizer({})
        norm.update_stats("cpu", 10.0)
        norm.update_stats("cpu", 20.0)
        assert norm.running_stats["cpu"]["count"] == 2

    def test_clip_outliers(self) -> None:
        norm = StateNormalizer({})
        assert norm.clip_outliers(5.0) == 3.0


class TestNoiseFilter:
    """测试NoiseFilter"""

    def test_normal_init(self) -> None:
        filt = NoiseFilter({"ema_alpha": 0.5})
        assert filt.ema_alpha == 0.5

    def test_empty_config(self) -> None:
        filt = NoiseFilter({})
        assert filt.ema_alpha == 0.3

    def test_boundary_alpha_min(self) -> None:
        with pytest.raises(ValidationError):
            NoiseFilter({"ema_alpha": 0.001})

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            NoiseFilter(None)

    def test_apply_ema_first(self) -> None:
        filt = NoiseFilter({})
        result = filt.apply_ema("cpu", 10.0)
        assert result == 10.0

    def test_apply_ema_second(self) -> None:
        filt = NoiseFilter({})
        filt.apply_ema("cpu", 10.0)
        result = filt.apply_ema("cpu", 20.0)
        assert 10.0 < result < 20.0


class TestSensoryModule:
    """测试SensoryModule"""

    def test_normal_init(self) -> None:
        mod = SensoryModule({})
        assert mod.current_state is None

    def test_empty_config(self) -> None:
        mod = SensoryModule({})
        assert mod.collectors is not None

    def test_boundary_perceive(self) -> None:
        mod = SensoryModule({"collectors": {"system": {"enabled": True, "interval": 0.0}}})
        state = mod.perceive()
        assert "timestamp" in state

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            SensoryModule(None)
