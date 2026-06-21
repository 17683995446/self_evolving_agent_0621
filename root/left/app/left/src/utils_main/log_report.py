"""日志可视化与运行报告生成

提供日志文件解析、过滤、统计与可视化，以及运行报告生成能力。

设计原则（第一性原理）：
1. 可追溯：用户能回溯任意时刻的运行状态
2. 可分析：提供日志级别统计、模块分布、时间分布等分析
3. 可导出：报告可导出为文本/JSON，便于归档与分享
4. 非侵入式：基于现有日志格式解析，不修改日志输出
"""
from __future__ import annotations

import os
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from root.left.app.left.src.utils_main.cli_formatter import (
    Color,
    colorize,
    format_status_label,
    render_divider,
    render_key_value,
    render_section,
    render_table,
)


# ---------------------------------------------------------------------------
# 日志条目解析
# ---------------------------------------------------------------------------

# 日志行格式: [2026-06-20 10:43:11] [INFO    ] [SelfEvolvingAgent] [main] message
LOG_PATTERN = re.compile(
    r"^\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] "
    r"\[(?P<level>[A-Z]+)\s*\] "
    r"\[(?P<logger>[^\]]+)\] "
    r"(?:\[(?P<module>[^\]]+)\] )?"
    r"(?P<message>.*)$"
)


@dataclass
class LogEntry:
    """单条日志记录。"""

    timestamp: str
    level: str
    logger: str
    module: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "logger": self.logger,
            "module": self.module,
            "message": self.message,
        }


def parse_log_line(line: str) -> Optional[LogEntry]:
    """解析单行日志。

    Returns:
        LogEntry 或 None（行不匹配日志格式时）
    """
    line = line.rstrip("\n\r")
    if not line:
        return None
    match = LOG_PATTERN.match(line)
    if match is None:
        return None
    return LogEntry(
        timestamp=match.group("timestamp"),
        level=match.group("level").strip(),
        logger=match.group("logger"),
        module=match.group("module") or "",
        message=match.group("message"),
    )


def parse_log_file(file_path: str) -> List[LogEntry]:
    """解析整个日志文件。

    Args:
        file_path: 日志文件路径

    Returns:
        LogEntry 列表

    Raises:
        FileNotFoundError: 文件不存在
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"日志文件不存在: {file_path}")
    entries: List[LogEntry] = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            entry = parse_log_line(line)
            if entry is not None:
                entries.append(entry)
    return entries


# ---------------------------------------------------------------------------
# 日志统计
# ---------------------------------------------------------------------------

@dataclass
class LogStats:
    """日志统计结果。"""

    total: int = 0
    by_level: Dict[str, int] = field(default_factory=dict)
    by_module: Dict[str, int] = field(default_factory=dict)
    by_logger: Dict[str, int] = field(default_factory=dict)
    time_range_start: str = ""
    time_range_end: str = ""
    error_messages: List[str] = field(default_factory=list)
    warning_messages: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "by_level": self.by_level,
            "by_module": self.by_module,
            "by_logger": self.by_logger,
            "time_range_start": self.time_range_start,
            "time_range_end": self.time_range_end,
            "error_count": len(self.error_messages),
            "warning_count": len(self.warning_messages),
        }


def compute_stats(entries: List[LogEntry]) -> LogStats:
    """计算日志统计。"""
    stats = LogStats()
    stats.total = len(entries)
    if not entries:
        return stats

    stats.by_level = dict(Counter(e.level for e in entries))
    stats.by_module = dict(Counter(e.module for e in entries if e.module))
    stats.by_logger = dict(Counter(e.logger for e in entries))
    stats.time_range_start = entries[0].timestamp
    stats.time_range_end = entries[-1].timestamp

    for e in entries:
        if e.level == "ERROR":
            stats.error_messages.append(e.message)
        elif e.level == "WARNING":
            stats.warning_messages.append(e.message)

    return stats


# ---------------------------------------------------------------------------
# 日志过滤
# ---------------------------------------------------------------------------

def filter_entries(
    entries: List[LogEntry],
    level: Optional[str] = None,
    module: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[LogEntry]:
    """过滤日志条目。

    Args:
        entries: 日志条目列表
        level: 按级别过滤（DEBUG/INFO/WARNING/ERROR/CRITICAL）
        module: 按模块过滤（子串匹配）
        keyword: 按消息关键字过滤（子串匹配）
        limit: 限制返回条数（取最后 N 条）

    Returns:
        过滤后的日志条目列表
    """
    result = entries
    if level:
        level_upper = level.upper()
        result = [e for e in result if e.level == level_upper]
    if module:
        result = [e for e in result if module in e.module]
    if keyword:
        result = [e for e in result if keyword in e.message]
    if limit is not None and limit > 0:
        result = result[-limit:]
    return result


# ---------------------------------------------------------------------------
# 可视化渲染
# ---------------------------------------------------------------------------

def render_stats(stats: LogStats) -> str:
    """渲染日志统计为可读文本。"""
    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section("日志统计"))
    lines.append(render_divider())
    lines.append("")

    # 概要
    lines.append(render_key_value([
        ("总条目数", stats.total),
        ("时间范围", f"{stats.time_range_start} ~ {stats.time_range_end}" if stats.total else "无"),
        ("错误数", stats.error_messages.__len__()),
        ("警告数", stats.warning_messages.__len__()),
    ]))
    lines.append("")

    # 按级别分布
    if stats.by_level:
        lines.append(render_section("按级别分布"))
        level_order = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        rows = []
        for lvl in level_order:
            if lvl in stats.by_level:
                count = stats.by_level[lvl]
                pct = (count / stats.total * 100) if stats.total else 0
                rows.append([lvl, count, f"{pct:.1f}%"])
        # 其他级别
        for lvl, count in stats.by_level.items():
            if lvl not in level_order:
                pct = (count / stats.total * 100) if stats.total else 0
                rows.append([lvl, count, f"{pct:.1f}%"])
        lines.append(render_table(["级别", "数量", "占比"], rows))
        lines.append("")

    # 按模块分布（Top 10）
    if stats.by_module:
        lines.append(render_section("按模块分布 (Top 10)"))
        sorted_modules = sorted(stats.by_module.items(), key=lambda x: -x[1])[:10]
        rows = [[mod, count] for mod, count in sorted_modules]
        lines.append(render_table(["模块", "数量"], rows))
        lines.append("")

    # 错误消息（最近 5 条）
    if stats.error_messages:
        lines.append(render_section("最近错误 (最多 5 条)"))
        for msg in stats.error_messages[-5:]:
            lines.append(f"  {colorize('ERROR', Color.RED)} {msg}")
        lines.append("")

    return "\n".join(lines)


def render_entries(entries: List[LogEntry], show_module: bool = True) -> str:
    """渲染日志条目列表为可读文本。"""
    if not entries:
        return "(无日志条目)"

    lines: List[str] = []
    for e in entries:
        level_display = _colorize_level(e.level)
        module_display = f" [{e.module}]" if show_module and e.module else ""
        lines.append(f"{e.timestamp} {level_display}{module_display} {e.message}")
    return "\n".join(lines)


def _colorize_level(level: str) -> str:
    """为日志级别添加颜色。"""
    level_map = {
        "DEBUG": Color.GRAY,
        "INFO": Color.CYAN,
        "WARNING": Color.YELLOW,
        "ERROR": Color.RED,
        "CRITICAL": Color.MAGENTA,
    }
    color = level_map.get(level)
    if color:
        return colorize(f"[{level:<7}]", color)
    return f"[{level:<7}]"


# ---------------------------------------------------------------------------
# 运行报告生成
# ---------------------------------------------------------------------------

@dataclass
class RunReport:
    """运行报告数据。"""

    generated_at: str
    env: str
    loop_count: int
    duration_seconds: float
    stats: LogStats
    top_errors: List[str] = field(default_factory=list)
    top_warnings: List[str] = field(default_factory=list)
    health_status: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "env": self.env,
            "loop_count": self.loop_count,
            "duration_seconds": self.duration_seconds,
            "health_status": self.health_status,
            "stats": self.stats.to_dict(),
            "top_errors": self.top_errors,
            "top_warnings": self.top_warnings,
        }

    def to_text(self) -> str:
        """渲染报告为文本格式。"""
        from root.left.app.left.src.utils_main.cli_formatter import format_duration

        lines: List[str] = []
        lines.append(render_divider())
        lines.append(render_section("Agent 运行报告"))
        lines.append(render_divider())
        lines.append("")

        lines.append(render_key_value([
            ("生成时间", self.generated_at),
            ("环境", self.env),
            ("循环次数", self.loop_count),
            ("运行时长", format_duration(self.duration_seconds)),
            ("健康状态", format_status_label(self.health_status)),
        ]))
        lines.append("")

        # 日志统计
        lines.append(render_stats(self.stats))

        # Top 错误
        if self.top_errors:
            lines.append(render_section("关键错误"))
            for msg in self.top_errors:
                lines.append(f"  {colorize('✗', Color.RED)} {msg}")
            lines.append("")

        # Top 警告
        if self.top_warnings:
            lines.append(render_section("关键警告"))
            for msg in self.top_warnings:
                lines.append(f"  {colorize('!', Color.YELLOW)} {msg}")
            lines.append("")

        lines.append(render_divider())
        return "\n".join(lines)

    def to_json(self) -> str:
        """渲染报告为 JSON 格式。"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def generate_report(
    log_file_path: str,
    env: str = "dev",
    loop_count: int = 0,
    duration_seconds: float = 0.0,
    health_status: str = "unknown",
) -> RunReport:
    """从日志文件生成运行报告。

    Args:
        log_file_path: 日志文件路径
        env: 环境名称
        loop_count: 循环次数
        duration_seconds: 运行时长（秒）
        health_status: 健康状态

    Returns:
        RunReport 实例
    """
    entries = parse_log_file(log_file_path)
    stats = compute_stats(entries)

    # 提取 Top 错误/警告（去重后取前 5）
    top_errors = list(dict.fromkeys(stats.error_messages))[:5]
    top_warnings = list(dict.fromkeys(stats.warning_messages))[:5]

    return RunReport(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        env=env,
        loop_count=loop_count,
        duration_seconds=duration_seconds,
        stats=stats,
        top_errors=top_errors,
        top_warnings=top_warnings,
        health_status=health_status,
    )


def save_report(report: RunReport, output_path: str, fmt: str = "text") -> str:
    """保存报告到文件。

    Args:
        report: 报告对象
        output_path: 输出路径
        fmt: 格式 (text/json)

    Returns:
        保存的文件路径
    """
    content = report.to_json() if fmt == "json" else report.to_text()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path
