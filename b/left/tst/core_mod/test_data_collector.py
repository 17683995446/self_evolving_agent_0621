"""数据采集器测试"""
import os
import tempfile

from root.left.app.left.src.core_mod.data_collector import (
    CallbackCollector,
    DataCollectorModule,
    FileCollector,
    HttpCollector,
    LogCollector,
    SystemMetricsCollector,
)


class TestLogCollector:
    """日志采集器测试"""

    def test_collect_empty_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            path = f.name
        try:
            collector = LogCollector("test_log", {"path": path, "max_lines": 10, "patterns": {"error": "ERROR"}})
            result = collector.collect()
            assert result.success is True
            assert result.data["lines"] == []
            assert result.data["counts"]["error"] == 0
        finally:
            os.remove(path)

    def test_collect_with_lines(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("INFO start\nERROR something wrong\nINFO done\n")
            path = f.name
        try:
            collector = LogCollector("test_log", {"path": path, "max_lines": 10, "patterns": {"error": "ERROR"}})
            result = collector.collect()
            assert result.success is True
            assert len(result.data["lines"]) == 3
            assert result.data["counts"]["error"] == 1
        finally:
            os.remove(path)

    def test_collect_tail(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("line1\nline2\n")
            path = f.name
        try:
            collector = LogCollector("test_log", {"path": path, "max_lines": 10})
            collector.collect()
            with open(path, "a") as f:
                f.write("line3\n")
            result = collector.collect()
            assert result.data["lines"] == ["line3"]
        finally:
            os.remove(path)


class TestHttpCollector:
    """HTTP 采集器测试"""

    def test_empty_url(self) -> None:
        collector = HttpCollector("test_http", {"url": ""})
        result = collector.collect()
        assert result.success is True
        assert result.data == {}

    def test_blocked_host(self) -> None:
        collector = HttpCollector("test_http", {"url": "http://example.com/metrics"})
        result = collector.collect()
        assert result.success is False
        assert "not allowed" in result.error


class TestFileCollector:
    """文件采集器测试"""

    def test_collect_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello world")
            path = f.name
        try:
            collector = FileCollector("test_file", {"path": path, "max_bytes": 100})
            result = collector.collect()
            assert result.success is True
            assert result.data["exists"] is True
            assert result.data["content_preview"] == "hello world"
        finally:
            os.remove(path)

    def test_blocked_path(self) -> None:
        collector = FileCollector("test_file", {"path": "/etc/passwd"})
        result = collector.collect()
        assert result.success is False
        assert "blocked" in result.error.lower()


class TestCallbackCollector:
    """回调采集器测试"""

    def test_callback(self) -> None:
        collector = CallbackCollector("test_cb", {"callback": lambda: {"cpu": 10}})
        result = collector.collect()
        assert result.success is True
        assert result.data == {"cpu": 10}

    def test_callback_exception(self) -> None:
        collector = CallbackCollector("test_cb", {"callback": lambda: (_ for _ in ()).throw(RuntimeError("boom"))})
        result = collector.collect()
        assert result.success is False


class TestSystemMetricsCollector:
    """系统指标采集器测试"""

    def test_collect_cpu(self) -> None:
        collector = SystemMetricsCollector("test_system", {"metrics": ["cpu"], "interval": 0.0})
        result = collector.collect()
        assert result.success is True
        assert "cpu_percent" in result.data
        assert isinstance(result.data["cpu_percent"], (int, float))

    def test_collect_memory(self) -> None:
        collector = SystemMetricsCollector("test_system", {"metrics": ["memory"]})
        result = collector.collect()
        assert result.success is True
        assert "memory_percent" in result.data
        assert "memory_available_mb" in result.data

    def test_collect_all_metrics(self) -> None:
        collector = SystemMetricsCollector("test_system", {"metrics": ["cpu", "memory", "disk", "network"], "interval": 0.0})
        result = collector.collect()
        assert result.success is True
        for key in ["cpu_percent", "memory_percent", "disk_percent", "network_bytes_sent"]:
            assert key in result.data

    def test_module_system_source(self) -> None:
        config = {
            "sources": [
                {"name": "sys", "type": "system", "config": {"metrics": ["memory"]}},
            ]
        }
        module = DataCollectorModule(config)
        result = module.collect_all()
        assert "sys" in result
        assert result["sys"]["data"]["memory_percent"] >= 0


class TestDataCollectorModule:
    """数据采集模块主控测试"""

    def test_empty_config(self) -> None:
        module = DataCollectorModule({})
        assert module.collect_all() == {}

    def test_multiple_sources(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("ERROR boom\n")
            log_path = f.name
        try:
            config = {
                "sources": [
                    {"name": "log1", "type": "log", "config": {"path": log_path, "patterns": {"error": "ERROR"}}},
                    {"name": "cb1", "type": "callback", "config": {"callback": lambda: 42}},
                ]
            }
            module = DataCollectorModule(config)
            result = module.collect_all()
            assert "log1" in result
            assert "cb1" in result
            assert result["log1"]["data"]["counts"]["error"] == 1
            assert result["cb1"]["data"] == 42
        finally:
            os.remove(log_path)

    def test_register_callback(self) -> None:
        module = DataCollectorModule({})
        module.register_callback("dynamic", lambda: {"value": 1})
        result = module.collect_all()
        assert result["dynamic"]["data"] == {"value": 1}
