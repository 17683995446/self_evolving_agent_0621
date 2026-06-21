"""CLI 输出格式标准化

提供统一的输出格式化能力：
- 颜色支持（自动检测 TTY，尊重 NO_COLOR 环境变量）
- 表格渲染（用于状态、配置、诊断结果）
- 键值对渲染（用于状态摘要）
- 进度指示（用于长时间操作）
- 状态符号（✓/✗/● 等）

设计原则（第一性原理）：
1. 一致性：所有输出遵循相同的视觉模式
2. 可读性：结构化数据用表格，重点用颜色，长操作用进度
3. 可访问性：颜色为可选，非 TTY 或 NO_COLOR 时自动禁用
4. 可组合：格式化器可跨命令复用
"""
from __future__ import annotations

import os
import sys
from typing import Any, List, Sequence, Tuple

# ---------------------------------------------------------------------------
# 颜色支持
# ---------------------------------------------------------------------------

# ANSI 转义码
class Color:
    """ANSI 颜色转义码常量。"""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"


def supports_color(stream: Any = None) -> bool:
    """判断是否应使用颜色输出。

    遵循 NO_COLOR 环境变量约定（https://no-color.org/）：
    如果设置了 NO_COLOR（无论值），则禁用颜色。
    """
    if os.environ.get("NO_COLOR") is not None:
        return False
    if stream is None:
        stream = sys.stdout
    return getattr(stream, "isatty", lambda: False)()


def colorize(text: str, color: str, stream: Any = None) -> str:
    """如果支持颜色则为文本添加颜色，否则原样返回。"""
    if supports_color(stream):
        return f"{color}{text}{Color.RESET}"
    return text


# ---------------------------------------------------------------------------
# 状态符号
# ---------------------------------------------------------------------------

def format_pass_fail(passed: bool, stream: Any = None) -> str:
    """格式化通过/失败状态符号。"""
    if passed:
        symbol = "✓"
        return colorize(symbol, Color.GREEN, stream)
    symbol = "✗"
    return colorize(symbol, Color.RED, stream)


def format_status_label(status: str, stream: Any = None) -> str:
    """格式化状态标签（healthy/unhealthy/unknown 等）。"""
    status_lower = status.lower()
    if status_lower in ("healthy", "ok", "pass", "passed", "running"):
        return colorize(status, Color.GREEN, stream)
    if status_lower in ("unhealthy", "fail", "failed", "error", "stopped"):
        return colorize(status, Color.RED, stream)
    if status_lower in ("warning", "warn", "unknown", "pending"):
        return colorize(status, Color.YELLOW, stream)
    return status


# ---------------------------------------------------------------------------
# 表格渲染
# ---------------------------------------------------------------------------

def render_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    stream: Any = None,
) -> str:
    """渲染 ASCII 表格。

    Args:
        headers: 表头列表
        rows: 数据行列表（每行为单元格列表）
        stream: 输出流（用于判断颜色支持）

    Returns:
        表格字符串

    示例:
        >>> print(render_table(["名称", "状态"], [["A", "OK"], ["B", "FAIL"]]))
        名称  状态
        ----  ----
        A     OK
        B     FAIL
    """
    if not headers:
        return ""

    # 计算每列宽度（考虑表头与所有行）
    str_rows: List[List[str]] = [[str(cell) for cell in row] for row in rows]
    col_count = len(headers)
    widths = [len(str(h)) for h in headers]
    for row in str_rows:
        for i, cell in enumerate(row[:col_count]):
            widths[i] = max(widths[i], len(cell))

    # 构建表格
    lines: List[str] = []

    # 表头（加粗）
    header_cells = []
    for i, h in enumerate(headers):
        header_cells.append(str(h).ljust(widths[i]))
    header_line = colorize("  ".join(header_cells), Color.BOLD, stream)
    lines.append(header_line)

    # 分隔线
    separator_cells = ["-" * w for w in widths]
    lines.append(colorize("  ".join(separator_cells), Color.DIM, stream))

    # 数据行
    for row in str_rows:
        cells = []
        for i in range(col_count):
            cell = row[i] if i < len(row) else ""
            cells.append(cell.ljust(widths[i]))
        lines.append("  ".join(cells))

    return "\n".join(lines)


def render_key_value(
    pairs: Sequence[Tuple[str, Any]],
    stream: Any = None,
    indent: int = 2,
) -> str:
    """渲染键值对列表。

    Args:
        pairs: (键, 值) 元组列表
        stream: 输出流
        indent: 缩进空格数

    Returns:
        格式化字符串

    示例:
        >>> print(render_key_value([("环境", "dev"), ("循环", 10)]))
          环境:  dev
          循环:  10
    """
    if not pairs:
        return ""
    max_key_len = max(len(str(k)) for k, _ in pairs)
    lines: List[str] = []
    prefix = " " * indent
    for key, value in pairs:
        key_str = str(key).ljust(max_key_len)
        colored_key = colorize(key_str, Color.CYAN, stream)
        lines.append(f"{prefix}{colored_key}:  {value}")
    return "\n".join(lines)


def render_section(title: str, stream: Any = None) -> str:
    """渲染节标题。"""
    return colorize(f"【{title}】", Color.BOLD, stream)


def render_divider(char: str = "=", length: int = 60, stream: Any = None) -> str:
    """渲染分隔线。"""
    return colorize(char * length, Color.DIM, stream)


# ---------------------------------------------------------------------------
# 进度指示
# ---------------------------------------------------------------------------

class ProgressBar:
    """简单的进度指示器。

    用于长时间操作的进度显示。
    非交互式环境下静默（不输出）。

    示例:
        with ProgressBar("诊断中", total=6, stream=sys.stderr) as bar:
            for i in range(6):
                do_work()
                bar.update(i + 1)
    """

    def __init__(
        self,
        label: str,
        total: int,
        width: int = 30,
        stream: Any = None,
    ) -> None:
        self.label = label
        self.total = total
        self.width = width
        self.current = 0
        self.stream = stream if stream is not None else sys.stderr
        self._active = False

    def __enter__(self) -> "ProgressBar":
        self._active = supports_color(self.stream)
        if self._active:
            self._render()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._active:
            # 完成后换行
            self.stream.write("\n")
            self.stream.flush()
        self._active = False

    def update(self, current: int) -> None:
        """更新进度。"""
        self.current = current
        if self._active:
            self._render()

    def _render(self) -> None:
        """渲染进度条。"""
        if self.total <= 0:
            fraction = 0.0
        else:
            fraction = min(self.current / self.total, 1.0)
        filled = int(self.width * fraction)
        bar = "█" * filled + "░" * (self.width - filled)
        percent = int(fraction * 100)
        # 使用回车符覆盖当前行
        self.stream.write(f"\r{self.label}: [{bar}] {percent}% ({self.current}/{self.total})")
        self.stream.flush()


def format_bytes(num_bytes: int) -> str:
    """格式化字节数为人类可读形式。"""
    if num_bytes < 0:
        return f"{num_bytes} B"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def format_duration(seconds: float) -> str:
    """格式化秒数为人类可读时长。"""
    if seconds < 0:
        return f"{seconds}s"
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m{secs:.0f}s"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h{minutes}m"
