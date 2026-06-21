"""Phase 2 核心"""
from typing import Any, Dict, Final

from root.left.app.left.src.core_mod.task import TaskPoolModule
from root.left.app.left.src.core_mod.decide import DecisionModule
from root.left.app.left.src.core_mod.memory import MemoryModule
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class PhaseTwoCore:
    """Phase 2 整合核心"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[PhaseTwoCore.__init__] start")
        Validator.require_type(config, dict, "config")
        logger.debug("[PhaseTwoCore.__init__] config validated")
        self.config: Final[Dict[str, Any]] = config
        logger.debug("[PhaseTwoCore.__init__] config assigned")
        self.task_pool = TaskPoolModule(config.get("task_pool", {}))
        logger.debug("[PhaseTwoCore.__init__] task_pool created")
        self.decision = DecisionModule(config.get("decision", {}))
        logger.debug("[PhaseTwoCore.__init__] decision created")
        self.memory = MemoryModule(config.get("memory", {}))
        logger.debug("[PhaseTwoCore.__init__] memory created")

    def step(
        self,
        phase1_result: Dict[str, Any],
        loop_count: int,
        agent_cpu: float,
        agent_memory: float
    ) -> Dict[str, Any]:
        logger.debug("[PhaseTwoCore.step] start")
        Validator.require_type(phase1_result, dict, "phase1_result")
        logger.debug("[PhaseTwoCore.step] phase1_result validated")
        Validator.require_type(loop_count, int, "loop_count")
        logger.debug("[PhaseTwoCore.step] loop_count validated")
        drive_state = phase1_result.get("drive_state", {})
        logger.debug(f"[PhaseTwoCore.step] drive_state keys={list(drive_state.keys())}")
        self.task_pool.generate_and_enqueue(drive_state)
        logger.debug("[PhaseTwoCore.step] tasks generated and enqueued")
        decision = self._make_decision(drive_state, loop_count, agent_cpu, agent_memory)
        logger.debug(f"[PhaseTwoCore.step] decision keys={list(decision.keys())}")
        self._record_memory(phase1_result, loop_count, drive_state)
        logger.debug("[PhaseTwoCore.step] memory recorded")
        result = self._build_result(decision)
        logger.debug("[PhaseTwoCore.step] done")
        return result

    def _make_decision(
        self,
        drive_state: Dict[str, Any],
        loop_count: int,
        agent_cpu: float,
        agent_memory: float
    ) -> Dict[str, Any]:
        logger.debug("[PhaseTwoCore._make_decision] start")
        result = self.decision.decide(
            self.task_pool.pool,
            drive_state,
            [],
            loop_count,
            agent_cpu,
            agent_memory
        )
        logger.debug("[PhaseTwoCore._make_decision] done")
        return result

    def _record_memory(
        self,
        phase1_result: Dict[str, Any],
        loop_count: int,
        drive_state: Dict[str, Any]
    ) -> None:
        logger.debug("[PhaseTwoCore._record_memory] start")
        performance = phase1_result.get("performance", 0.0)
        logger.debug(f"[PhaseTwoCore._record_memory] performance={performance}")
        state = phase1_result.get("state", {})
        logger.debug(f"[PhaseTwoCore._record_memory] state keys={list(state.keys())}")
        self.memory.record_state(loop_count, state, drive_state, performance)
        logger.debug("[PhaseTwoCore._record_memory] done")

    def _build_result(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[PhaseTwoCore._build_result] start")
        result = {
            "decision": decision,
            "task_pool_snapshot": self.task_pool.get_pool_snapshot(),
            "memory_recent": self.memory.get_recent_states(10),
        }
        logger.debug(f"[PhaseTwoCore._build_result] result keys={list(result.keys())}")
        return result

    def should_pause(self, phase1_result: Dict[str, Any]) -> bool:
        logger.debug("[PhaseTwoCore.should_pause] start")
        drive_state = phase1_result.get("drive_state", {})
        logger.debug(f"[PhaseTwoCore.should_pause] drive_state keys={list(drive_state.keys())}")
        result = self.decision.should_pause(drive_state)
        logger.debug(f"[PhaseTwoCore.should_pause] result={result}")
        return result

    def get_state(self) -> Dict[str, Any]:
        """获取 Phase 2 状态"""
        return {
            "task_count": self.task_pool.get_pool_snapshot().get("total", 0),
            "has_decision": hasattr(self.decision, "decide"),
            "has_memory": hasattr(self.memory, "record_state"),
        }

    def reset(self) -> None:
        """重置 Phase 2"""
        logger.debug("[PhaseTwoCore.reset] called", "phase2")
        for module in [self.task_pool, self.decision, self.memory]:
            if hasattr(module, "reset") and callable(getattr(module, "reset")):
                module.reset()

    def health_check(self) -> bool:
        """健康检查"""
        logger.debug("[PhaseTwoCore.health_check] called", "phase2")
        return all(
            module.health_check()
            for module in [self.task_pool, self.decision, self.memory]
        )
