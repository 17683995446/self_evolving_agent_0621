"""决策模块"""
import random
from typing import Any, Dict, Final, List, Optional

from root.left.app.left.src.utils_main.constants import DriveType, TaskStatus
from root.left.app.left.src.utils_main.exceptions import DecisionException
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class ExplorationController:
    """探索控制器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[ExplorationController.__init__] start")
        Validator.require_type(config, dict, "config")
        logger.debug("[ExplorationController.__init__] config validated")
        self.config: Final[Dict[str, Any]] = config
        logger.debug("[ExplorationController.__init__] config assigned")
        self.base_ratio: float = float(config.get("base_exploration_ratio", 0.3))
        logger.debug(f"[ExplorationController.__init__] base_ratio={self.base_ratio}")
        self.min_ratio: float = float(config.get("min_exploration_ratio", 0.1))
        logger.debug(f"[ExplorationController.__init__] min_ratio={self.min_ratio}")
        self.max_ratio: float = float(config.get("max_exploration_ratio", 0.5))
        logger.debug(f"[ExplorationController.__init__] max_ratio={self.max_ratio}")
        self.exploration_count: int = 0
        logger.debug("[ExplorationController.__init__] exploration_count initialized")
        self.exploitation_count: int = 0
        logger.debug("[ExplorationController.__init__] exploitation_count initialized")

    def should_explore(self, drive_state: Dict[str, Any]) -> bool:
        logger.debug("[ExplorationController.should_explore] start")
        scenario = drive_state.get("scenario", "normal")
        logger.debug(f"[ExplorationController.should_explore] scenario={scenario}")
        if scenario == "emergency":
            logger.debug("[ExplorationController.should_explore] emergency -> False")
            return False
        current_ratio = self._get_current_ratio()
        logger.debug(f"[ExplorationController.should_explore] current_ratio={current_ratio}")
        result = random.random() < current_ratio
        logger.debug(f"[ExplorationController.should_explore] result={result}")
        return result

    def _get_current_ratio(self) -> float:
        logger.debug("[ExplorationController._get_current_ratio] start")
        total = self.exploration_count + self.exploitation_count
        logger.debug(f"[ExplorationController._get_current_ratio] total={total}")
        if total == 0:
            logger.debug("[ExplorationController._get_current_ratio] total=0 -> base_ratio")
            return self.base_ratio
        actual = self.exploration_count / total
        logger.debug(f"[ExplorationController._get_current_ratio] actual={actual}")
        if actual < self.min_ratio:
            result = self.base_ratio + 0.1
            logger.debug(f"[ExplorationController._get_current_ratio] actual<min -> {result}")
            return result
        if actual > self.max_ratio:
            result = self.base_ratio - 0.1
            logger.debug(f"[ExplorationController._get_current_ratio] actual>max -> {result}")
            return result
        logger.debug("[ExplorationController._get_current_ratio] -> base_ratio")
        return self.base_ratio

    def record_choice(self, is_exploration: bool) -> None:
        logger.debug(f"[ExplorationController.record_choice] is_exploration={is_exploration}")
        if is_exploration:
            self.exploration_count += 1
            logger.debug(f"[ExplorationController.record_choice] exploration_count={self.exploration_count}")
        else:
            self.exploitation_count += 1
            logger.debug(f"[ExplorationController.record_choice] exploitation_count={self.exploitation_count}")


class TaskSelector:
    """任务选择器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[TaskSelector.__init__] start")
        Validator.require_type(config, dict, "config")
        logger.debug("[TaskSelector.__init__] config validated")
        self.config: Final[Dict[str, Any]] = config
        logger.debug("[TaskSelector.__init__] done")

    def select(self, tasks: List[Any], drive_state: Dict[str, Any]) -> Optional[Any]:
        logger.debug("[TaskSelector.select] start")
        if not tasks:
            logger.debug("[TaskSelector.select] empty tasks -> None")
            return None
        logger.debug(f"[TaskSelector.select] tasks count={len(tasks)}")
        gaps = drive_state.get("gaps", {})
        logger.debug(f"[TaskSelector.select] gaps={gaps}")
        priority_order = sorted(
            tasks,
            key=lambda t: self._task_priority(t, gaps),
            reverse=True
        )
        logger.debug("[TaskSelector.select] sorted done")
        selected = priority_order[0]
        logger.debug(f"[TaskSelector.select] selected={selected}")
        return selected

    def _task_priority(self, task: Any, gaps: Dict[Any, float]) -> float:
        logger.debug("[TaskSelector._task_priority] start")
        task_type = getattr(task, "task_type", None)
        logger.debug(f"[TaskSelector._task_priority] task_type={task_type}")
        base_priority = getattr(task, "priority", 0.5)
        logger.debug(f"[TaskSelector._task_priority] base_priority={base_priority}")
        gap = gaps.get(task_type, 0.5)
        logger.debug(f"[TaskSelector._task_priority] gap={gap}")
        result = base_priority * (1 + gap)
        logger.debug(f"[TaskSelector._task_priority] result={result}")
        return result


class ResourceBalancer:
    """资源平衡器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[ResourceBalancer.__init__] start")
        Validator.require_type(config, dict, "config")
        logger.debug("[ResourceBalancer.__init__] config validated")
        self.config: Final[Dict[str, Any]] = config
        logger.debug("[ResourceBalancer.__init__] config assigned")
        self.cpu_limit: float = float(config.get("cpu_limit", 20.0))
        logger.debug(f"[ResourceBalancer.__init__] cpu_limit={self.cpu_limit}")
        self.memory_limit: float = float(config.get("memory_limit", 20.0))
        logger.debug(f"[ResourceBalancer.__init__] memory_limit={self.memory_limit}")

    def check_limits(self, agent_cpu: float, agent_memory: float) -> bool:
        logger.debug("[ResourceBalancer.check_limits] start")
        cpu_ok = agent_cpu <= self.cpu_limit
        logger.debug(f"[ResourceBalancer.check_limits] cpu_ok={cpu_ok}")
        mem_ok = agent_memory <= self.memory_limit
        logger.debug(f"[ResourceBalancer.check_limits] mem_ok={mem_ok}")
        result = cpu_ok and mem_ok
        logger.debug(f"[ResourceBalancer.check_limits] result={result}")
        return result

    def get_available_capacity(self, agent_cpu: float, agent_memory: float) -> Dict[str, float]:
        logger.debug("[ResourceBalancer.get_available_capacity] start")
        cpu_cap = max(0.0, self.cpu_limit - agent_cpu)
        logger.debug(f"[ResourceBalancer.get_available_capacity] cpu_cap={cpu_cap}")
        mem_cap = max(0.0, self.memory_limit - agent_memory)
        logger.debug(f"[ResourceBalancer.get_available_capacity] mem_cap={mem_cap}")
        result = {"cpu": cpu_cap, "memory": mem_cap}
        logger.debug(f"[ResourceBalancer.get_available_capacity] result={result}")
        return result


class DecisionModule:
    """决策模块主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[DecisionModule.__init__] start")
        Validator.require_type(config, dict, "config")
        logger.debug("[DecisionModule.__init__] config validated")
        self.config: Final[Dict[str, Any]] = config
        logger.debug("[DecisionModule.__init__] config assigned")
        self.exploration = ExplorationController(config.get("exploration", {}))
        logger.debug("[DecisionModule.__init__] exploration created")
        self.task_selector = TaskSelector(config.get("task_selector", {}))
        logger.debug("[DecisionModule.__init__] task_selector created")
        self.resource_balancer = ResourceBalancer(config.get("resource_balancer", {}))
        logger.debug("[DecisionModule.__init__] resource_balancer created")
        self.decision_history: List[Dict[str, Any]] = []
        self.max_history: int = int(config.get("max_history", 100))
        logger.debug(f"[DecisionModule.__init__] decision_history initialized max_history={self.max_history}")

    def decide(
        self,
        task_pool: Any,
        drive_state: Dict[str, Any],
        performance_history: List[float],
        loop_count: int,
        agent_cpu: float,
        agent_memory: float
    ) -> Dict[str, Any]:
        logger.debug("[DecisionModule.decide] start")
        Validator.require_type(drive_state, dict, "drive_state")
        logger.debug("[DecisionModule.decide] drive_state validated")
        Validator.require_type(performance_history, list, "performance_history")
        logger.debug("[DecisionModule.decide] performance_history validated")
        Validator.require_type(loop_count, int, "loop_count")
        logger.debug("[DecisionModule.decide] loop_count validated")
        self._check_resources(agent_cpu, agent_memory)
        logger.debug("[DecisionModule.decide] resources checked")
        is_explore = self.exploration.should_explore(drive_state)
        logger.debug(f"[DecisionModule.decide] is_explore={is_explore}")
        self.exploration.record_choice(is_explore)
        logger.debug("[DecisionModule.decide] choice recorded")
        selected_task = self._select_task(task_pool, drive_state, is_explore)
        logger.debug(f"[DecisionModule.decide] selected_task={selected_task}")
        result = self._build_decision(loop_count, is_explore, selected_task, agent_cpu, agent_memory)
        logger.debug("[DecisionModule.decide] done")
        return result

    def _check_resources(self, agent_cpu: float, agent_memory: float) -> None:
        logger.debug("[DecisionModule._check_resources] start")
        if not self.resource_balancer.check_limits(agent_cpu, agent_memory):
            logger.error("[DecisionModule._check_resources] limits exceeded")
            raise DecisionException("Resource limits exceeded", task_count=0)
        logger.debug("[DecisionModule._check_resources] ok")

    def _select_task(
        self, task_pool: Any, drive_state: Dict[str, Any], is_explore: bool
    ) -> Optional[Any]:
        logger.debug("[DecisionModule._select_task] start")
        pending_tasks = task_pool.get_by_status(TaskStatus.PENDING)
        logger.debug(f"[DecisionModule._select_task] pending_tasks count={len(pending_tasks)}")
        if not pending_tasks:
            logger.debug("[DecisionModule._select_task] no pending tasks -> None")
            return None
        if is_explore:
            selected = random.choice(pending_tasks)
            logger.debug(f"[DecisionModule._select_task] explore selected={selected}")
            return selected
        selected = self.task_selector.select(pending_tasks, drive_state)
        logger.debug(f"[DecisionModule._select_task] exploit selected={selected}")
        return selected

    def _build_decision(
        self, loop_count: int, is_explore: bool,
        selected_task: Optional[Any], agent_cpu: float, agent_memory: float
    ) -> Dict[str, Any]:
        logger.debug("[DecisionModule._build_decision] start")
        decision = {
            "loop": loop_count,
            "is_exploration": is_explore,
            "selected_task": selected_task.to_dict() if selected_task else None,
            "resource_capacity": self.resource_balancer.get_available_capacity(agent_cpu, agent_memory),
        }
        logger.debug(f"[DecisionModule._build_decision] decision built={decision}")
        self.decision_history.append(decision)
        if len(self.decision_history) > self.max_history:
            removed = self.decision_history.pop(0)
            logger.debug(f"[DecisionModule._build_decision] trimmed oldest decision loop={removed.get('loop')}")
        logger.debug(f"[DecisionModule._build_decision] history len={len(self.decision_history)}")
        return decision

    def should_pause(self, drive_state: Dict[str, Any]) -> bool:
        logger.debug("[DecisionModule.should_pause] start")
        gaps = drive_state.get("gaps", {})
        logger.debug(f"[DecisionModule.should_pause] gaps={gaps}")
        safe_gap = gaps.get(DriveType.SAFE, 0)
        logger.debug(f"[DecisionModule.should_pause] safe_gap={safe_gap}")
        result = safe_gap > 0.7
        logger.debug(f"[DecisionModule.should_pause] result={result}")
        return result

    def get_state(self) -> Dict[str, Any]:
        """获取决策模块状态"""
        return {
            "decision_history_len": len(self.decision_history),
            "max_history": self.max_history,
            "has_exploration": hasattr(self.exploration, "should_explore"),
            "has_task_selector": hasattr(self.task_selector, "select"),
            "has_resource_balancer": hasattr(self.resource_balancer, "check_limits"),
        }

    def reset(self) -> None:
        """重置决策模块"""
        logger.debug("[DecisionModule.reset] called", "decision")
        self.decision_history.clear()

    def health_check(self) -> bool:
        """健康检查"""
        logger.debug("[DecisionModule.health_check] called", "decision")
        return True
