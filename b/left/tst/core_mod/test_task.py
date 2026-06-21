"""任务池模块单元测试"""
import pytest
from root.left.app.left.src.core_mod.task import (
    Task, TaskPool, SafeTaskGenerator, GainTaskGenerator,
    EffTaskGenerator, TaskPoolModule,
)
from root.left.app.left.src.core_mod.task_templates import TaskTemplateRegistry
from root.left.app.left.src.utils_main.constants import TaskType, TaskStatus
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestTask:
    """测试Task"""

    def test_normal_init(self) -> None:
        task = Task(TaskType.SAFE, 0.5, {"action": "test"})
        assert task.task_type == TaskType.SAFE

    def test_empty_payload(self) -> None:
        task = Task(TaskType.GAIN, 0.5, {})
        assert task.payload == {}

    def test_boundary_zero_priority(self) -> None:
        task = Task(TaskType.EFF, 0.0, {})
        assert task.priority == 0.0

    def test_invalid_format_none_type(self) -> None:
        with pytest.raises(ValidationError):
            Task(None, 0.5, {})

    def test_to_dict(self) -> None:
        task = Task(TaskType.SAFE, 0.5, {})
        d = task.to_dict()
        assert "task_id" in d

    def test_status_default(self) -> None:
        task = Task(TaskType.SAFE, 0.5, {})
        assert task.status == TaskStatus.PENDING


class TestTaskPool:
    """测试TaskPool"""

    def test_normal_add(self) -> None:
        pool = TaskPool({"max_size": 10})
        task = Task(TaskType.SAFE, 0.5, {})
        assert pool.add(task) is True

    def test_empty_pool(self) -> None:
        pool = TaskPool({})
        assert pool.get_next() is None

    def test_boundary_full(self) -> None:
        pool = TaskPool({"max_size": 1})
        pool.add(Task(TaskType.SAFE, 0.5, {}))
        result = pool.add(Task(TaskType.SAFE, 0.6, {}))
        assert result is True
        assert len(pool.tasks) == 1
        assert list(pool.tasks.values())[0].priority == 0.6

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            TaskPool(None)

    def test_get_next(self) -> None:
        pool = TaskPool({})
        task = Task(TaskType.SAFE, 0.5, {})
        pool.add(task)
        next_task = pool.get_next()
        assert next_task.status == TaskStatus.RUNNING

    def test_update_status_retry(self) -> None:
        pool = TaskPool({})
        task = Task(TaskType.SAFE, 0.5, {})
        pool.add(task)
        pool.update_status(task.task_id, TaskStatus.FAILED)
        assert task.status == TaskStatus.PENDING

    def test_clear_completed(self) -> None:
        pool = TaskPool({})
        task = Task(TaskType.SAFE, 0.5, {})
        pool.add(task)
        pool.update_status(task.task_id, TaskStatus.COMPLETED)
        assert pool.clear_completed() == 1

    def test_get_by_type(self) -> None:
        pool = TaskPool({})
        pool.add(Task(TaskType.SAFE, 0.5, {}))
        assert len(pool.get_by_type(TaskType.SAFE)) == 1


class TestSafeTaskGenerator:
    """测试SafeTaskGenerator"""

    def test_normal_generate(self) -> None:
        gen = SafeTaskGenerator({}, TaskTemplateRegistry({}))
        drive = {"gaps": {TaskType.SAFE: 0.5}}
        tasks = gen.generate(drive)
        assert len(tasks) == 1

    def test_empty_drive(self) -> None:
        gen = SafeTaskGenerator({}, TaskTemplateRegistry({}))
        tasks = gen.generate({})
        assert len(tasks) == 1

    def test_boundary_low_gap(self) -> None:
        gen = SafeTaskGenerator({}, TaskTemplateRegistry({}))
        drive = {"gaps": {TaskType.SAFE: 0.1}}
        tasks = gen.generate(drive)
        assert len(tasks) == 0

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            SafeTaskGenerator(None, TaskTemplateRegistry({}))


class TestGainTaskGenerator:
    """测试GainTaskGenerator"""

    def test_normal_generate(self) -> None:
        gen = GainTaskGenerator({}, TaskTemplateRegistry({}))
        drive = {"gaps": {TaskType.GAIN: 0.5}}
        tasks = gen.generate(drive)
        assert len(tasks) == 1

    def test_empty_drive(self) -> None:
        gen = GainTaskGenerator({}, TaskTemplateRegistry({}))
        tasks = gen.generate({})
        assert len(tasks) == 1

    def test_boundary_low_gap(self) -> None:
        gen = GainTaskGenerator({}, TaskTemplateRegistry({}))
        drive = {"gaps": {TaskType.GAIN: 0.1}}
        tasks = gen.generate(drive)
        assert len(tasks) == 0

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            GainTaskGenerator(None, TaskTemplateRegistry({}))


class TestEffTaskGenerator:
    """测试EffTaskGenerator"""

    def test_normal_generate(self) -> None:
        gen = EffTaskGenerator({}, TaskTemplateRegistry({}))
        drive = {"gaps": {TaskType.EFF: 0.5}}
        tasks = gen.generate(drive)
        assert len(tasks) == 1

    def test_empty_drive(self) -> None:
        gen = EffTaskGenerator({}, TaskTemplateRegistry({}))
        tasks = gen.generate({})
        assert len(tasks) == 1

    def test_boundary_low_gap(self) -> None:
        gen = EffTaskGenerator({}, TaskTemplateRegistry({}))
        drive = {"gaps": {TaskType.EFF: 0.1}}
        tasks = gen.generate(drive)
        assert len(tasks) == 0

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            EffTaskGenerator(None, TaskTemplateRegistry({}))


class TestTaskPoolModule:
    """测试TaskPoolModule"""

    def test_normal_init(self) -> None:
        mod = TaskPoolModule({})
        assert mod.pool is not None

    def test_empty_config(self) -> None:
        mod = TaskPoolModule({})
        assert mod.safe_gen is not None

    def test_generate_and_enqueue(self) -> None:
        mod = TaskPoolModule({})
        drive = {"gaps": {TaskType.SAFE: 0.5, TaskType.GAIN: 0.5, TaskType.EFF: 0.5}}
        count = mod.generate_and_enqueue(drive)
        assert count == 3

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            TaskPoolModule(None)

    def test_get_pool_snapshot(self) -> None:
        mod = TaskPoolModule({})
        snap = mod.get_pool_snapshot()
        assert "total" in snap
