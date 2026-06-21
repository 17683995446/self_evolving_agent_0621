"""CLI 输出格式标准化测试"""
from __future__ import annotations

import io
import os
from unittest.mock import patch

from root.left.app.left.src.utils_main.cli_formatter import (
    Color,
    ProgressBar,
    colorize,
    format_bytes,
    format_duration,
    format_pass_fail,
    format_status_label,
    render_divider,
    render_key_value,
    render_section,
    render_table,
    supports_color,
)


# ---------------------------------------------------------------------------
# 颜色支持测试
# ---------------------------------------------------------------------------

class TestSupportsColor:
    """测试颜色支持判断"""

    def test_no_color_env_disables(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            assert supports_color() is False

    def test_no_color_empty_string_disables(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": ""}):
            assert supports_color() is False

    def test_non_tty_disables(self) -> None:
        stream = io.StringIO()
        assert supports_color(stream) is False


class TestColorize:
    """测试颜色化函数"""

    def test_colorize_with_no_color_env(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            result = colorize("hello", Color.RED)
            assert result == "hello"

    def test_colorize_non_tty_returns_plain(self) -> None:
        stream = io.StringIO()
        with patch.dict(os.environ, {}, clear=True):
            result = colorize("hello", Color.RED, stream)
            assert result == "hello"


# ---------------------------------------------------------------------------
# 状态符号测试
# ---------------------------------------------------------------------------

class TestFormatPassFail:
    """测试通过/失败符号"""

    def test_pass_returns_checkmark(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            result = format_pass_fail(True)
            assert "✓" in result

    def test_fail_returns_x(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            result = format_pass_fail(False)
            assert "✗" in result


class TestFormatStatusLabel:
    """测试状态标签格式化"""

    def test_healthy_label(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            assert format_status_label("healthy") == "healthy"

    def test_unhealthy_label(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            assert format_status_label("unhealthy") == "unhealthy"

    def test_unknown_label(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            assert format_status_label("unknown") == "unknown"

    def test_running_label(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            assert format_status_label("running") == "running"

    def test_other_label_unchanged(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            assert format_status_label("custom") == "custom"


# ---------------------------------------------------------------------------
# 表格渲染测试
# ---------------------------------------------------------------------------

class TestRenderTable:
    """测试表格渲染"""

    def test_basic_table(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            result = render_table(["名称", "状态"], [["A", "OK"], ["B", "FAIL"]])
            lines = result.split("\n")
            assert "名称" in lines[0]
            assert "状态" in lines[0]
            assert "A" in lines[2]
            assert "OK" in lines[2]
            assert "B" in lines[3]
            assert "FAIL" in lines[3]

    def test_table_with_empty_rows(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            result = render_table(["名称", "状态"], [])
            lines = result.split("\n")
            assert "名称" in lines[0]
            assert "状态" in lines[0]

    def test_table_empty_headers_returns_empty(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            result = render_table([], [["A"]])
            assert result == ""

    def test_table_column_width_alignment(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            result = render_table(["名称", "值"], [["x", "1"], ["longer_name", "100"]])
            lines = result.split("\n")
            # 表头和分隔线和数据行都应该存在
            assert len(lines) == 4  # header + separator + 2 rows

    def test_table_handles_non_string_cells(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            result = render_table(["数量"], [[42], [True]])
            assert "42" in result
            assert "True" in result


class TestRenderKeyValue:
    """测试键值对渲染"""

    def test_basic_key_value(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            result = render_key_value([("环境", "dev"), ("循环", 10)])
            assert "环境" in result
            assert "dev" in result
            assert "循环" in result
            assert "10" in result

    def test_key_value_empty_returns_empty(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            assert render_key_value([]) == ""

    def test_key_value_alignment(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            result = render_key_value([("短", "a"), ("长键名", "b")])
            lines = result.split("\n")
            # 两个键值对应该各占一行
            assert len(lines) == 2


class TestRenderSection:
    """测试节标题渲染"""

    def test_section_contains_title(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            result = render_section("测试")
            assert "测试" in result
            assert "【" in result
            assert "】" in result


class TestRenderDivider:
    """测试分隔线渲染"""

    def test_divider_default(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            result = render_divider()
            assert len(result) == 60
            assert "=" in result

    def test_divider_custom(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            result = render_divider("-", 20)
            assert len(result) == 20
            assert result == "-" * 20


# ---------------------------------------------------------------------------
# 进度条测试
# ---------------------------------------------------------------------------

class TestProgressBar:
    """测试进度条"""

    def test_progress_bar_non_tty_silent(self) -> None:
        """非 TTY 环境下进度条应静默"""
        stream = io.StringIO()
        with patch.dict(os.environ, {}, clear=True):
            with ProgressBar("测试", total=5, stream=stream) as bar:
                for i in range(5):
                    bar.update(i + 1)
        # 非交互式下不应有输出
        assert stream.getvalue() == ""

    def test_progress_bar_no_color_silent(self) -> None:
        """NO_COLOR 环境下进度条应静默"""
        stream = io.StringIO()
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            with ProgressBar("测试", total=5, stream=stream) as bar:
                bar.update(5)
        assert stream.getvalue() == ""

    def test_progress_bar_update_sets_current(self) -> None:
        stream = io.StringIO()
        bar = ProgressBar("测试", total=10, stream=stream)
        bar.update(3)
        assert bar.current == 3
        bar.update(7)
        assert bar.current == 7


# ---------------------------------------------------------------------------
# 格式化辅助函数测试
# ---------------------------------------------------------------------------

class TestFormatBytes:
    """测试字节格式化"""

    def test_bytes(self) -> None:
        assert format_bytes(0) == "0 B"
        assert format_bytes(512) == "512 B"
        assert format_bytes(1023) == "1023 B"

    def test_kilobytes(self) -> None:
        assert format_bytes(1024) == "1.0 KB"
        assert format_bytes(1536) == "1.5 KB"

    def test_megabytes(self) -> None:
        assert format_bytes(1048576) == "1.0 MB"

    def test_gigabytes(self) -> None:
        assert format_bytes(1073741824) == "1.0 GB"

    def test_negative(self) -> None:
        assert format_bytes(-1) == "-1 B"


class TestFormatDuration:
    """测试时长格式化"""

    def test_seconds(self) -> None:
        assert format_duration(0.5) == "0.5s"
        assert format_duration(30) == "30.0s"

    def test_minutes(self) -> None:
        assert "m" in format_duration(90)
        assert "s" in format_duration(90)

    def test_hours(self) -> None:
        assert "h" in format_duration(3700)
        assert "m" in format_duration(3700)

    def test_negative(self) -> None:
        assert format_duration(-1) == "-1s"
