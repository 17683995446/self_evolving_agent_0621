"""性能基准与资源占用报告测试"""
from __future__ import annotations

import json
import os
import tempfile
import time

from root.left.app.left.src.cli import main
from root.left.app.left.src.utils_main.benchmark import (
    BenchmarkReport,
    BenchmarkResult,
    MemorySnapshot,
    ResourceSample,
    get_memory_snapshot,
    get_system_info,
    measure_operation,
    render_resource_samples,
    run_benchmark,
    sample_resources,
    save_benchmark_report,
)


# ---------------------------------------------------------------------------
# MemorySnapshot 测试
# ---------------------------------------------------------------------------

class TestMemorySnapshot:
    """测试内存快照"""

    def test_to_dict(self):
        snap = MemorySnapshot(rss_mb=100.5, vms_mb=200.0, percent=5.0)
        d = snap.to_dict()
        assert d["rss_mb"] == 100.5
        assert d["vms_mb"] == 200.0
        assert d["percent"] == 5.0

    def test_to_dict_rounds_values(self):
        snap = MemorySnapshot(rss_mb=100.56789, vms_mb=200.12345, percent=5.98765)
        d = snap.to_dict()
        assert d["rss_mb"] == 100.57
        assert d["vms_mb"] == 200.12
        assert d["percent"] == 5.99


# ---------------------------------------------------------------------------
# BenchmarkResult 测试
# ---------------------------------------------------------------------------

class TestBenchmarkResult:
    """测试基准测试结果"""

    def test_to_dict(self):
        result = BenchmarkResult(
            name="test",
            iterations=10,
            total_seconds=1.0,
            avg_seconds=0.1,
            min_seconds=0.05,
            max_seconds=0.2,
        )
        d = result.to_dict()
        assert d["name"] == "test"
        assert d["iterations"] == 10
        assert d["total_seconds"] == 1.0
        assert d["avg_seconds"] == 0.1
        assert d["ops_per_second"] == 10.0

    def test_ops_per_second(self):
        result = BenchmarkResult(
            name="test", iterations=100, total_seconds=2.0,
            avg_seconds=0.02, min_seconds=0.01, max_seconds=0.03,
        )
        assert result.ops_per_second == 50.0

    def test_ops_per_second_zero_time(self):
        result = BenchmarkResult(
            name="test", iterations=10, total_seconds=0.0,
            avg_seconds=0.0, min_seconds=0.0, max_seconds=0.0,
        )
        assert result.ops_per_second == 0.0

    def test_to_dict_with_memory(self):
        mem = MemorySnapshot(rss_mb=50.0, vms_mb=100.0, percent=2.0)
        result = BenchmarkResult(
            name="test", iterations=5, total_seconds=0.5,
            avg_seconds=0.1, min_seconds=0.08, max_seconds=0.12,
            memory_before=mem, memory_after=mem,
        )
        d = result.to_dict()
        assert d["memory_before"] is not None
        assert d["memory_after"] is not None
        assert d["memory_before"]["rss_mb"] == 50.0


# ---------------------------------------------------------------------------
# BenchmarkReport 测试
# ---------------------------------------------------------------------------

class TestBenchmarkReport:
    """测试基准报告"""

    def test_to_dict(self):
        report = BenchmarkReport(generated_at="2026-01-01", env="dev")
        d = report.to_dict()
        assert d["generated_at"] == "2026-01-01"
        assert d["env"] == "dev"
        assert d["results"] == []

    def test_to_text_empty(self):
        report = BenchmarkReport(generated_at="2026-01-01", env="dev")
        text = report.to_text()
        assert "性能基准报告" in text
        assert "无基准结果" in text

    def test_to_text_with_results(self):
        result = BenchmarkResult(
            name="test_op", iterations=10, total_seconds=1.0,
            avg_seconds=0.1, min_seconds=0.05, max_seconds=0.2,
        )
        report = BenchmarkReport(
            generated_at="2026-01-01", env="dev",
            results=[result],
            system_info={"python": "3.14"},
        )
        text = report.to_text()
        assert "性能基准报告" in text
        assert "test_op" in text
        assert "系统信息" in text
        assert "python" in text

    def test_to_json(self):
        report = BenchmarkReport(generated_at="2026-01-01", env="dev")
        json_str = report.to_json()
        data = json.loads(json_str)
        assert data["generated_at"] == "2026-01-01"
        assert data["env"] == "dev"


# ---------------------------------------------------------------------------
# 资源测量函数测试
# ---------------------------------------------------------------------------

class TestGetMemorySnapshot:
    """测试内存快照获取"""

    def test_returns_snapshot_or_none(self):
        snap = get_memory_snapshot()
        # psutil 已安装时应返回快照
        if snap is not None:
            assert snap.rss_mb > 0
            assert snap.vms_mb > 0
            assert snap.percent >= 0


class TestGetSystemInfo:
    """测试系统信息获取"""

    def test_returns_dict(self):
        info = get_system_info()
        assert isinstance(info, dict)
        assert "python" in info
        assert "platform" in info
        assert "cpu_count" in info

    def test_contains_python_version(self):
        info = get_system_info()
        assert "3." in info["python"]


# ---------------------------------------------------------------------------
# measure_operation 测试
# ---------------------------------------------------------------------------

class TestMeasureOperation:
    """测试操作测量"""

    def test_basic_measurement(self):
        def dummy():
            pass
        result = measure_operation("dummy", dummy, iterations=5)
        assert result.name == "dummy"
        assert result.iterations == 5
        assert result.total_seconds >= 0
        assert result.avg_seconds >= 0
        assert result.min_seconds <= result.max_seconds

    def test_with_work(self):
        def work():
            return sum(range(1000))
        result = measure_operation("work", work, iterations=10)
        assert result.iterations == 10
        assert result.total_seconds > 0
        assert result.ops_per_second > 0

    def test_memory_snapshots_captured(self):
        def work():
            data = [list(range(100)) for _ in range(10)]
            return len(data)
        result = measure_operation("work", work, iterations=3)
        # psutil 可用时应有内存快照
        if result.memory_before is not None:
            assert result.memory_after is not None


# ---------------------------------------------------------------------------
# run_benchmark 测试
# ---------------------------------------------------------------------------

class TestRunBenchmark:
    """测试完整基准测试"""

    def test_returns_report(self):
        report = run_benchmark(iterations=3, env="dev")
        assert isinstance(report, BenchmarkReport)
        assert report.env == "dev"
        assert len(report.results) > 0

    def test_contains_config_load_result(self):
        report = run_benchmark(iterations=3, env="dev")
        names = [r.name for r in report.results]
        assert "config_load" in names

    def test_contains_memory_alloc_result(self):
        report = run_benchmark(iterations=3, env="dev")
        names = [r.name for r in report.results]
        assert "memory_alloc" in names

    def test_system_info_populated(self):
        report = run_benchmark(iterations=3, env="dev")
        assert "python" in report.system_info


# ---------------------------------------------------------------------------
# save_benchmark_report 测试
# ---------------------------------------------------------------------------

class TestSaveBenchmarkReport:
    """测试保存基准报告"""

    def test_save_text(self):
        report = BenchmarkReport(generated_at="2026-01-01", env="dev")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            path = f.name
        try:
            save_benchmark_report(report, path, fmt="text")
            assert os.path.exists(path)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "性能基准报告" in content
        finally:
            os.unlink(path)

    def test_save_json(self):
        report = BenchmarkReport(generated_at="2026-01-01", env="dev")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_benchmark_report(report, path, fmt="json")
            assert os.path.exists(path)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["env"] == "dev"
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# ResourceSample 与采样测试
# ---------------------------------------------------------------------------

class TestResourceSample:
    """测试资源采样"""

    def test_to_dict(self):
        mem = MemorySnapshot(rss_mb=50.0, vms_mb=100.0, percent=2.0)
        sample = ResourceSample(timestamp=1000.0, memory=mem, cpu_percent=10.0)
        d = sample.to_dict()
        assert d["timestamp"] == 1000.0
        assert d["memory"] is not None
        assert d["cpu_percent"] == 10.0

    def test_to_dict_no_memory(self):
        sample = ResourceSample(timestamp=1000.0, memory=None, cpu_percent=None)
        d = sample.to_dict()
        assert d["memory"] is None
        assert d["cpu_percent"] is None


class TestSampleResources:
    """测试资源采样函数"""

    def test_returns_sample(self):
        sample = sample_resources()
        assert isinstance(sample, ResourceSample)
        assert sample.timestamp > 0


class TestRenderResourceSamples:
    """测试资源采样渲染"""

    def test_empty_samples(self):
        result = render_resource_samples([])
        assert "无采样数据" in result

    def test_with_samples(self):
        mem = MemorySnapshot(rss_mb=50.0, vms_mb=100.0, percent=2.0)
        samples = [
            ResourceSample(timestamp=time.time(), memory=mem, cpu_percent=10.0),
            ResourceSample(timestamp=time.time() + 1, memory=mem, cpu_percent=15.0),
        ]
        result = render_resource_samples(samples)
        assert "资源监控" in result
        assert "2" in result  # 2 个采样

    def test_with_statistics(self):
        mem1 = MemorySnapshot(rss_mb=50.0, vms_mb=100.0, percent=2.0)
        mem2 = MemorySnapshot(rss_mb=60.0, vms_mb=110.0, percent=3.0)
        samples = [
            ResourceSample(timestamp=time.time(), memory=mem1, cpu_percent=10.0),
            ResourceSample(timestamp=time.time() + 1, memory=mem2, cpu_percent=20.0),
        ]
        result = render_resource_samples(samples)
        assert "统计" in result
        assert "最小" in result
        assert "最大" in result


# ---------------------------------------------------------------------------
# CLI 集成测试
# ---------------------------------------------------------------------------

class TestCLIBenchmark:
    """测试 benchmark 子命令"""

    def test_benchmark_basic(self, capsys):
        rc = main(["benchmark", "--iterations", "3"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "性能基准报告" in captured.out

    def test_benchmark_json(self, capsys):
        rc = main(["benchmark", "--iterations", "3", "--json"])
        captured = capsys.readouterr()
        assert rc == 0
        data = json.loads(captured.out)
        assert "results" in data
        assert "system_info" in data

    def test_benchmark_with_output(self, capsys, tmp_path):
        output_file = tmp_path / "bench.txt"
        rc = main(["benchmark", "--iterations", "3", "--output", str(output_file)])
        captured = capsys.readouterr()
        assert rc == 0
        assert output_file.exists()
        assert "已保存" in captured.err

    def test_benchmark_monitor(self, capsys):
        # 监控模式，少量采样
        rc = main(["benchmark", "--monitor", "--iterations", "2", "--interval", "0.01"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "资源监控" in captured.out

    def test_benchmark_monitor_json(self, capsys):
        rc = main(["benchmark", "--monitor", "--iterations", "2", "--interval", "0.01", "--json"])
        captured = capsys.readouterr()
        assert rc == 0
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 2


# ---------------------------------------------------------------------------
# 帮助系统集成
# ---------------------------------------------------------------------------

class TestHelpIntegration:
    """测试帮助系统是否包含 benchmark 命令"""

    def test_help_all_contains_benchmark(self, capsys):
        rc = main(["help"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "benchmark" in captured.out

    def test_help_benchmark(self, capsys):
        rc = main(["help", "benchmark"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "benchmark" in captured.out
        assert "性能" in captured.out or "基准" in captured.out
