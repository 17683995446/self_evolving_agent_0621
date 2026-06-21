"""生产级运维与监控模块"""
import os
import signal
import threading
from typing import Any, Callable, Dict, Final, List

from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class HealthChecker:
    """健康检查器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[HealthChecker.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.checks: Dict[str, Callable[[], bool]] = {}
        self._healthy: bool = True
        self._lock = threading.Lock()
        logger.info("HealthChecker initialized", "ops")

    def register(self, name: str, check_fn: Callable[[], bool]) -> None:
        logger.debug(f"[HealthChecker.register] name={name}")
        self.checks[name] = check_fn

    def check(self) -> Dict[str, Any]:
        logger.debug("[HealthChecker.check] start")
        results = {}
        all_healthy = True
        for name, fn in self.checks.items():
            try:
                ok = fn()
                results[name] = "healthy" if ok else "unhealthy"
                if not ok:
                    all_healthy = False
            except Exception as e:
                results[name] = f"error: {e}"
                all_healthy = False
        with self._lock:
            self._healthy = all_healthy
        result = {"status": "healthy" if all_healthy else "unhealthy", "checks": results}
        logger.debug(f"[HealthChecker.check] result={result['status']}")
        return result

    def is_healthy(self) -> bool:
        with self._lock:
            return self._healthy


class MetricsCollector:
    """指标收集器（Prometheus格式）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[MetricsCollector.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
        logger.info("MetricsCollector initialized", "ops")

    def inc_counter(self, name: str, value: int = 1) -> None:
        logger.debug(f"[MetricsCollector.inc_counter] name={name} value={value}")
        with self._lock:
            self.counters[name] = self.counters.get(name, 0) + value

    def set_gauge(self, name: str, value: float) -> None:
        logger.debug(f"[MetricsCollector.set_gauge] name={name} value={value}")
        with self._lock:
            self.gauges[name] = value

    def record_histogram(self, name: str, value: float) -> None:
        logger.debug(f"[MetricsCollector.record_histogram] name={name} value={value}")
        with self._lock:
            if name not in self.histograms:
                self.histograms[name] = []
            self.histograms[name].append(value)

    def render_prometheus(self) -> str:
        logger.debug("[MetricsCollector.render_prometheus] start")
        lines: List[str] = []
        with self._lock:
            for name, value in self.counters.items():
                lines.append(f"# TYPE {name} counter")
                lines.append(f'{name} {value}')
            for name, value in self.gauges.items():
                lines.append(f"# TYPE {name} gauge")
                lines.append(f'{name} {value}')
            for name, values in self.histograms.items():
                if values:
                    lines.append(f"# TYPE {name} histogram")
                    lines.append(f'{name}_count {len(values)}')
                    lines.append(f'{name}_sum {sum(values)}')
        result = "\n".join(lines)
        logger.debug("[MetricsCollector.render_prometheus] done")
        return result

    def get_snapshot(self) -> Dict[str, Any]:
        logger.debug("[MetricsCollector.get_snapshot] start")
        with self._lock:
            return {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {k: {"count": len(v), "sum": sum(v)} for k, v in self.histograms.items()},
            }


class DependencyChecker:
    """依赖检查器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[DependencyChecker.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.dependencies: Dict[str, Callable[[], bool]] = {}
        logger.info("DependencyChecker initialized", "ops")

    def register(self, name: str, check_fn: Callable[[], bool]) -> None:
        logger.debug(f"[DependencyChecker.register] name={name}")
        self.dependencies[name] = check_fn

    def check_all(self) -> Dict[str, Any]:
        logger.debug("[DependencyChecker.check_all] start")
        results = {}
        all_ok = True
        for name, fn in self.dependencies.items():
            try:
                ok = fn()
                results[name] = "ok" if ok else "failed"
                if not ok:
                    all_ok = False
            except Exception as e:
                results[name] = f"error: {e}"
                all_ok = False
        result = {"ready": all_ok, "dependencies": results}
        logger.info(f"[DependencyChecker.check_all] ready={all_ok}", "ops")
        return result


class GracefulShutdown:
    """优雅关闭控制器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[GracefulShutdown.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.timeout: float = float(config.get("timeout", 10.0))
        self._shutdown_hooks: List[Callable[[], None]] = []
        self._shutting_down: bool = False
        self._lock = threading.Lock()
        logger.info(f"GracefulShutdown initialized timeout={self.timeout}", "ops")

    def register_hook(self, hook: Callable[[], None]) -> None:
        logger.debug("[GracefulShutdown.register_hook] start")
        self._shutdown_hooks.append(hook)

    def start(self) -> None:
        logger.debug("[GracefulShutdown.start] registering signals")
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum: int, frame: Any) -> None:
        logger.info(f"[GracefulShutdown._handle_signal] received signal={signum}", "ops")
        self.shutdown()

    def shutdown(self) -> None:
        logger.info("[GracefulShutdown.shutdown] initiating graceful shutdown", "ops")
        with self._lock:
            if self._shutting_down:
                return
            self._shutting_down = True
        for hook in self._shutdown_hooks:
            try:
                hook()
            except Exception as e:
                logger.error(f"[GracefulShutdown.shutdown] hook error: {e}", "ops")
        logger.info("[GracefulShutdown.shutdown] completed", "ops")

    def is_shutting_down(self) -> bool:
        with self._lock:
            return self._shutting_down


class HotReloader:
    """热更新控制器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[HotReloader.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.watch_path: str = str(config.get("watch_path", ""))
        self._last_mtime: float = 0.0
        self._reload_hooks: List[Callable[[], None]] = []
        logger.info(f"HotReloader initialized watch_path={self.watch_path}", "ops")

    def register_hook(self, hook: Callable[[], None]) -> None:
        logger.debug("[HotReloader.register_hook] start")
        self._reload_hooks.append(hook)

    def check_and_reload(self) -> bool:
        logger.debug("[HotReloader.check_and_reload] start")
        if not self.watch_path or not os.path.exists(self.watch_path):
            return False
        mtime = os.path.getmtime(self.watch_path)
        if mtime > self._last_mtime:
            logger.info("[HotReloader.check_and_reload] change detected", "ops")
            self._last_mtime = mtime
            for hook in self._reload_hooks:
                try:
                    hook()
                except Exception as e:
                    logger.error(f"[HotReloader.check_and_reload] hook error: {e}", "ops")
            return True
        return False


class OpsModule:
    """运维模块主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[OpsModule.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.health = HealthChecker(config.get("health", {}))
        logger.debug("[OpsModule.__init__] health created")
        self.metrics = MetricsCollector(config.get("metrics", {}))
        logger.debug("[OpsModule.__init__] metrics created")
        self.deps = DependencyChecker(config.get("deps", {}))
        logger.debug("[OpsModule.__init__] deps created")
        self.shutdown = GracefulShutdown(config.get("shutdown", {}))
        logger.debug("[OpsModule.__init__] shutdown created")
        self.reloader = HotReloader(config.get("reloader", {}))
        logger.debug("[OpsModule.__init__] reloader created")
        logger.info("OpsModule initialized", "ops")

    def record_loop_metrics(self, loop_count: int, performance: float, latency: float) -> None:
        logger.debug(f"[OpsModule.record_loop_metrics] loop={loop_count}")
        self.metrics.inc_counter("agent_loops_total")
        self.metrics.set_gauge("agent_loop_count", float(loop_count))
        self.metrics.set_gauge("agent_performance", performance)
        self.metrics.record_histogram("agent_loop_latency_seconds", latency)

    def get_health(self) -> Dict[str, Any]:
        return self.health.check()

    def get_metrics(self) -> str:
        return self.metrics.render_prometheus()

    def check_dependencies(self) -> Dict[str, Any]:
        return self.deps.check_all()

    def start_shutdown_handler(self) -> None:
        self.shutdown.start()

    def check_hot_reload(self) -> bool:
        return self.reloader.check_and_reload()
