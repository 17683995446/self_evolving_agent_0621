"""任务调度系统测试"""
from __future__ import annotations

import time
from datetime import datetime

from root.left.app.left.src.cli import main
from root.left.app.left.src.utils_main.scheduler import (
    PRESET_CRONS,
    CronExpression,
    CronParseError,
    ScheduledTask,
    Scheduler,
    TaskExecution,
    _parse_field,
    render_history,
    render_next_runs,
    render_presets,
    render_scheduler_summary,
    render_tasks,
)


# ---------------------------------------------------------------------------
# 字段解析测试
# ---------------------------------------------------------------------------

class TestParseField:
    """测试 cron 字段解析"""

    def test_star(self):
        assert _parse_field("*", 0, 59, "分") == list(range(0, 60))

    def test_specific_value(self):
        assert _parse_field("5", 0, 59, "分") == [5]

    def test_range(self):
        assert _parse_field("1-5", 0, 59, "分") == [1, 2, 3, 4, 5]

    def test_list(self):
        assert _parse_field("1,3,5", 0, 59, "分") == [1, 3, 5]

    def test_step(self):
        assert _parse_field("*/15", 0, 59, "分") == [0, 15, 30, 45]

    def test_range_step(self):
        assert _parse_field("1-10/2", 0, 59, "分") == [1, 3, 5, 7, 9]

    def test_combined(self):
        result = _parse_field("0,15,30,45", 0, 59, "分")
        assert result == [0, 15, 30, 45]

    def test_empty_raises(self):
        try:
            _parse_field("", 0, 59, "分")
            assert False, "应抛出 CronParseError"
        except CronParseError:
            pass

    def test_out_of_range_raises(self):
        try:
            _parse_field("60", 0, 59, "分")
            assert False, "应抛出 CronParseError"
        except CronParseError:
            pass

    def test_invalid_value_raises(self):
        try:
            _parse_field("abc", 0, 59, "分")
            assert False, "应抛出 CronParseError"
        except CronParseError:
            pass

    def test_invalid_step_raises(self):
        try:
            _parse_field("*/0", 0, 59, "分")
            assert False, "应抛出 CronParseError"
        except CronParseError:
            pass

    def test_invalid_range_raises(self):
        try:
            _parse_field("5-1", 0, 59, "分")
            assert False, "应抛出 CronParseError"
        except CronParseError:
            pass


# ---------------------------------------------------------------------------
# CronExpression 测试
# ---------------------------------------------------------------------------

class TestCronExpression:
    """测试 cron 表达式"""

    def test_parse_basic(self):
        cron = CronExpression.parse("*/5 * * * *")
        assert cron.minute == [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
        assert cron.hour == list(range(24))
        assert cron.day == list(range(1, 32))
        assert cron.month == list(range(1, 13))
        assert cron.weekday == list(range(7))

    def test_parse_specific(self):
        cron = CronExpression.parse("30 9 * * 1")
        assert cron.minute == [30]
        assert cron.hour == [9]
        assert cron.weekday == [1]

    def test_parse_raw_preserved(self):
        cron = CronExpression.parse("0 2 * * *")
        assert cron.raw == "0 2 * * *"

    def test_parse_empty_raises(self):
        try:
            CronExpression.parse("")
            assert False, "应抛出 CronParseError"
        except CronParseError:
            pass

    def test_parse_wrong_fields_raises(self):
        try:
            CronExpression.parse("* * * *")
            assert False, "应抛出 CronParseError"
        except CronParseError:
            pass

    def test_parse_too_many_fields_raises(self):
        try:
            CronExpression.parse("* * * * * *")
            assert False, "应抛出 CronParseError"
        except CronParseError:
            pass

    def test_matches_true(self):
        cron = CronExpression.parse("30 9 * * *")
        dt = datetime(2024, 6, 15, 9, 30)  # 周六
        assert cron.matches(dt) is True

    def test_matches_false_minute(self):
        cron = CronExpression.parse("30 9 * * *")
        dt = datetime(2024, 6, 15, 9, 31)
        assert cron.matches(dt) is False

    def test_matches_false_hour(self):
        cron = CronExpression.parse("30 9 * * *")
        dt = datetime(2024, 6, 15, 10, 30)
        assert cron.matches(dt) is False

    def test_matches_weekday(self):
        # 周一 9:30
        cron = CronExpression.parse("30 9 * * 1")
        # 2024-06-17 是周一
        dt = datetime(2024, 6, 17, 9, 30)
        assert cron.matches(dt) is True
        # 2024-06-18 是周二
        dt2 = datetime(2024, 6, 18, 9, 30)
        assert cron.matches(dt2) is False

    def test_matches_sunday(self):
        # 周日 0
        cron = CronExpression.parse("0 0 * * 0")
        # 2024-06-16 是周日
        dt = datetime(2024, 6, 16, 0, 0)
        assert cron.matches(dt) is True

    def test_next_run_every_minute(self):
        cron = CronExpression.parse("* * * * *")
        now = datetime(2024, 6, 15, 10, 0)
        nxt = cron.next_run(now)
        assert nxt == datetime(2024, 6, 15, 10, 1)

    def test_next_run_next_hour(self):
        cron = CronExpression.parse("0 * * * *")
        now = datetime(2024, 6, 15, 10, 30)
        nxt = cron.next_run(now)
        assert nxt == datetime(2024, 6, 15, 11, 0)

    def test_next_run_next_day(self):
        cron = CronExpression.parse("0 0 * * *")
        now = datetime(2024, 6, 15, 10, 0)
        nxt = cron.next_run(now)
        assert nxt == datetime(2024, 6, 16, 0, 0)

    def test_next_run_default_now(self):
        cron = CronExpression.parse("* * * * *")
        nxt = cron.next_run()
        assert isinstance(nxt, datetime)
        # 应在当前时间之后
        assert nxt > datetime.now().replace(second=0, microsecond=0)

    def test_to_dict(self):
        cron = CronExpression.parse("30 9 * * 1")
        d = cron.to_dict()
        assert d["raw"] == "30 9 * * 1"
        assert d["minute"] == [30]
        assert d["hour"] == [9]
        assert d["weekday"] == [1]


# ---------------------------------------------------------------------------
# 预设表达式测试
# ---------------------------------------------------------------------------

class TestPresets:
    """测试预设 cron 表达式"""

    def test_presets_not_empty(self):
        assert len(PRESET_CRONS) > 0

    def test_all_presets_valid(self):
        for name, expr in PRESET_CRONS.items():
            cron = CronExpression.parse(expr)
            assert cron is not None, f"预设 {name} 表达式 {expr} 无效"

    def test_contains_common_presets(self):
        assert "every_minute" in PRESET_CRONS
        assert "hourly" in PRESET_CRONS
        assert "daily" in PRESET_CRONS
        assert "weekly" in PRESET_CRONS
        assert "monthly" in PRESET_CRONS

    def test_every_5_minutes(self):
        cron = CronExpression.parse(PRESET_CRONS["every_5_minutes"])
        assert cron.minute == [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]

    def test_daily(self):
        cron = CronExpression.parse(PRESET_CRONS["daily"])
        assert cron.minute == [0]
        assert cron.hour == [0]


# ---------------------------------------------------------------------------
# ScheduledTask 测试
# ---------------------------------------------------------------------------

class TestScheduledTask:
    """测试定时任务"""

    def test_to_dict(self):
        task = ScheduledTask(
            name="backup",
            cron="0 2 * * *",
            command="echo backup",
            description="每日备份",
        )
        d = task.to_dict()
        assert d["name"] == "backup"
        assert d["cron"] == "0 2 * * *"
        assert d["command"] == "echo backup"
        assert d["description"] == "每日备份"
        assert d["enabled"] is True

    def test_default_values(self):
        task = ScheduledTask(name="t", cron="* * * * *", command="echo hi")
        assert task.enabled is True
        assert task.description == ""
        assert task.last_run is None
        assert task.created_at > 0


# ---------------------------------------------------------------------------
# TaskExecution 测试
# ---------------------------------------------------------------------------

class TestTaskExecution:
    """测试执行记录"""

    def test_to_dict(self):
        exe = TaskExecution(
            task_name="test",
            command="echo hi",
            started_at=1000.0,
            finished_at=1001.5,
            return_code=0,
            success=True,
            output="hi\n",
        )
        d = exe.to_dict()
        assert d["task_name"] == "test"
        assert d["return_code"] == 0
        assert d["success"] is True

    def test_duration(self):
        exe = TaskExecution(
            task_name="test",
            command="echo hi",
            started_at=1000.0,
            finished_at=1002.5,
            return_code=0,
            success=True,
        )
        assert exe.duration == 2.5


# ---------------------------------------------------------------------------
# Scheduler 测试
# ---------------------------------------------------------------------------

class TestScheduler:
    """测试调度器"""

    def test_add_and_get_task(self):
        scheduler = Scheduler()
        task = ScheduledTask(name="t1", cron="* * * * *", command="echo hi")
        scheduler.add_task(task)
        assert scheduler.get_task("t1") is not None
        assert len(scheduler.get_tasks()) == 1

    def test_add_invalid_cron_raises(self):
        scheduler = Scheduler()
        task = ScheduledTask(name="t1", cron="invalid", command="echo hi")
        try:
            scheduler.add_task(task)
            assert False, "应抛出 CronParseError"
        except CronParseError:
            pass

    def test_remove_task(self):
        scheduler = Scheduler()
        scheduler.add_task(ScheduledTask(name="t1", cron="* * * * *", command="echo hi"))
        assert scheduler.remove_task("t1") is True
        assert scheduler.get_task("t1") is None

    def test_remove_nonexistent(self):
        scheduler = Scheduler()
        assert scheduler.remove_task("nope") is False

    def test_enable_disable(self):
        scheduler = Scheduler()
        scheduler.add_task(ScheduledTask(name="t1", cron="* * * * *", command="echo hi"))
        assert scheduler.disable_task("t1") is True
        assert scheduler.get_task("t1").enabled is False
        assert scheduler.get_task("t1").next_run_time is None
        assert scheduler.enable_task("t1") is True
        assert scheduler.get_task("t1").enabled is True
        assert scheduler.get_task("t1").next_run_time is not None

    def test_enable_nonexistent(self):
        scheduler = Scheduler()
        assert scheduler.enable_task("nope") is False

    def test_disable_nonexistent(self):
        scheduler = Scheduler()
        assert scheduler.disable_task("nope") is False

    def test_get_due_tasks_disabled(self):
        scheduler = Scheduler()
        task = ScheduledTask(name="t1", cron="* * * * *", command="echo hi", enabled=False)
        scheduler.add_task(task)
        # 禁用任务不应到期
        due = scheduler.get_due_tasks(now=time.time() + 100)
        assert len(due) == 0

    def test_get_due_tasks_future(self):
        scheduler = Scheduler()
        # 未来时间执行
        future_cron = "0 0 1 1 *"
        task = ScheduledTask(name="t1", cron=future_cron, command="echo hi")
        scheduler.add_task(task)
        # 当前时间不应到期
        due = scheduler.get_due_tasks(now=time.time())
        assert len(due) == 0

    def test_execute_task_success(self):
        scheduler = Scheduler()
        task = ScheduledTask(name="t1", cron="* * * * *", command="echo hello")
        scheduler.add_task(task)
        exe = scheduler.execute_task(task, timeout=5.0)
        assert exe.success is True
        assert exe.return_code == 0
        assert "hello" in exe.output
        assert task.last_run is not None

    def test_execute_task_failure(self):
        scheduler = Scheduler()
        task = ScheduledTask(name="t1", cron="* * * * *", command="exit 1")
        scheduler.add_task(task)
        exe = scheduler.execute_task(task, timeout=5.0)
        assert exe.success is False
        assert exe.return_code == 1

    def test_history(self):
        scheduler = Scheduler()
        task = ScheduledTask(name="t1", cron="* * * * *", command="echo hi")
        scheduler.add_task(task)
        scheduler.execute_task(task, timeout=5.0)
        history = scheduler.get_history()
        assert len(history) == 1
        assert history[0].task_name == "t1"

    def test_clear_history(self):
        scheduler = Scheduler()
        task = ScheduledTask(name="t1", cron="* * * * *", command="echo hi")
        scheduler.add_task(task)
        scheduler.execute_task(task, timeout=5.0)
        scheduler.clear_history()
        assert len(scheduler.get_history()) == 0

    def test_to_dict(self):
        scheduler = Scheduler()
        scheduler.add_task(ScheduledTask(name="t1", cron="* * * * *", command="echo hi"))
        d = scheduler.to_dict()
        assert d["task_count"] == 1
        assert d["enabled_count"] == 1
        assert d["history_count"] == 0
        assert len(d["tasks"]) == 1

    def test_history_limit(self):
        """历史记录应限制最大数量"""
        scheduler = Scheduler()
        scheduler._max_history = 3
        task = ScheduledTask(name="t1", cron="* * * * *", command="echo hi")
        scheduler.add_task(task)
        for _ in range(5):
            scheduler.execute_task(task, timeout=5.0)
        history = scheduler.get_history()
        assert len(history) == 3


# ---------------------------------------------------------------------------
# 渲染测试
# ---------------------------------------------------------------------------

class TestRenderTasks:
    """测试任务列表渲染"""

    def test_empty(self):
        result = render_tasks([])
        assert "无定时任务" in result

    def test_with_tasks(self):
        task = ScheduledTask(name="t1", cron="* * * * *", command="echo hi")
        result = render_tasks([task])
        assert "定时任务" in result
        assert "t1" in result
        assert "echo hi" in result

    def test_disabled_task(self):
        task = ScheduledTask(name="t1", cron="* * * * *", command="echo hi", enabled=False)
        result = render_tasks([task])
        assert "禁用" in result


class TestRenderHistory:
    """测试历史渲染"""

    def test_empty(self):
        result = render_history([])
        assert "无执行历史" in result

    def test_with_history(self):
        exe = TaskExecution(
            task_name="t1",
            command="echo hi",
            started_at=time.time(),
            finished_at=time.time() + 0.1,
            return_code=0,
            success=True,
        )
        result = render_history([exe])
        assert "执行历史" in result
        assert "t1" in result


class TestRenderSummary:
    """测试摘要渲染"""

    def test_empty(self):
        scheduler = Scheduler()
        result = render_scheduler_summary(scheduler)
        assert "调度器摘要" in result
        assert "任务总数" in result

    def test_with_tasks(self):
        scheduler = Scheduler()
        scheduler.add_task(ScheduledTask(name="t1", cron="* * * * *", command="echo hi"))
        result = render_scheduler_summary(scheduler)
        assert "1" in result


class TestRenderPresets:
    """测试预设渲染"""

    def test_presets(self):
        result = render_presets()
        assert "预设" in result
        assert "every_minute" in result
        assert "daily" in result


class TestRenderNextRuns:
    """测试下次执行渲染"""

    def test_empty(self):
        result = render_next_runs([])
        assert "无任务" in result

    def test_with_tasks(self):
        task = ScheduledTask(name="t1", cron="* * * * *", command="echo hi")
        # 模拟下次执行时间
        task.next_run_time = time.time() + 60
        result = render_next_runs([task])
        assert "下次执行" in result
        assert "t1" in result

    def test_all_disabled(self):
        task = ScheduledTask(name="t1", cron="* * * * *", command="echo hi", enabled=False)
        result = render_next_runs([task])
        assert "无启用" in result


# ---------------------------------------------------------------------------
# CLI 集成测试
# ---------------------------------------------------------------------------

class TestCLISchedule:
    """测试 schedule 子命令"""

    def test_schedule_no_args_shows_help(self, capsys):
        rc = main(["schedule"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "用法" in captured.out

    def test_schedule_list_empty(self, capsys):
        rc = main(["schedule", "--list"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "无定时任务" in captured.out

    def test_schedule_presets(self, capsys):
        rc = main(["schedule", "--presets"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "预设" in captured.out
        assert "every_minute" in captured.out

    def test_schedule_summary(self, capsys):
        rc = main(["schedule", "--summary"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "调度器摘要" in captured.out

    def test_schedule_validate_valid(self, capsys):
        rc = main(["schedule", "--validate", "*/5 * * * *"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "有效" in captured.out

    def test_schedule_validate_invalid(self, capsys):
        rc = main(["schedule", "--validate", "invalid"])
        captured = capsys.readouterr()
        assert rc == 2
        assert "错误" in captured.err

    def test_schedule_test_valid(self, capsys):
        rc = main(["schedule", "--test", "*/5 * * * *"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "下次执行" in captured.out

    def test_schedule_test_invalid(self, capsys):
        rc = main(["schedule", "--test", "invalid"])
        captured = capsys.readouterr()
        assert rc == 2
        assert "错误" in captured.err

    def test_schedule_add_valid(self, capsys):
        rc = main(["schedule", "--add", "test_task", "* * * * *", "echo hi"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "已添加任务" in captured.out
        assert "test_task" in captured.out

    def test_schedule_add_invalid_cron(self, capsys):
        rc = main(["schedule", "--add", "test_task", "invalid", "echo hi"])
        captured = capsys.readouterr()
        assert rc == 2
        assert "错误" in captured.err

    def test_schedule_remove_nonexistent(self, capsys):
        rc = main(["schedule", "--remove", "nonexistent"])
        captured = capsys.readouterr()
        assert rc == 1
        assert "错误" in captured.err

    def test_schedule_enable_nonexistent(self, capsys):
        rc = main(["schedule", "--enable", "nonexistent"])
        captured = capsys.readouterr()
        assert rc == 1
        assert "错误" in captured.err

    def test_schedule_disable_nonexistent(self, capsys):
        rc = main(["schedule", "--disable", "nonexistent"])
        captured = capsys.readouterr()
        assert rc == 1
        assert "错误" in captured.err

    def test_schedule_next_empty(self, capsys):
        rc = main(["schedule", "--next"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "无任务" in captured.out

    def test_schedule_history_empty(self, capsys):
        rc = main(["schedule", "--history"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "无执行历史" in captured.out


# ---------------------------------------------------------------------------
# 帮助系统集成
# ---------------------------------------------------------------------------

class TestHelpIntegration:
    """测试帮助系统是否包含 schedule 命令"""

    def test_help_all_contains_schedule(self, capsys):
        rc = main(["help"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "schedule" in captured.out

    def test_help_schedule(self, capsys):
        rc = main(["help", "schedule"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "schedule" in captured.out
        assert "定时" in captured.out
