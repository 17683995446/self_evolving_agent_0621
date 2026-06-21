"""运维模块单元测试"""
import os
import tempfile
import time

import pytest

from root.left.app.left.src.core_mod.ops import (
    HealthChecker, MetricsCollector, DependencyChecker,
    GracefulShutdown, HotReloader, OpsModule,
)
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestHealthChecker:
    """测试HealthChecker"""

    def test_normal_healthy(self) -> None:
        hc = HealthChecker({})
        hc.register("db", lambda: True)
        result = hc.check()
        assert result["status"] == "healthy"

    def test_unhealthy(self) -> None:
        hc = HealthChecker({})
        hc.register("db", lambda: False)
        result = hc.check()
        assert result["status"] == "unhealthy"

    def test_exception_in_check(self) -> None:
        hc = HealthChecker({})
        hc.register("db", lambda: 1 / 0)
        result = hc.check()
        assert result["status"] == "unhealthy"

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            HealthChecker(None)


class TestMetricsCollector:
    """测试MetricsCollector"""

    def test_counter(self) -> None:
        mc = MetricsCollector({})
        mc.inc_counter("loops", 1)
        mc.inc_counter("loops", 2)
        snap = mc.get_snapshot()
        assert snap["counters"]["loops"] == 3

    def test_gauge(self) -> None:
        mc = MetricsCollector({})
        mc.set_gauge("cpu", 0.5)
        snap = mc.get_snapshot()
        assert snap["gauges"]["cpu"] == 0.5

    def test_histogram(self) -> None:
        mc = MetricsCollector({})
        mc.record_histogram("lat", 0.1)
        mc.record_histogram("lat", 0.2)
        snap = mc.get_snapshot()
        assert snap["histograms"]["lat"]["count"] == 2

    def test_prometheus_render(self) -> None:
        mc = MetricsCollector({})
        mc.inc_counter("loops")
        mc.set_gauge("cpu", 0.5)
        text = mc.render_prometheus()
        assert "loops" in text
        assert "cpu" in text


class TestDependencyChecker:
    """测试DependencyChecker"""

    def test_all_ok(self) -> None:
        dc = DependencyChecker({})
        dc.register("db", lambda: True)
        result = dc.check_all()
        assert result["ready"] is True

    def test_one_failed(self) -> None:
        dc = DependencyChecker({})
        dc.register("db", lambda: True)
        dc.register("cache", lambda: False)
        result = dc.check_all()
        assert result["ready"] is False


class TestGracefulShutdown:
    """测试GracefulShutdown"""

    def test_shutdown_runs_hooks(self) -> None:
        gs = GracefulShutdown({})
        called = []
        gs.register_hook(lambda: called.append(1))
        gs.shutdown()
        assert len(called) == 1

    def test_is_shutting_down(self) -> None:
        gs = GracefulShutdown({})
        assert gs.is_shutting_down() is False
        gs.shutdown()
        assert gs.is_shutting_down() is True

    def test_idempotent_shutdown(self) -> None:
        gs = GracefulShutdown({})
        called = []
        gs.register_hook(lambda: called.append(1))
        gs.shutdown()
        gs.shutdown()
        assert len(called) == 1


class TestHotReloader:
    """测试HotReloader"""

    def test_no_file(self) -> None:
        hr = HotReloader({"watch_path": "/nonexistent"})
        assert hr.check_and_reload() is False

    def test_file_changed(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"v1")
            path = f.name
        try:
            hr = HotReloader({"watch_path": path})
            assert hr.check_and_reload() is True
            assert hr.check_and_reload() is False
            time.sleep(0.01)
            os.utime(path, None)
            assert hr.check_and_reload() is True
        finally:
            os.remove(path)

    def test_reload_hook(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"v1")
            path = f.name
        try:
            hr = HotReloader({"watch_path": path})
            called = []
            hr.register_hook(lambda: called.append(1))
            hr.check_and_reload()
            assert len(called) == 1
        finally:
            os.remove(path)


class TestOpsModule:
    """测试OpsModule"""

    def test_normal_init(self) -> None:
        mod = OpsModule({})
        assert mod.health is not None

    def test_record_loop_metrics(self) -> None:
        mod = OpsModule({})
        mod.record_loop_metrics(1, 0.5, 0.01)
        snap = mod.metrics.get_snapshot()
        assert snap["counters"]["agent_loops_total"] == 1
        assert snap["gauges"]["agent_performance"] == 0.5

    def test_check_dependencies(self) -> None:
        mod = OpsModule({})
        mod.deps.register("db", lambda: True)
        result = mod.check_dependencies()
        assert result["ready"] is True

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            OpsModule(None)
