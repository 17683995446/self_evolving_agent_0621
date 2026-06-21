"""任务池模块补充测试"""
from root.left.app.left.src.core_mod.task import TaskPoolModule, Task, TaskPool, TaskStatus, TaskType


class TestTaskPoolModuleExtra:
    """测试TaskPoolModule额外路径"""

    def test_get_next_task_empty(self) -> None:
        mod = TaskPoolModule({})
        assert mod.get_next_task() is None

    def test_update_task_status(self) -> None:
        mod = TaskPoolModule({})
        task = Task(TaskType.SAFE, 0.5, {})
        mod.pool.add(task)
        result = mod.update_task_status(task.task_id, TaskStatus.COMPLETED)
        assert result is True

    def test_update_task_status_not_found(self) -> None:
        mod = TaskPoolModule({})
        result = mod.update_task_status("invalid", TaskStatus.COMPLETED)
        assert result is False


class TestTaskPoolExtra:
    """测试TaskPool额外路径"""

    def test_update_status_not_found(self) -> None:
        pool = TaskPool({})
        assert pool.update_status("invalid", TaskStatus.COMPLETED) is False
