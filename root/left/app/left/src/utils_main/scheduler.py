"""任务调度系统

提供基于 cron 表达式的定时任务调度能力。

设计原则（第一性原理）：
1. 可表达：用标准 5 字段 cron 表达式描述时间计划
   （分 时 日 月 周）
2. 可调度：解析 cron 表达式，计算下一次执行时间
3. 可执行：到点触发任务，记录执行结果
4. 可观测：查看待执行任务、历史执行记录
5. 可管理：添加/删除/启用/禁用任务

cron 表达式字段说明：
- 分钟：0-59
- 小时：0-23
- 日：1-31
- 月：1-12
- 周：0-6（0=周日，6=周六）

支持语法：
- *：任意值
- 5：具体值
- 1-5：范围
- 1,3,5：列表
- */5：步长
- 1-10/2：范围步长
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from root.left.app.left.src.utils_main.cli_formatter import (
    Color,
    colorize,
    render_divider,
    render_key_value,
    render_section,
    render_table,
)


# ---------------------------------------------------------------------------
# cron 表达式解析
# ---------------------------------------------------------------------------

# 各字段范围（最小值, 最大值）
CRON_FIELD_RANGES: List[Tuple[int, int]] = [
    (0, 59),   # 分钟
    (0, 23),   # 小时
    (1, 31),   # 日
    (1, 12),   # 月
    (0, 6),    # 周（0=周日）
]

CRON_FIELD_NAMES: List[str] = ["分钟", "小时", "日", "月", "周"]


class CronParseError(ValueError):
    """cron 表达式解析错误。"""


def _parse_field(expr: str, min_val: int, max_val: int, field_name: str) -> List[int]:
    """解析单个 cron 字段，返回匹配值列表。

    Args:
        expr: 字段表达式
        min_val: 字段最小值
        max_val: 字段最大值
        field_name: 字段名（用于错误信息）

    Returns:
        排序后的匹配值列表

    Raises:
        CronParseError: 解析失败
    """
    if not expr:
        raise CronParseError(f"{field_name} 字段为空")

    values: set = set()

    # 处理逗号分隔的列表
    for part in expr.split(","):
        part = part.strip()
        if not part:
            raise CronParseError(f"{field_name} 字段含空段")

        # 处理步长
        step = 1
        if "/" in part:
            range_part, _, step_str = part.partition("/")
            try:
                step = int(step_str)
            except ValueError:
                raise CronParseError(f"{field_name} 字段步长无效: {step_str}")
            if step <= 0:
                raise CronParseError(f"{field_name} 字段步长必须为正数: {step}")
            part = range_part

        # 处理范围
        if part == "*":
            start, end = min_val, max_val
        elif "-" in part:
            try:
                start_str, _, end_str = part.partition("-")
                start = int(start_str)
                end = int(end_str)
            except ValueError:
                raise CronParseError(f"{field_name} 字段范围无效: {part}")
        else:
            try:
                start = int(part)
                end = start if step == 1 else max_val
            except ValueError:
                raise CronParseError(f"{field_name} 字段值无效: {part}")

        # 校验范围
        if start < min_val or end > max_val:
            raise CronParseError(
                f"{field_name} 字段值超出范围 [{min_val}-{max_val}]: {part}"
            )
        if start > end:
            raise CronParseError(f"{field_name} 字段范围起始大于结束: {part}")

        # 生成值
        for v in range(start, end + 1, step):
            values.add(v)

    return sorted(values)


@dataclass
class CronExpression:
    """cron 表达式。

    5 字段：分 时 日 月 周
    """

    minute: List[int]
    hour: List[int]
    day: List[int]
    month: List[int]
    weekday: List[int]
    raw: str = ""

    @classmethod
    def parse(cls, expr: str) -> "CronExpression":
        """解析 cron 表达式字符串。

        Args:
            expr: 5 字段 cron 表达式

        Returns:
            CronExpression 实例

        Raises:
            CronParseError: 解析失败
        """
        if not expr or not expr.strip():
            raise CronParseError("cron 表达式为空")

        parts = expr.strip().split()
        if len(parts) != 5:
            raise CronParseError(
                f"cron 表达式必须为 5 个字段，实际 {len(parts)} 个: {expr!r}"
            )

        fields: List[List[int]] = []
        for i, (part, (min_v, max_v), name) in enumerate(
            zip(parts, CRON_FIELD_RANGES, CRON_FIELD_NAMES)
        ):
            fields.append(_parse_field(part, min_v, max_v, name))

        return cls(
            minute=fields[0],
            hour=fields[1],
            day=fields[2],
            month=fields[3],
            weekday=fields[4],
            raw=expr.strip(),
        )

    def matches(self, dt: datetime) -> bool:
        """判断给定时间是否匹配 cron 表达式。

        Args:
            dt: 待匹配时间

        Returns:
            是否匹配
        """
        if dt.minute not in self.minute:
            return False
        if dt.hour not in self.hour:
            return False
        if dt.month not in self.month:
            return False
        # 日和周：cron 规范中，两者任一匹配即触发（特殊处理）
        # 这里采用严格匹配：两者都需匹配。若用户用 * 则不影响。
        if dt.day not in self.day:
            return False
        # Python weekday(): 0=周一...6=周日
        # cron weekday: 0=周日...6=周六
        cron_wd = (dt.weekday() + 1) % 7
        if cron_wd not in self.weekday:
            return False
        return True

    def next_run(self, after: Optional[datetime] = None) -> datetime:
        """计算下一次匹配时间。

        Args:
            after: 起始时间（不含），默认当前时间

        Returns:
            下一次匹配的 datetime

        Raises:
            CronParseError: 一年内无匹配时间
        """
        if after is None:
            after = datetime.now().replace(second=0, microsecond=0)
        else:
            after = after.replace(second=0, microsecond=0)

        # 从下一分钟开始逐分钟搜索
        # 优化：按字段跳跃，但为简单起见先用分钟级搜索，限制一年内
        candidate = after + timedelta(minutes=1)
        max_candidate = after + timedelta(days=366)
        while candidate < max_candidate:
            if self.matches(candidate):
                return candidate
            candidate += timedelta(minutes=1)
        raise CronParseError(f"一年内无匹配时间: {self.raw}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw": self.raw,
            "minute": self.minute,
            "hour": self.hour,
            "day": self.day,
            "month": self.month,
            "weekday": self.weekday,
        }


# ---------------------------------------------------------------------------
# 预设表达式
# ---------------------------------------------------------------------------

PRESET_CRONS: Dict[str, str] = {
    "every_minute": "* * * * *",
    "every_5_minutes": "*/5 * * * *",
    "every_15_minutes": "*/15 * * * *",
    "every_30_minutes": "*/30 * * * *",
    "hourly": "0 * * * *",
    "daily": "0 0 * * *",
    "daily_9am": "0 9 * * *",
    "weekly": "0 0 * * 0",
    "monthly": "0 0 1 * *",
    "weekdays_9am": "0 9 * * 1-5",
}


# ---------------------------------------------------------------------------
# 任务与执行记录
# ---------------------------------------------------------------------------

@dataclass
class ScheduledTask:
    """定时任务。"""

    name: str
    cron: str  # cron 表达式字符串
    command: str  # 要执行的命令
    enabled: bool = True
    description: str = ""
    created_at: float = field(default_factory=time.time)
    last_run: Optional[float] = None
    next_run_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "cron": self.cron,
            "command": self.command,
            "enabled": self.enabled,
            "description": self.description,
            "created_at": self.created_at,
            "last_run": self.last_run,
            "next_run_time": self.next_run_time,
        }


@dataclass
class TaskExecution:
    """任务执行记录。"""

    task_name: str
    command: str
    started_at: float
    finished_at: float
    return_code: int
    success: bool
    output: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_name": self.task_name,
            "command": self.command,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "return_code": self.return_code,
            "success": self.success,
            "output": self.output,
            "error": self.error,
        }

    @property
    def duration(self) -> float:
        """执行耗时（秒）。"""
        return self.finished_at - self.started_at


# ---------------------------------------------------------------------------
# 调度器
# ---------------------------------------------------------------------------

class Scheduler:
    """任务调度器。

    管理定时任务、计算下次执行时间、执行到期任务。
    """

    def __init__(self) -> None:
        self._tasks: Dict[str, ScheduledTask] = {}
        self._history: List[TaskExecution] = []
        self._max_history: int = 100

    def add_task(self, task: ScheduledTask) -> None:
        """添加任务。若同名任务已存在则覆盖。"""
        # 校验 cron 表达式
        CronExpression.parse(task.cron)
        self._tasks[task.name] = task
        self._update_next_run(task)

    def remove_task(self, name: str) -> bool:
        """移除任务。"""
        if name in self._tasks:
            del self._tasks[name]
            return True
        return False

    def get_task(self, name: str) -> Optional[ScheduledTask]:
        """获取任务。"""
        return self._tasks.get(name)

    def get_tasks(self) -> List[ScheduledTask]:
        """获取所有任务。"""
        return list(self._tasks.values())

    def enable_task(self, name: str) -> bool:
        """启用任务。"""
        task = self._tasks.get(name)
        if task is None:
            return False
        task.enabled = True
        self._update_next_run(task)
        return True

    def disable_task(self, name: str) -> bool:
        """禁用任务。"""
        task = self._tasks.get(name)
        if task is None:
            return False
        task.enabled = False
        task.next_run_time = None
        return True

    def _update_next_run(self, task: ScheduledTask) -> None:
        """更新任务的下次执行时间。"""
        if not task.enabled:
            task.next_run_time = None
            return
        try:
            cron = CronExpression.parse(task.cron)
            nxt = cron.next_run()
            task.next_run_time = nxt.timestamp()
        except CronParseError:
            task.next_run_time = None

    def get_due_tasks(self, now: Optional[float] = None) -> List[ScheduledTask]:
        """获取当前到期的任务。

        Args:
            now: 当前时间戳，默认 time.time()

        Returns:
            到期任务列表
        """
        if now is None:
            now = time.time()
        due: List[ScheduledTask] = []
        for task in self._tasks.values():
            if not task.enabled:
                continue
            if task.next_run_time is None:
                continue
            if task.next_run_time <= now:
                due.append(task)
        return due

    def execute_task(self, task: ScheduledTask, timeout: float = 60.0) -> TaskExecution:
        """执行任务。

        Args:
            task: 待执行任务
            timeout: 超时秒数

        Returns:
            执行记录
        """
        started = time.time()
        output = ""
        error = ""
        return_code = -1

        try:
            result = subprocess.run(
                task.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = result.stdout
            error = result.stderr
            return_code = result.returncode
        except subprocess.TimeoutExpired as e:
            error = f"执行超时（{timeout}s）"
            if e.stdout:
                output = e.stdout if isinstance(e.stdout, str) else e.stdout.decode("utf-8", errors="replace")
        except Exception as e:
            error = f"执行异常: {e}"

        finished = time.time()
        execution = TaskExecution(
            task_name=task.name,
            command=task.command,
            started_at=started,
            finished_at=finished,
            return_code=return_code,
            success=(return_code == 0),
            output=output,
            error=error,
        )

        # 更新任务状态
        task.last_run = finished
        self._update_next_run(task)

        # 记录历史
        self._history.append(execution)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        return execution

    def run_due(self, now: Optional[float] = None, timeout: float = 60.0) -> List[TaskExecution]:
        """执行所有到期任务。

        Args:
            now: 当前时间戳
            timeout: 单任务超时秒数

        Returns:
            执行记录列表
        """
        due = self.get_due_tasks(now)
        results: List[TaskExecution] = []
        for task in due:
            results.append(self.execute_task(task, timeout=timeout))
        return results

    def get_history(self, limit: int = 50) -> List[TaskExecution]:
        """获取执行历史。"""
        return self._history[-limit:]

    def clear_history(self) -> None:
        """清空历史。"""
        self._history.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_count": len(self._tasks),
            "enabled_count": sum(1 for t in self._tasks.values() if t.enabled),
            "history_count": len(self._history),
            "tasks": [t.to_dict() for t in self._tasks.values()],
        }


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------

def _format_timestamp(ts: Optional[float]) -> str:
    """格式化时间戳为字符串。"""
    if ts is None:
        return "-"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def render_tasks(tasks: List[ScheduledTask]) -> str:
    """渲染任务列表。"""
    if not tasks:
        return "无定时任务。"

    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section(f"定时任务（共 {len(tasks)} 个）"))
    lines.append(render_divider())
    lines.append("")

    rows: List[List[str]] = []
    for t in tasks:
        status = colorize("启用", Color.GREEN) if t.enabled else colorize("禁用", Color.GRAY)
        rows.append([
            t.name,
            t.cron,
            t.command,
            status,
            _format_timestamp(t.next_run_time),
        ])

    lines.append(render_table(
        ["名称", "cron", "命令", "状态", "下次执行"],
        rows,
    ))
    return "\n".join(lines)


def render_history(history: List[TaskExecution]) -> str:
    """渲染执行历史。"""
    if not history:
        return "无执行历史。"

    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section(f"执行历史（共 {len(history)} 条）"))
    lines.append(render_divider())
    lines.append("")

    rows: List[List[str]] = []
    for h in history:
        status = colorize("成功", Color.GREEN) if h.success else colorize("失败", Color.RED)
        rows.append([
            h.task_name,
            _format_timestamp(h.started_at),
            f"{h.duration:.2f}s",
            status,
            str(h.return_code),
        ])

    lines.append(render_table(
        ["任务", "开始时间", "耗时", "结果", "返回码"],
        rows,
    ))
    return "\n".join(lines)


def render_scheduler_summary(scheduler: Scheduler) -> str:
    """渲染调度器摘要。"""
    tasks = scheduler.get_tasks()
    history = scheduler.get_history()
    success_count = sum(1 for h in history if h.success)
    fail_count = len(history) - success_count

    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section("调度器摘要"))
    lines.append(render_divider())
    lines.append("")

    lines.append(render_key_value([
        ("任务总数", len(tasks)),
        ("启用任务", sum(1 for t in tasks if t.enabled)),
        ("禁用任务", sum(1 for t in tasks if not t.enabled)),
        ("历史记录数", len(history)),
        ("成功执行", success_count),
        ("失败执行", fail_count),
    ]))

    return "\n".join(lines)


def render_presets() -> str:
    """渲染预设 cron 表达式。"""
    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section("预设 cron 表达式"))
    lines.append(render_divider())
    lines.append("")

    rows: List[List[str]] = []
    for name, expr in PRESET_CRONS.items():
        rows.append([name, expr])

    lines.append(render_table(["名称", "表达式"], rows))
    return "\n".join(lines)


def render_next_runs(tasks: List[ScheduledTask], limit: int = 10) -> str:
    """渲染下次执行时间列表。"""
    if not tasks:
        return "无任务。"

    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section("下次执行时间"))
    lines.append(render_divider())
    lines.append("")

    # 按下次执行时间排序
    enabled = [t for t in tasks if t.enabled and t.next_run_time is not None]
    enabled.sort(key=lambda t: t.next_run_time or 0)

    rows: List[List[str]] = []
    for t in enabled[:limit]:
        rows.append([
            t.name,
            t.cron,
            _format_timestamp(t.next_run_time),
        ])

    if not rows:
        return "无启用的任务。"

    lines.append(render_table(["名称", "cron", "下次执行"], rows))
    return "\n".join(lines)
