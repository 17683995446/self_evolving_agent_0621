"""决策模块单元测试"""
import pytest
from root.left.app.left.src.core_mod.decide import (
    ExplorationController, TaskSelector, ResourceBalancer, DecisionModule,
)
from root.left.app.left.src.core_mod.task import TaskPoolModule, Task
from root.left.app.left.src.utils_main.constants import TaskType, DriveType
from root.left.app.left.src.utils_main.exceptions import ValidationError, DecisionException


class TestExplorationController:
    """测试ExplorationController"""

    def test_normal_should_explore(self) -> None:
        ctrl = ExplorationController({})
        drive = {"scenario": "normal"}
        result = ctrl.should_explore(drive)
        assert isinstance(result, bool)

    def test_empty_drive(self) -> None:
        ctrl = ExplorationController({})
        result = ctrl.should_explore({})
        assert isinstance(result, bool)

    def test_boundary_emergency(self) -> None:
        ctrl = ExplorationController({})
        drive = {"scenario": "emergency"}
        assert ctrl.should_explore(drive) is False

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            ExplorationController(None)

    def test_record_choice(self) -> None:
        ctrl = ExplorationController({})
        ctrl.record_choice(True)
        assert ctrl.exploration_count == 1

    def test_current_ratio(self) -> None:
        ctrl = ExplorationController({"base_exploration_ratio": 0.3})
        assert ctrl._get_current_ratio() == 0.3


class TestTaskSelector:
    """测试TaskSelector"""

    def test_normal_select(self) -> None:
        sel = TaskSelector({})
        tasks = [Task(TaskType.SAFE, 0.5, {}), Task(TaskType.GAIN, 0.8, {})]
        drive = {"gaps": {TaskType.SAFE: 0.5, TaskType.GAIN: 0.3}}
        result = sel.select(tasks, drive)
        assert result is not None

    def test_empty_tasks(self) -> None:
        sel = TaskSelector({})
        assert sel.select([], {}) is None

    def test_boundary_single_task(self) -> None:
        sel = TaskSelector({})
        tasks = [Task(TaskType.SAFE, 0.5, {})]
        result = sel.select(tasks, {})
        assert result is not None

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            TaskSelector(None)


class TestResourceBalancer:
    """测试ResourceBalancer"""

    def test_normal_within_limits(self) -> None:
        bal = ResourceBalancer({"cpu_limit": 20.0})
        assert bal.check_limits(10.0, 10.0) is True

    def test_empty_config(self) -> None:
        bal = ResourceBalancer({})
        assert bal.check_limits(0.0, 0.0) is True

    def test_boundary_at_limit(self) -> None:
        bal = ResourceBalancer({"cpu_limit": 20.0})
        assert bal.check_limits(20.0, 20.0) is True

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            ResourceBalancer(None)

    def test_available_capacity(self) -> None:
        bal = ResourceBalancer({"cpu_limit": 20.0})
        cap = bal.get_available_capacity(10.0, 10.0)
        assert cap["cpu"] == 10.0


class TestDecisionModule:
    """测试DecisionModule"""

    def test_normal_decide(self) -> None:
        mod = DecisionModule({})
        pool_mod = TaskPoolModule({})
        pool_mod.pool.add(Task(TaskType.SAFE, 0.5, {}))
        drive = {"scenario": "normal", "gaps": {TaskType.SAFE: 0.5}}
        result = mod.decide(pool_mod.pool, drive, [], 1, 0.0, 0.0)
        assert "selected_task" in result

    def test_empty_pool(self) -> None:
        mod = DecisionModule({})
        pool_mod = TaskPoolModule({})
        drive = {"scenario": "normal", "gaps": {}}
        result = mod.decide(pool_mod.pool, drive, [], 1, 0.0, 0.0)
        assert result["selected_task"] is None

    def test_boundary_resource_exceeded(self) -> None:
        mod = DecisionModule({"resource_balancer": {"cpu_limit": 10.0}})
        pool_mod = TaskPoolModule({})
        drive = {"scenario": "normal", "gaps": {}}
        with pytest.raises(DecisionException):
            mod.decide(pool_mod.pool, drive, [], 1, 20.0, 0.0)

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            DecisionModule(None)

    def test_should_pause(self) -> None:
        mod = DecisionModule({})
        drive = {"gaps": {DriveType.SAFE: 0.8}}
        assert mod.should_pause(drive) is True

    def test_should_not_pause(self) -> None:
        mod = DecisionModule({})
        drive = {"gaps": {DriveType.SAFE: 0.5}}
        assert mod.should_pause(drive) is False
