"""自主目标生成与动机涌现模块"""
from typing import Any, Dict, Final, List, Optional

import numpy as np

from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class IntrinsicReward:
    """内在奖励计算器（新奇性、学习进度、自主性）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[IntrinsicReward.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.novelty_weight: float = float(config.get("novelty_weight", 0.4))
        self.progress_weight: float = float(config.get("progress_weight", 0.4))
        self.autonomy_weight: float = float(config.get("autonomy_weight", 0.2))
        self.seen_states: List[List[float]] = []
        self.max_seen: int = int(config.get("max_seen", 500))
        self.prev_performance: float = 0.0
        logger.info("IntrinsicReward initialized", "autonomous")

    def compute(self, state: List[float], performance: float, is_self_chosen: bool) -> float:
        logger.debug("[IntrinsicReward.compute] start")
        novelty = self._novelty(state)
        progress = self._progress(performance)
        autonomy = 1.0 if is_self_chosen else 0.0
        reward = (self.novelty_weight * novelty +
                  self.progress_weight * progress +
                  self.autonomy_weight * autonomy)
        self._record_state(state)
        self.prev_performance = performance
        logger.debug(f"[IntrinsicReward.compute] reward={reward:.4f}")
        return float(reward)

    def _novelty(self, state: List[float]) -> float:
        if not self.seen_states:
            return 1.0
        s = np.array(state, dtype=np.float64)
        min_dist = float("inf")
        for seen in self.seen_states:
            seen_arr = np.array(seen, dtype=np.float64)
            min_len = min(len(s), len(seen_arr))
            if min_len == 0:
                continue
            dist = float(np.linalg.norm(s[:min_len] - seen_arr[:min_len]))
            min_dist = min(min_dist, dist)
        novelty = float(np.tanh(min_dist))
        logger.debug(f"[IntrinsicReward._novelty] novelty={novelty:.4f}")
        return novelty

    def _progress(self, performance: float) -> float:
        progress = max(0.0, performance - self.prev_performance)
        logger.debug(f"[IntrinsicReward._progress] progress={progress:.4f}")
        return progress

    def _record_state(self, state: List[float]) -> None:
        self.seen_states.append(list(state))
        if len(self.seen_states) > self.max_seen:
            self.seen_states.pop(0)
        logger.debug(f"[IntrinsicReward._record_state] seen={len(self.seen_states)}")

    def get_state(self) -> Dict[str, Any]:
        return {
            "seen_count": len(self.seen_states),
            "weights": {
                "novelty": self.novelty_weight,
                "progress": self.progress_weight,
                "autonomy": self.autonomy_weight,
            },
        }


class CuriosityDrive:
    """好奇心驱动器（预测误差作为探索信号）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[CuriosityDrive.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.error_history: List[float] = []
        self.max_history: int = int(config.get("max_history", 100))
        self.threshold: float = float(config.get("threshold", 0.1))
        logger.info(f"CuriosityDrive initialized threshold={self.threshold}", "autonomous")

    def update(self, predicted: float, actual: float) -> float:
        logger.debug("[CuriosityDrive.update] start")
        error = abs(predicted - actual)
        self.error_history.append(error)
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)
        curiosity = float(np.tanh(error))
        logger.debug(f"[CuriosityDrive.update] error={error:.4f} curiosity={curiosity:.4f}")
        return curiosity

    def is_curious(self) -> bool:
        if not self.error_history:
            return False
        recent = float(np.mean(self.error_history[-10:]))
        curious = recent > self.threshold
        logger.debug(f"[CuriosityDrive.is_curious] recent={recent:.4f} curious={curious}")
        return curious

    def get_state(self) -> Dict[str, Any]:
        return {
            "history_size": len(self.error_history),
            "threshold": self.threshold,
            "is_curious": self.is_curious(),
        }


class GoalGenerator:
    """目标生成器（从状态空间采样可行目标）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[GoalGenerator.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.goal_pool: List[Dict[str, Any]] = []
        self.max_goals: int = int(config.get("max_goals", 50))
        self.state_dim: int = int(config.get("state_dim", 5))
        logger.info(f"GoalGenerator initialized max_goals={self.max_goals}", "autonomous")

    def generate(self, current_state: List[float]) -> Dict[str, Any]:
        logger.debug("[GoalGenerator.generate] start")
        target = [float(np.clip(v + np.random.randn() * 0.1, 0.0, 1.0)) for v in current_state]
        if len(target) < self.state_dim:
            target = target + [0.5] * (self.state_dim - len(target))
        else:
            target = target[:self.state_dim]
        goal = {
            "id": f"goal_{len(self.goal_pool)}",
            "target": target,
            "priority": float(np.random.rand()),
            "created": len(self.goal_pool),
        }
        self.goal_pool.append(goal)
        if len(self.goal_pool) > self.max_goals:
            self.goal_pool.pop(0)
        logger.debug(f"[GoalGenerator.generate] id={goal['id']}")
        return goal

    def select_best(self) -> Optional[Dict[str, Any]]:
        if not self.goal_pool:
            return None
        best = max(self.goal_pool, key=lambda g: g["priority"])
        logger.debug(f"[GoalGenerator.select_best] id={best['id']}")
        return best

    def get_state(self) -> Dict[str, Any]:
        return {
            "goal_count": len(self.goal_pool),
            "max_goals": self.max_goals,
            "state_dim": self.state_dim,
        }


class MotivationEmergence:
    """动机涌现引擎（动态优先级调整）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[MotivationEmergence.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.drives: Dict[str, float] = dict(config.get("drives", {
            "survival": 0.5,
            "exploration": 0.3,
            "mastery": 0.2,
        }))
        self.adaptation_rate: float = float(config.get("adaptation_rate", 0.1))
        logger.info(f"MotivationEmergence initialized drives={list(self.drives.keys())}", "autonomous")

    def update(self, feedback: Dict[str, float]) -> None:
        logger.debug("[MotivationEmergence.update] start")
        Validator.require_type(feedback, dict, "feedback")
        for drive_name, signal in feedback.items():
            if drive_name in self.drives:
                old = self.drives[drive_name]
                self.drives[drive_name] = float(np.clip(
                    old + self.adaptation_rate * (signal - old),
                    0.0, 1.0
                ))
                logger.debug(f"[MotivationEmergence.update] {drive_name}={self.drives[drive_name]:.4f}")

    def get_dominant(self) -> str:
        dominant = max(self.drives, key=lambda k: self.drives[k])
        logger.debug(f"[MotivationEmergence.get_dominant] {dominant}")
        return dominant

    def get_state(self) -> Dict[str, Any]:
        return {
            "drives": self.drives.copy(),
            "dominant": self.get_dominant(),
        }


class AutonomousGoalModule:
    """自主目标生成与动机涌现主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[AutonomousGoalModule.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.intrinsic = IntrinsicReward(config.get("intrinsic", {}))
        logger.debug("[AutonomousGoalModule.__init__] intrinsic created")
        self.curiosity = CuriosityDrive(config.get("curiosity", {}))
        logger.debug("[AutonomousGoalModule.__init__] curiosity created")
        self.generator = GoalGenerator(config.get("generator", {}))
        logger.debug("[AutonomousGoalModule.__init__] generator created")
        self.motivation = MotivationEmergence(config.get("motivation", {}))
        logger.debug("[AutonomousGoalModule.__init__] motivation created")
        logger.info("AutonomousGoalModule initialized", "autonomous")

    def generate_goal(self, current_state: List[float], performance: float) -> Dict[str, Any]:
        logger.debug("[AutonomousGoalModule.generate_goal] start")
        goal = self.generator.generate(current_state)
        reward = self.intrinsic.compute(current_state, performance, is_self_chosen=True)
        goal["intrinsic_reward"] = reward
        logger.info(f"[AutonomousGoalModule.generate_goal] id={goal['id']} reward={reward:.4f}", "autonomous")
        return goal

    def evaluate_action(self, predicted: float, actual: float, performance: float, state: List[float], is_self_chosen: bool) -> Dict[str, Any]:
        logger.debug("[AutonomousGoalModule.evaluate_action] start")
        curiosity = self.curiosity.update(predicted, actual)
        intrinsic = self.intrinsic.compute(state, performance, is_self_chosen)
        return {
            "curiosity": curiosity,
            "intrinsic_reward": intrinsic,
            "is_curious": self.curiosity.is_curious(),
        }

    def update_motivation(self, feedback: Dict[str, float]) -> None:
        logger.debug("[AutonomousGoalModule.update_motivation] start")
        self.motivation.update(feedback)

    def get_dominant_motivation(self) -> str:
        return self.motivation.get_dominant()

    def get_state(self) -> Dict[str, Any]:
        return {
            "intrinsic": self.intrinsic.get_state(),
            "curiosity": self.curiosity.get_state(),
            "generator": self.generator.get_state(),
            "motivation": self.motivation.get_state(),
        }
