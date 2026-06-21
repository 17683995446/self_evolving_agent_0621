"""任务池模块"""
import time
import uuid
from typing import Any, Dict, Final, List, Optional

from root.left.app.left.src.core_mod.task_templates import TaskTemplateRegistry
from root.left.app.left.src.utils_main.constants import TaskStatus, TaskType
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class Task:
    """任务实体"""

    def __init__(
        self, task_type: TaskType, priority: float, payload: Dict[str, Any]
    ) -> None:
        Validator.require_type(task_type, TaskType, "task_type")
        Validator.require_type(priority, (int, float), "priority")
        Validator.require_type(payload, dict, "payload")
        self._init_fields(task_type, priority, payload)

    def _init_fields(
        self, task_type: TaskType, priority: float, payload: Dict[str, Any]
    ) -> None:
        self.task_id: str = str(uuid.uuid4())
        self.task_type: TaskType = task_type
        self.priority: float = float(priority)
        self.status: TaskStatus = TaskStatus.PENDING
        self.payload: Dict[str, Any] = payload
        self.created_at: float = time.time()
        self.retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return self._build_dict()

    def _build_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "priority": self.priority,
            "status": self.status.value,
            "payload": self.payload,
            "created_at": self.created_at,
            "retry_count": self.retry_count,
        }


class TaskPool:
    """任务池"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.max_size: int = int(config.get("max_size", 100))
        self.task_timeout: float = float(config.get("task_timeout", 300.0))
        self.tasks: Dict[str, Task] = {}
        self.pending_queue: List[str] = []
        logger.info(f"TaskPool initialized max_size={self.max_size} timeout={self.task_timeout}", "task_pool")

    def add(self, task: Task) -> bool:
        if len(self.tasks) >= self.max_size:
            logger.warning(f"TaskPool full, attempting cleanup for {task.task_id}", "task_pool")
            cleared = self.clear_completed()
            logger.debug(f"TaskPool cleanup cleared={cleared}", "task_pool")
            stale = self.clear_stale()
            logger.debug(f"TaskPool stale cleared={stale}", "task_pool")
        if len(self.tasks) >= self.max_size:
            logger.warning(f"TaskPool still full after cleanup, evicting lowest priority for {task.task_id}", "task_pool")
            self._evict_lowest_priority()
        self.tasks[task.task_id] = task
        self.pending_queue.append(task.task_id)
        self._sort_pending()
        logger.debug(f"Task added: {task.task_id} type={task.task_type.value}", "task_pool")
        return True

    def _evict_lowest_priority(self) -> None:
        if not self.tasks:
            return
        lowest_task = min(self.tasks.values(), key=lambda t: t.priority)
        self.tasks.pop(lowest_task.task_id, None)
        if lowest_task.task_id in self.pending_queue:
            self.pending_queue.remove(lowest_task.task_id)
        logger.info(f"Evicted lowest priority task: {lowest_task.task_id} priority={lowest_task.priority}", "task_pool")

    def _sort_pending(self) -> None:
        self.pending_queue.sort(
            key=lambda tid: self.tasks[tid].priority,
            reverse=True
        )

    def get_next(self) -> Optional[Task]:
        logger.debug(f"get_next called, queue_size={len(self.pending_queue)}", "task_pool")
        while self.pending_queue:
            tid = self.pending_queue.pop(0)
            task = self.tasks.get(tid)
            if task is None:
                logger.warning(f"Task {tid} not found in tasks dict, skipping", "task_pool")
                continue
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.RUNNING
                logger.info(f"Task {tid} started running", "task_pool")
                return task
            logger.debug(f"Task {tid} status={task.status.value}, requeueing", "task_pool")
            self.pending_queue.append(tid)
        logger.info("No pending tasks available", "task_pool")
        return None

    def update_status(self, task_id: str, status: TaskStatus) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"update_status: task {task_id} not found", "task_pool")
            return False
        old_status = task.status
        task.status = status
        logger.info(f"Task {task_id} status: {old_status.value} -> {status.value}", "task_pool")
        self._handle_retry(task)
        return True

    def _handle_retry(self, task: Task) -> None:
        if task.status == TaskStatus.FAILED and task.retry_count < 3:
            task.retry_count += 1
            task.status = TaskStatus.PENDING
            self.pending_queue.append(task.task_id)
            self._sort_pending()
            logger.info(f"Task {task.task_id} retry #{task.retry_count}", "task_pool")

    def get_by_status(self, status: TaskStatus) -> List[Task]:
        return [t for t in self.tasks.values() if t.status == status]

    def get_by_type(self, task_type: TaskType) -> List[Task]:
        return [t for t in self.tasks.values() if t.task_type == task_type]

    def get_frozen_count(self) -> int:
        return len(self.get_by_status(TaskStatus.FROZEN))

    def clear_completed(self) -> int:
        completed = self.get_by_status(TaskStatus.COMPLETED)
        for task in completed:
            self.tasks.pop(task.task_id, None)
            if task.task_id in self.pending_queue:
                self.pending_queue.remove(task.task_id)
        logger.info(f"Cleared {len(completed)} completed tasks", "task_pool")
        return len(completed)

    def clear_stale(self) -> int:
        now = time.time()
        stale_ids = [
            tid for tid, task in self.tasks.items()
            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
            and (now - task.created_at) > self.task_timeout
        ]
        for tid in stale_ids:
            task = self.tasks.pop(tid, None)
            if task and task.task_id in self.pending_queue:
                self.pending_queue.remove(task.task_id)
        logger.info(f"Cleared {len(stale_ids)} stale tasks", "task_pool")
        return len(stale_ids)


class SafeTaskGenerator:
    """安全任务生成器"""

    def __init__(self, config: Dict[str, Any], registry: TaskTemplateRegistry) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.registry: Final[TaskTemplateRegistry] = registry

    def generate(self, drive_state: Dict[str, Any]) -> List[Task]:
        gaps = drive_state.get("gaps", {})
        safe_gap = gaps.get(TaskType.SAFE, 0.5)
        logger.debug(f"SafeTaskGenerator gap={safe_gap}", "task_gen")
        if safe_gap <= 0.3:
            return []
        return [self._create_task(safe_gap)]

    def _create_task(self, gap: float) -> Task:
        payload = self.registry.build_payload("health_check", {})
        return Task(TaskType.SAFE, priority=gap, payload=payload)


class GainTaskGenerator:
    """收益任务生成器"""

    def __init__(self, config: Dict[str, Any], registry: TaskTemplateRegistry) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.registry: Final[TaskTemplateRegistry] = registry

    def generate(self, drive_state: Dict[str, Any]) -> List[Task]:
        gaps = drive_state.get("gaps", {})
        gain_gap = gaps.get(TaskType.GAIN, 0.5)
        logger.debug(f"GainTaskGenerator gap={gain_gap}", "task_gen")
        if gain_gap <= 0.2:
            return []
        return [self._create_task(gain_gap)]

    def _create_task(self, gap: float) -> Task:
        payload = self.registry.build_payload("log_scan", {})
        return Task(TaskType.GAIN, priority=gap, payload=payload)


class EffTaskGenerator:
    """能效任务生成器"""

    def __init__(self, config: Dict[str, Any], registry: TaskTemplateRegistry) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.registry: Final[TaskTemplateRegistry] = registry

    def generate(self, drive_state: Dict[str, Any]) -> List[Task]:
        gaps = drive_state.get("gaps", {})
        eff_gap = gaps.get(TaskType.EFF, 0.5)
        logger.debug(f"EffTaskGenerator gap={eff_gap}", "task_gen")
        if eff_gap <= 0.2:
            return []
        return [self._create_task(eff_gap)]

    def _create_task(self, gap: float) -> Task:
        payload = self.registry.build_payload("disk_cleanup", {})
        return Task(TaskType.EFF, priority=gap, payload=payload)


class TaskPoolModule:
    """任务池模块主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.pool = TaskPool(config.get("pool", {}))
        self.registry = TaskTemplateRegistry(config.get("task_templates", {}))
        self.safe_gen = SafeTaskGenerator(config.get("safe_gen", {}), self.registry)
        self.gain_gen = GainTaskGenerator(config.get("gain_gen", {}), self.registry)
        self.eff_gen = EffTaskGenerator(config.get("eff_gen", {}), self.registry)
        logger.info("TaskPoolModule initialized", "task_pool")

    def generate_and_enqueue(self, drive_state: Dict[str, Any]) -> int:
        Validator.require_type(drive_state, dict, "drive_state")
        all_tasks: List[Task] = []
        all_tasks.extend(self.safe_gen.generate(drive_state))
        all_tasks.extend(self.gain_gen.generate(drive_state))
        all_tasks.extend(self.eff_gen.generate(drive_state))
        logger.info(f"Generated {len(all_tasks)} tasks", "task_pool")
        for task in all_tasks:
            self.pool.add(task)
        return len(all_tasks)

    def get_next_task(self) -> Optional[Task]:
        return self.pool.get_next()

    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        return self.pool.update_status(task_id, status)

    def get_pool_snapshot(self) -> Dict[str, Any]:
        snapshot = {
            "total": len(self.pool.tasks),
            "pending": len(self.pool.get_by_status(TaskStatus.PENDING)),
            "running": len(self.pool.get_by_status(TaskStatus.RUNNING)),
            "completed": len(self.pool.get_by_status(TaskStatus.COMPLETED)),
            "failed": len(self.pool.get_by_status(TaskStatus.FAILED)),
            "frozen": self.pool.get_frozen_count(),
        }
        logger.debug(f"Pool snapshot: {snapshot}", "task_pool")
        return snapshot

    def get_state(self) -> Dict[str, Any]:
        """获取任务池模块状态"""
        return {
            "pool_snapshot": self.get_pool_snapshot(),
            "has_registry": hasattr(self.registry, "build_payload"),
        }

    def reset(self) -> None:
        """重置任务池模块"""
        logger.debug("[TaskPoolModule.reset] called", "task_pool")
        self.pool.tasks.clear()
        self.registry = TaskTemplateRegistry(self.config.get("task_templates", {}))
        self.safe_gen = SafeTaskGenerator(self.config.get("safe_gen", {}), self.registry)
        self.gain_gen = GainTaskGenerator(self.config.get("gain_gen", {}), self.registry)
        self.eff_gen = EffTaskGenerator(self.config.get("eff_gen", {}), self.registry)

    def health_check(self) -> bool:
        """健康检查"""
        logger.debug("[TaskPoolModule.health_check] called", "task_pool")
        return True
