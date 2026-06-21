"""资源边界测试"""
import pytest
import time
from root.left.app.left.src.core_mod.task import TaskPool, Task, TaskType, TaskStatus
from root.left.app.left.src.core_mod.decide import ResourceBalancer, DecisionModule
from root.left.app.left.src.core_mod.drive import DriveEngine
from root.left.app.left.src.utils_main.constants import DriveType
from root.left.app.left.src.utils_main.exceptions import DecisionException


class TestResourceBalancer:
    """测试资源平衡器边界"""

    def test_cpu_at_limit(self) -> None:
        bal = ResourceBalancer({"cpu_limit": 20.0})
        assert bal.check_limits(20.0, 10.0) is True

    def test_cpu_over_limit(self) -> None:
        bal = ResourceBalancer({"cpu_limit": 20.0})
        assert bal.check_limits(20.1, 10.0) is False

    def test_memory_at_limit(self) -> None:
        bal = ResourceBalancer({"memory_limit": 20.0})
        assert bal.check_limits(10.0, 20.0) is True

    def test_memory_over_limit(self) -> None:
        bal = ResourceBalancer({"memory_limit": 20.0})
        assert bal.check_limits(10.0, 20.1) is False

    def test_available_capacity_zero(self) -> None:
        bal = ResourceBalancer({"cpu_limit": 20.0, "memory_limit": 20.0})
        cap = bal.get_available_capacity(20.0, 20.0)
        assert cap["cpu"] == 0.0
        assert cap["memory"] == 0.0


class TestDecisionResourceLimits:
    """测试决策模块资源限制"""

    def test_decide_with_high_cpu(self) -> None:
        mod = DecisionModule({"resource_balancer": {"cpu_limit": 10.0}})
        from root.left.app.left.src.core_mod.task import TaskPool
        pool = TaskPool({})
        drive = {"scenario": "normal", "gaps": {}}
        with pytest.raises(DecisionException):
            mod.decide(pool, drive, [], 1, 15.0, 0.0)

    def test_decide_with_high_memory(self) -> None:
        mod = DecisionModule({"resource_balancer": {"memory_limit": 10.0}})
        from root.left.app.left.src.core_mod.task import TaskPool
        pool = TaskPool({})
        drive = {"scenario": "normal", "gaps": {}}
        with pytest.raises(DecisionException):
            mod.decide(pool, drive, [], 1, 0.0, 15.0)


class TestTaskPoolLimits:
    """测试任务池边界"""

    def test_pool_max_size(self) -> None:
        pool = TaskPool({"max_size": 2})
        pool.add(Task(TaskType.SAFE, 0.5, {}))
        pool.add(Task(TaskType.SAFE, 0.5, {}))
        result = pool.add(Task(TaskType.SAFE, 0.6, {}))
        assert result is True
        assert len(pool.tasks) == 2

    def test_pool_clear_completed(self) -> None:
        pool = TaskPool({})
        task = Task(TaskType.SAFE, 0.5, {})
        pool.add(task)
        pool.update_status(task.task_id, TaskStatus.COMPLETED)
        assert pool.clear_completed() == 1
        assert len(pool.tasks) == 0


class TestDriveEnginePerformance:
    """测试驱力引擎性能"""

    def test_compute_performance(self) -> None:
        engine = DriveEngine({})
        state = {"system_metrics": {"cpu_percent": 50.0, "memory_percent": 50.0}}
        start = time.time()
        for _ in range(100):
            engine.compute(state, 0.1, [])
        elapsed = time.time() - start
        assert elapsed < 1.0

    def test_interrupt_boundary(self) -> None:
        engine = DriveEngine({})
        assert engine.should_interrupt({"gaps": {DriveType.SAFE: 0.71}}) is True
        assert engine.should_interrupt({"gaps": {DriveType.SAFE: 0.69}}) is False
