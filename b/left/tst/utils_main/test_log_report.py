"""日志可视化与运行报告生成测试"""
from __future__ import annotations

import json
import os

import pytest

from root.left.app.left.src.cli import build_parser, main
from root.left.app.left.src.utils_main.log_report import (
    LogStats,
    compute_stats,
    filter_entries,
    generate_report,
    parse_log_file,
    parse_log_line,
    render_entries,
    render_stats,
    save_report,
)


# ---------------------------------------------------------------------------
# 测试数据
# ---------------------------------------------------------------------------

SAMPLE_LOG_LINES = [
    "[2026-06-20 10:00:00] [INFO    ] [SelfEvolvingAgent] [main] Agent 启动",
    "[2026-06-20 10:00:01] [DEBUG   ] [SelfEvolvingAgent] [main] Loop 1 started",
    "[2026-06-20 10:00:02] [INFO    ] [SelfEvolvingAgent] [phase1] Phase1 completed",
    "[2026-06-20 10:00:03] [WARNING ] [SelfEvolvingAgent] [main] Pause triggered",
    "[2026-06-20 10:00:04] [ERROR   ] [SelfEvolvingAgent] [main] Task failed",
    "[2026-06-20 10:00:05] [INFO    ] [SelfEvolvingAgent] [main] Agent stopped",
    "",
    "not a log line",
    "[2026-06-20 10:00:06] [CRITICAL] [SelfEvolvingAgent] [main] Fatal error",
]


# ---------------------------------------------------------------------------
# 日志解析测试
# ---------------------------------------------------------------------------

class TestParseLogLine:
    """测试单行日志解析"""

    def test_parse_valid_line(self) -> None:
        line = "[2026-06-20 10:00:00] [INFO    ] [SelfEvolvingAgent] [main] Agent 启动"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.timestamp == "2026-06-20 10:00:00"
        assert entry.level == "INFO"
        assert entry.logger == "SelfEvolvingAgent"
        assert entry.module == "main"
        assert entry.message == "Agent 启动"

    def test_parse_line_without_module(self) -> None:
        line = "[2026-06-20 10:00:00] [INFO    ] [SelfEvolvingAgent] No module here"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.module == ""
        assert entry.message == "No module here"

    def test_parse_empty_line(self) -> None:
        assert parse_log_line("") is None

    def test_parse_non_log_line(self) -> None:
        assert parse_log_line("not a log line") is None

    def test_parse_critical_level(self) -> None:
        line = "[2026-06-20 10:00:00] [CRITICAL] [SelfEvolvingAgent] [main] Fatal"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.level == "CRITICAL"


class TestParseLogFile:
    """测试日志文件解析"""

    def test_parse_file(self, tmp_path) -> None:
        log_file = tmp_path / "test.log"
        log_file.write_text("\n".join(SAMPLE_LOG_LINES), encoding="utf-8")
        entries = parse_log_file(str(log_file))
        # 7 条有效日志（排除空行和非日志行）
        assert len(entries) == 7
        assert entries[0].level == "INFO"
        assert entries[-1].level == "CRITICAL"

    def test_parse_nonexistent_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            parse_log_file("/nonexistent/path.log")


# ---------------------------------------------------------------------------
# 统计测试
# ---------------------------------------------------------------------------

class TestComputeStats:
    """测试日志统计"""

    def test_stats_total(self) -> None:
        entries = [parse_log_line(line) for line in SAMPLE_LOG_LINES if line and line.startswith("[")]
        entries = [e for e in entries if e is not None]
        stats = compute_stats(entries)
        assert stats.total == 7

    def test_stats_by_level(self) -> None:
        entries = [parse_log_line(line) for line in SAMPLE_LOG_LINES if line and line.startswith("[")]
        entries = [e for e in entries if e is not None]
        stats = compute_stats(entries)
        assert stats.by_level.get("INFO", 0) == 3
        assert stats.by_level.get("DEBUG", 0) == 1
        assert stats.by_level.get("WARNING", 0) == 1
        assert stats.by_level.get("ERROR", 0) == 1
        assert stats.by_level.get("CRITICAL", 0) == 1

    def test_stats_by_module(self) -> None:
        entries = [parse_log_line(line) for line in SAMPLE_LOG_LINES if line and line.startswith("[")]
        entries = [e for e in entries if e is not None]
        stats = compute_stats(entries)
        assert stats.by_module.get("main", 0) == 6
        assert stats.by_module.get("phase1", 0) == 1

    def test_stats_time_range(self) -> None:
        entries = [parse_log_line(line) for line in SAMPLE_LOG_LINES if line and line.startswith("[")]
        entries = [e for e in entries if e is not None]
        stats = compute_stats(entries)
        assert stats.time_range_start == "2026-06-20 10:00:00"
        assert stats.time_range_end == "2026-06-20 10:00:06"

    def test_stats_error_messages(self) -> None:
        entries = [parse_log_line(line) for line in SAMPLE_LOG_LINES if line and line.startswith("[")]
        entries = [e for e in entries if e is not None]
        stats = compute_stats(entries)
        assert len(stats.error_messages) == 1
        assert "Task failed" in stats.error_messages[0]

    def test_stats_warning_messages(self) -> None:
        entries = [parse_log_line(line) for line in SAMPLE_LOG_LINES if line and line.startswith("[")]
        entries = [e for e in entries if e is not None]
        stats = compute_stats(entries)
        assert len(stats.warning_messages) == 1
        assert "Pause triggered" in stats.warning_messages[0]

    def test_stats_empty_entries(self) -> None:
        stats = compute_stats([])
        assert stats.total == 0
        assert stats.by_level == {}


# ---------------------------------------------------------------------------
# 过滤测试
# ---------------------------------------------------------------------------

class TestFilterEntries:
    """测试日志过滤"""

    @pytest.fixture
    def entries(self) -> list:
        return [parse_log_line(line) for line in SAMPLE_LOG_LINES if line and line.startswith("[")]

    def test_filter_by_level(self, entries) -> None:
        filtered = filter_entries(entries, level="error")
        assert len(filtered) == 1
        assert filtered[0].level == "ERROR"

    def test_filter_by_level_case_insensitive(self, entries) -> None:
        filtered = filter_entries(entries, level="info")
        assert len(filtered) == 3
        assert all(e.level == "INFO" for e in filtered)

    def test_filter_by_module(self, entries) -> None:
        filtered = filter_entries(entries, module="phase1")
        assert len(filtered) == 1
        assert filtered[0].module == "phase1"

    def test_filter_by_keyword(self, entries) -> None:
        filtered = filter_entries(entries, keyword="Agent")
        assert len(filtered) == 2  # "Agent 启动" 和 "Agent stopped"

    def test_filter_by_limit(self, entries) -> None:
        filtered = filter_entries(entries, limit=3)
        assert len(filtered) == 3
        # 应取最后 3 条
        assert filtered[-1].level == "CRITICAL"

    def test_filter_no_match(self, entries) -> None:
        filtered = filter_entries(entries, keyword="nonexistent")
        assert len(filtered) == 0

    def test_filter_combined(self, entries) -> None:
        filtered = filter_entries(entries, level="info", keyword="Agent")
        assert len(filtered) == 2


# ---------------------------------------------------------------------------
# 渲染测试
# ---------------------------------------------------------------------------

class TestRenderStats:
    """测试统计渲染"""

    def test_render_stats_contains_title(self) -> None:
        entries = [parse_log_line(line) for line in SAMPLE_LOG_LINES if line and line.startswith("[")]
        entries = [e for e in entries if e is not None]
        stats = compute_stats(entries)
        text = render_stats(stats)
        assert "日志统计" in text

    def test_render_stats_contains_total(self) -> None:
        entries = [parse_log_line(line) for line in SAMPLE_LOG_LINES if line and line.startswith("[")]
        entries = [e for e in entries if e is not None]
        stats = compute_stats(entries)
        text = render_stats(stats)
        assert "7" in text

    def test_render_stats_empty(self) -> None:
        stats = LogStats()
        text = render_stats(stats)
        assert "日志统计" in text


class TestRenderEntries:
    """测试条目渲染"""

    def test_render_entries(self) -> None:
        entries = [parse_log_line(line) for line in SAMPLE_LOG_LINES if line and line.startswith("[")]
        entries = [e for e in entries if e is not None]
        text = render_entries(entries)
        assert "Agent 启动" in text
        assert "INFO" in text

    def test_render_empty_entries(self) -> None:
        text = render_entries([])
        assert "无日志条目" in text


# ---------------------------------------------------------------------------
# 运行报告测试
# ---------------------------------------------------------------------------

class TestRunReport:
    """测试运行报告"""

    def test_report_to_dict(self, tmp_path) -> None:
        log_file = tmp_path / "test.log"
        log_file.write_text("\n".join(SAMPLE_LOG_LINES), encoding="utf-8")
        report = generate_report(str(log_file), env="dev", loop_count=10, duration_seconds=60.0)
        d = report.to_dict()
        assert d["env"] == "dev"
        assert d["loop_count"] == 10
        assert d["duration_seconds"] == 60.0
        assert "stats" in d
        assert d["stats"]["total"] == 7

    def test_report_to_text(self, tmp_path) -> None:
        log_file = tmp_path / "test.log"
        log_file.write_text("\n".join(SAMPLE_LOG_LINES), encoding="utf-8")
        report = generate_report(str(log_file))
        text = report.to_text()
        assert "运行报告" in text
        assert "日志统计" in text

    def test_report_to_json(self, tmp_path) -> None:
        log_file = tmp_path / "test.log"
        log_file.write_text("\n".join(SAMPLE_LOG_LINES), encoding="utf-8")
        report = generate_report(str(log_file))
        json_str = report.to_json()
        data = json.loads(json_str)
        assert "generated_at" in data
        assert "stats" in data

    def test_report_top_errors(self, tmp_path) -> None:
        log_file = tmp_path / "test.log"
        log_file.write_text("\n".join(SAMPLE_LOG_LINES), encoding="utf-8")
        report = generate_report(str(log_file))
        assert len(report.top_errors) > 0
        assert "Task failed" in report.top_errors[0]


class TestSaveReport:
    """测试报告保存"""

    def test_save_text_report(self, tmp_path) -> None:
        log_file = tmp_path / "test.log"
        log_file.write_text("\n".join(SAMPLE_LOG_LINES), encoding="utf-8")
        report = generate_report(str(log_file))
        output = str(tmp_path / "report.txt")
        save_report(report, output, fmt="text")
        assert os.path.exists(output)
        with open(output, "r", encoding="utf-8") as f:
            content = f.read()
        assert "运行报告" in content

    def test_save_json_report(self, tmp_path) -> None:
        log_file = tmp_path / "test.log"
        log_file.write_text("\n".join(SAMPLE_LOG_LINES), encoding="utf-8")
        report = generate_report(str(log_file))
        output = str(tmp_path / "report.json")
        save_report(report, output, fmt="json")
        assert os.path.exists(output)
        with open(output, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "stats" in data


# ---------------------------------------------------------------------------
# CLI logs 子命令测试
# ---------------------------------------------------------------------------

class TestCLILogsParser:
    """测试 logs 子命令参数解析"""

    def test_logs_parser_basic(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["logs", "test.log"])
        assert args.command == "logs"
        assert args.file == "test.log"
        assert args.level is None
        assert args.stats is False

    def test_logs_parser_with_filters(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["logs", "test.log", "--level", "ERROR", "--module", "main", "--tail", "10"])
        assert args.level == "ERROR"
        assert args.module == "main"
        assert args.tail == 10

    def test_logs_parser_stats(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["logs", "test.log", "--stats"])
        assert args.stats is True


class TestCLILogsCommand:
    """测试 logs 子命令执行"""

    def test_logs_nonexistent_file(self, capsys) -> None:
        exit_code = main(["logs", "/nonexistent/file.log"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "不存在" in captured.err

    def test_logs_view(self, capsys, tmp_path) -> None:
        log_file = tmp_path / "test.log"
        log_file.write_text("\n".join(SAMPLE_LOG_LINES), encoding="utf-8")
        exit_code = main(["logs", str(log_file)])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Agent 启动" in captured.out

    def test_logs_stats(self, capsys, tmp_path) -> None:
        log_file = tmp_path / "test.log"
        log_file.write_text("\n".join(SAMPLE_LOG_LINES), encoding="utf-8")
        exit_code = main(["logs", str(log_file), "--stats"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "日志统计" in captured.out

    def test_logs_filter_level(self, capsys, tmp_path) -> None:
        log_file = tmp_path / "test.log"
        log_file.write_text("\n".join(SAMPLE_LOG_LINES), encoding="utf-8")
        exit_code = main(["logs", str(log_file), "--level", "ERROR"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Task failed" in captured.out
        assert "Agent 启动" not in captured.out

    def test_logs_tail(self, capsys, tmp_path) -> None:
        log_file = tmp_path / "test.log"
        log_file.write_text("\n".join(SAMPLE_LOG_LINES), encoding="utf-8")
        exit_code = main(["logs", str(log_file), "--tail", "2"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Fatal error" in captured.out


# ---------------------------------------------------------------------------
# CLI report 子命令测试
# ---------------------------------------------------------------------------

class TestCLIReportParser:
    """测试 report 子命令参数解析"""

    def test_report_parser_basic(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["report", "test.log"])
        assert args.command == "report"
        assert args.file == "test.log"
        assert args.json is False

    def test_report_parser_with_options(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "report", "test.log", "--env", "prod", "--loop-count", "100",
            "--duration", "3600", "--json", "--output", "out.json",
        ])
        assert args.env == "prod"
        assert args.loop_count == 100
        assert args.duration == 3600.0
        assert args.json is True
        assert args.output == "out.json"


class TestCLIReportCommand:
    """测试 report 子命令执行"""

    def test_report_nonexistent_file(self, capsys) -> None:
        exit_code = main(["report", "/nonexistent/file.log"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "不存在" in captured.err

    def test_report_text(self, capsys, tmp_path) -> None:
        log_file = tmp_path / "test.log"
        log_file.write_text("\n".join(SAMPLE_LOG_LINES), encoding="utf-8")
        exit_code = main(["report", str(log_file)])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "运行报告" in captured.out

    def test_report_json(self, capsys, tmp_path) -> None:
        log_file = tmp_path / "test.log"
        log_file.write_text("\n".join(SAMPLE_LOG_LINES), encoding="utf-8")
        exit_code = main(["report", str(log_file), "--json"])
        captured = capsys.readouterr()
        assert exit_code == 0
        data = json.loads(captured.out)
        assert "stats" in data

    def test_report_save_to_file(self, capsys, tmp_path) -> None:
        log_file = tmp_path / "test.log"
        log_file.write_text("\n".join(SAMPLE_LOG_LINES), encoding="utf-8")
        output = str(tmp_path / "report.txt")
        exit_code = main(["report", str(log_file), "--output", output])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert os.path.exists(output)
        assert "已保存" in captured.err
