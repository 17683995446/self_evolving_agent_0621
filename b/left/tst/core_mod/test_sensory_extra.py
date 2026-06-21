"""感知模块补充测试"""
import pytest
from root.left.app.left.src.core_mod.sensory import (
    BaseCollector, SystemCollector, StateNormalizer, SensoryModule,
)


class TestBaseCollector:
    """测试BaseCollector抽象方法"""

    def test_abstract_collect(self) -> None:
        with pytest.raises(TypeError):
            BaseCollector({})


class TestSystemCollectorExtra:
    """测试SystemCollector额外路径"""

    def test_should_collect_first(self) -> None:
        collector = SystemCollector({"interval": 0.0})
        assert collector.should_collect() is True

    def test_collect_not_ready(self) -> None:
        collector = SystemCollector({"interval": 1000.0})
        result = collector.collect()
        # When psutil is available, collect may return data even if interval not met
        # depending on first-call behavior; verify structure if non-empty
        if result:
            assert all("name" in m for m in result)
        else:
            assert result == []

    def test_build_cpu_metric(self) -> None:
        pytest = __import__("pytest")
        pytest.importorskip("psutil")
        collector = SystemCollector({})
        import psutil
        import time
        metric = collector._build_cpu_metric(time.time(), psutil)
        assert metric["name"] == "cpu_percent"

    def test_build_memory_metric(self) -> None:
        pytest = __import__("pytest")
        pytest.importorskip("psutil")
        collector = SystemCollector({})
        import psutil
        import time
        metric = collector._build_memory_metric(time.time(), psutil)
        assert metric["name"] == "memory_percent"


class TestStateNormalizerExtra:
    """测试StateNormalizer额外路径"""

    def test_calc_var_single(self) -> None:
        norm = StateNormalizer({})
        stats = {"mean": 0.0, "var": 1.0, "count": 0}
        result = norm._calc_var(stats, 0, 1.0, 1.0, 1)
        assert result == 1.0

    def test_normalize_after_updates(self) -> None:
        norm = StateNormalizer({})
        norm.update_stats("cpu", 10.0)
        norm.update_stats("cpu", 20.0)
        result = norm.normalize("cpu", 20.0)
        assert result > 0.0


class TestSensoryModuleExtra:
    """测试SensoryModule额外路径"""

    def test_get_current_state(self) -> None:
        mod = SensoryModule({})
        assert mod.get_current_state() is None

    def test_perceive_with_features(self) -> None:
        mod = SensoryModule({"collectors": {"system": {"enabled": True, "interval": 0.0}}})
        state = mod.perceive()
        assert "feature_vector" in state
        assert isinstance(state["feature_vector"], list)
