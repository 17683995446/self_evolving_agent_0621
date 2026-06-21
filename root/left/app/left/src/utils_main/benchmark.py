"""性能基准与资源占用报告

提供 Agent 运行性能测量、资源占用监控与基准报告生成能力。

设计原则（第一性原理）：
1. 可测量：量化 Agent 的循环耗时、内存占用、CPU 使用率
2. 可比较：基准结果可保存与对比，支持配置调优决策
3. 可理解：结果以表格与摘要形式呈现，附带解读
4. 非侵入式：测量逻辑不改变 Agent 正常行为
"""
from __future__ import annotations

import gc
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from root.left.app.left.src.utils_main.cli_formatter import (
    Color,
    colorize,
    format_duration,
    render_divider,
    render_key_value,
    render_section,
    render_table,
)


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class MemorySnapshot:
    """内存快照。"""

    rss_mb: float  # 常驻内存 (MB)
    vms_mb: float  # 虚拟内存 (MB)
    percent: float  # 占系统内存百分比

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rss_mb": round(self.rss_mb, 2),
            "vms_mb": round(self.vms_mb, 2),
            "percent": round(self.percent, 2),
        }


@dataclass
class BenchmarkResult:
    """单项基准测试结果。"""

    name: str
    iterations: int
    total_seconds: float
    avg_seconds: float
    min_seconds: float
    max_seconds: float
    memory_before: Optional[MemorySnapshot] = None
    memory_after: Optional[MemorySnapshot] = None

    @property
    def ops_per_second(self) -> float:
        """每秒操作数。"""
        if self.total_seconds <= 0:
            return 0.0
        return self.iterations / self.total_seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "iterations": self.iterations,
            "total_seconds": round(self.total_seconds, 4),
            "avg_seconds": round(self.avg_seconds, 4),
            "min_seconds": round(self.min_seconds, 4),
            "max_seconds": round(self.max_seconds, 4),
            "ops_per_second": round(self.ops_per_second, 2),
            "memory_before": self.memory_before.to_dict() if self.memory_before else None,
            "memory_after": self.memory_after.to_dict() if self.memory_after else None,
        }


@dataclass
class BenchmarkReport:
    """基准测试报告。"""

    generated_at: str
    env: str
    results: List[BenchmarkResult] = field(default_factory=list)
    system_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "env": self.env,
            "system_info": self.system_info,
            "results": [r.to_dict() for r in self.results],
        }

    def to_text(self) -> str:
        """渲染报告为文本。"""
        lines: List[str] = []
        lines.append(render_divider())
        lines.append(render_section("Agent 性能基准报告"))
        lines.append(render_divider())
        lines.append("")

        # 系统信息
        if self.system_info:
            lines.append(render_section("系统信息"))
            sys_items = [(k, v) for k, v in self.system_info.items()]
            lines.append(render_key_value(sys_items))
            lines.append("")

        # 基准结果
        if self.results:
            lines.append(render_section("基准结果"))
            lines.append("")
            for r in self.results:
                lines.append(f"  {colorize(r.name, Color.CYAN)}")
                lines.append(render_key_value([
                    ("迭代次数", r.iterations),
                    ("总耗时", format_duration(r.total_seconds)),
                    ("平均耗时", f"{r.avg_seconds * 1000:.2f} ms"),
                    ("最小耗时", f"{r.min_seconds * 1000:.2f} ms"),
                    ("最大耗时", f"{r.max_seconds * 1000:.2f} ms"),
                    ("吞吐量", f"{r.ops_per_second:.2f} ops/s"),
                ]))
                if r.memory_before and r.memory_after:
                    mem_delta = r.memory_after.rss_mb - r.memory_before.rss_mb
                    mem_delta_display = f"{mem_delta:+.2f} MB"
                    lines.append(render_key_value([
                        ("内存（前）", f"{r.memory_before.rss_mb:.2f} MB"),
                        ("内存（后）", f"{r.memory_after.rss_mb:.2f} MB"),
                        ("内存增量", mem_delta_display),
                    ]))
                lines.append("")
        else:
            lines.append("无基准结果。")
            lines.append("")

        lines.append(render_divider())
        return "\n".join(lines)

    def to_json(self) -> str:
        """渲染报告为 JSON。"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 资源测量
# ---------------------------------------------------------------------------

def get_memory_snapshot() -> Optional[MemorySnapshot]:
    """获取当前进程内存快照。

    Returns:
        MemorySnapshot 或 None（psutil 不可用时）
    """
    try:
        import psutil
        process = psutil.Process(os.getpid())
        mem = process.memory_info()
        return MemorySnapshot(
            rss_mb=mem.rss / 1024 / 1024,
            vms_mb=mem.vms / 1024 / 1024,
            percent=process.memory_percent(),
        )
    except ImportError:
        return None
    except Exception:
        return None


def get_system_info() -> Dict[str, Any]:
    """获取系统信息。

    Returns:
        系统信息字典
    """
    import platform
    info: Dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count() or "unknown",
    }
    try:
        import psutil
        info["cpu_percent"] = f"{psutil.cpu_percent(interval=0.1):.1f}%"
        mem = psutil.virtual_memory()
        info["memory_total"] = f"{mem.total / 1024 / 1024:.0f} MB"
        info["memory_available"] = f"{mem.available / 1024 / 1024:.0f} MB"
    except ImportError:
        info["psutil"] = "不可用"
    return info


# ---------------------------------------------------------------------------
# 基准测量
# ---------------------------------------------------------------------------

def measure_operation(
    name: str,
    func: Any,
    iterations: int = 10,
    warmup: int = 1,
) -> BenchmarkResult:
    """测量函数执行性能。

    Args:
        name: 测量名称
        func: 待测量的可调用对象
        iterations: 迭代次数
        warmup: 预热次数（不计入统计）

    Returns:
        BenchmarkResult
    """
    # 预热
    for _ in range(warmup):
        func()

    # 强制 GC 以减少干扰
    gc.collect()

    mem_before = get_memory_snapshot()

    times: List[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    mem_after = get_memory_snapshot()

    total = sum(times)
    return BenchmarkResult(
        name=name,
        iterations=iterations,
        total_seconds=total,
        avg_seconds=total / iterations if iterations > 0 else 0.0,
        min_seconds=min(times) if times else 0.0,
        max_seconds=max(times) if times else 0.0,
        memory_before=mem_before,
        memory_after=mem_after,
    )


def measure_loop_time(agent: Any, iterations: int = 10) -> BenchmarkResult:
    """测量 Agent 单次循环耗时。

    Args:
        agent: Agent 实例（需有 step 方法）
        iterations: 迭代次数

    Returns:
        BenchmarkResult
    """
    def _do_step():
        if hasattr(agent, "step"):
            agent.step()
        elif hasattr(agent, "_run_single_loop"):
            agent._run_single_loop()
        else:
            # 回退：空操作
            pass

    return measure_operation("agent_loop", _do_step, iterations=iterations)


def run_benchmark(
    agent: Optional[Any] = None,
    iterations: int = 10,
    env: str = "dev",
) -> BenchmarkReport:
    """运行完整基准测试。

    Args:
        agent: Agent 实例（可选）
        iterations: 每项测试的迭代次数
        env: 环境名

    Returns:
        BenchmarkReport
    """
    from datetime import datetime

    results: List[BenchmarkResult] = []

    # 1. 配置加载基准
    def _load_config():
        from root.left.app.left.src.utils_main.config_loader import ConfigLoader
        try:
            ConfigLoader.load_config(env)
        except Exception:
            pass

    results.append(measure_operation("config_load", _load_config, iterations=iterations))

    # 2. Agent 循环基准（如果提供了 agent）
    if agent is not None:
        results.append(measure_loop_time(agent, iterations=iterations))

    # 3. 内存分配基准（标准化参考）
    def _alloc_test():
        data = [list(range(1000)) for _ in range(100)]
        return len(data)

    results.append(measure_operation("memory_alloc", _alloc_test, iterations=iterations))

    return BenchmarkReport(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        env=env,
        results=results,
        system_info=get_system_info(),
    )


# ---------------------------------------------------------------------------
# 报告保存
# ---------------------------------------------------------------------------

def save_benchmark_report(
    report: BenchmarkReport,
    output_path: str,
    fmt: str = "text",
) -> str:
    """保存基准报告到文件。

    Args:
        report: 基准报告
        output_path: 输出路径
        fmt: 格式 (text/json)

    Returns:
        保存的文件路径
    """
    content = report.to_json() if fmt == "json" else report.to_text()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path


# ---------------------------------------------------------------------------
# 资源监控（持续）
# ---------------------------------------------------------------------------

@dataclass
class ResourceSample:
    """单次资源采样。"""

    timestamp: float
    memory: Optional[MemorySnapshot]
    cpu_percent: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": round(self.timestamp, 3),
            "memory": self.memory.to_dict() if self.memory else None,
            "cpu_percent": self.cpu_percent,
        }


def sample_resources() -> ResourceSample:
    """采样当前资源占用。"""
    mem = get_memory_snapshot()
    cpu: Optional[float] = None
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=None)
    except ImportError:
        pass
    except Exception:
        pass
    return ResourceSample(
        timestamp=time.time(),
        memory=mem,
        cpu_percent=cpu,
    )


def render_resource_samples(samples: List[ResourceSample]) -> str:
    """渲染资源采样列表为文本。"""
    if not samples:
        return "无采样数据。"

    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section(f"资源监控（{len(samples)} 个采样）"))
    lines.append(render_divider())
    lines.append("")

    rows: List[List[str]] = []
    for s in samples:
        ts = time.strftime("%H:%M:%S", time.localtime(s.timestamp))
        mem = f"{s.memory.rss_mb:.2f} MB" if s.memory else "N/A"
        cpu = f"{s.cpu_percent:.1f}%" if s.cpu_percent is not None else "N/A"
        rows.append([ts, mem, cpu])

    lines.append(render_table(["时间", "内存 (RSS)", "CPU"], rows))

    # 统计
    if len(samples) > 1:
        mem_values = [s.memory.rss_mb for s in samples if s.memory]
        cpu_values = [s.cpu_percent for s in samples if s.cpu_percent is not None]
        lines.append("")
        lines.append(render_section("统计"))
        stats_items: List[Any] = []
        if mem_values:
            stats_items.extend([
                ("内存最小", f"{min(mem_values):.2f} MB"),
                ("内存最大", f"{max(mem_values):.2f} MB"),
                ("内存平均", f"{sum(mem_values) / len(mem_values):.2f} MB"),
            ])
        if cpu_values:
            stats_items.extend([
                ("CPU 最小", f"{min(cpu_values):.1f}%"),
                ("CPU 最大", f"{max(cpu_values):.1f}%"),
                ("CPU 平均", f"{sum(cpu_values) / len(cpu_values):.1f}%"),
            ])
        if stats_items:
            lines.append(render_key_value(stats_items))

    lines.append("")
    lines.append(render_divider())
    return "\n".join(lines)
