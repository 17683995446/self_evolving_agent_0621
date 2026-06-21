"""复杂环境模拟与沙箱推演模块"""
from typing import Any, Dict, Final, List

import numpy as np

from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class EnvironmentSimulator:
    """环境模拟器（模拟状态转移、环境动态）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[EnvironmentSimulator.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.state_dim: int = int(config.get("state_dim", 5))
        self.noise_std: float = float(config.get("noise_std", 0.05))
        self.transition_matrix: np.ndarray = self._init_transition()
        logger.info(f"EnvironmentSimulator initialized state_dim={self.state_dim}", "simulate")

    def _init_transition(self) -> np.ndarray:
        m = np.eye(self.state_dim, dtype=np.float64) * 0.9
        noise = np.random.randn(self.state_dim, self.state_dim) * 0.05
        m = m + noise
        m = np.clip(m, 0.0, 1.0)
        row_sums = m.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        m = m / row_sums
        return m

    def step(self, state: List[float], action: List[float]) -> List[float]:
        logger.debug("[EnvironmentSimulator.step] start")
        s = np.array(state, dtype=np.float64)
        if len(s) < self.state_dim:
            s = np.pad(s, (0, self.state_dim - len(s)))
        else:
            s = s[:self.state_dim]
        a = np.array(action, dtype=np.float64)
        if len(a) < self.state_dim:
            a = np.pad(a, (0, self.state_dim - len(a)))
        else:
            a = a[:self.state_dim]
        noise = np.random.randn(self.state_dim) * self.noise_std
        next_s = np.dot(self.transition_matrix, s) + a * 0.1 + noise
        next_s = np.clip(next_s, 0.0, 1.0)
        result = [float(v) for v in next_s]
        logger.debug(f"[EnvironmentSimulator.step] next_state_norm={np.linalg.norm(next_s):.4f}")
        return result

    def reset(self) -> None:
        logger.debug("[EnvironmentSimulator.reset] start")
        self.transition_matrix = self._init_transition()

    def get_state(self) -> Dict[str, Any]:
        return {
            "state_dim": self.state_dim,
            "noise_std": self.noise_std,
        }


class SandboxEngine:
    """沙箱引擎（隔离推演、无副作用执行）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[SandboxEngine.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.max_steps: int = int(config.get("max_steps", 50))
        self.simulator = EnvironmentSimulator(config.get("simulator", {}))
        self.history: List[Dict[str, Any]] = []
        logger.info(f"SandboxEngine initialized max_steps={self.max_steps}", "simulate")

    def run_scenario(self, initial_state: List[float], actions: List[List[float]]) -> Dict[str, Any]:
        logger.debug("[SandboxEngine.run_scenario] start")
        Validator.require_type(initial_state, list, "initial_state")
        Validator.require_type(actions, list, "actions")
        state = list(initial_state)
        trajectory: List[List[float]] = [state]
        for i, action in enumerate(actions[:self.max_steps]):
            state = self.simulator.step(state, action)
            trajectory.append(state)
        result = {
            "trajectory": trajectory,
            "final_state": trajectory[-1],
            "steps": len(trajectory) - 1,
        }
        self.history.append(result)
        logger.debug(f"[SandboxEngine.run_scenario] steps={result['steps']}")
        return result

    def get_state(self) -> Dict[str, Any]:
        return {
            "max_steps": self.max_steps,
            "scenario_count": len(self.history),
        }


class CounterfactualPlanner:
    """反事实规划器（多分支假设推演）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[CounterfactualPlanner.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.branch_factor: int = int(config.get("branch_factor", 3))
        self.horizon: int = int(config.get("horizon", 5))
        self.sandbox = SandboxEngine(config.get("sandbox", {}))
        logger.info(f"CounterfactualPlanner initialized branches={self.branch_factor}", "simulate")

    def plan(self, initial_state: List[float], action_candidates: List[List[float]]) -> List[Dict[str, Any]]:
        logger.debug("[CounterfactualPlanner.plan] start")
        branches: List[Dict[str, Any]] = []
        for action in action_candidates[:self.branch_factor]:
            actions = [action for _ in range(self.horizon)]
            scenario = self.sandbox.run_scenario(initial_state, actions)
            branches.append({
                "action": action,
                "final_state": scenario["final_state"],
                "steps": scenario["steps"],
            })
        logger.debug(f"[CounterfactualPlanner.plan] branches={len(branches)}")
        return branches

    def get_state(self) -> Dict[str, Any]:
        return {
            "branch_factor": self.branch_factor,
            "horizon": self.horizon,
        }


class RiskAssessor:
    """风险评估器（概率化风险量化）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[RiskAssessor.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.risk_threshold: float = float(config.get("risk_threshold", 0.3))
        self.history: List[Dict[str, Any]] = []
        self.max_history: int = int(config.get("max_history", 100))
        logger.info(f"RiskAssessor initialized threshold={self.risk_threshold}", "simulate")

    def assess(self, trajectory: List[List[float]]) -> Dict[str, Any]:
        logger.debug("[RiskAssessor.assess] start")
        Validator.require_type(trajectory, list, "trajectory")
        if not trajectory:
            return {"risk_score": 0.0, "high_risk": False, "variance": 0.0}
        flat = []
        for step in trajectory:
            if isinstance(step, list):
                flat.extend(step)
            else:
                flat.append(float(step))
        states = np.array(flat, dtype=np.float64)
        variance = float(np.var(states))
        max_deviation = float(np.max(np.abs(states - np.mean(states))))
        risk_score = min(1.0, (variance + max_deviation) / 2.0)
        high_risk = risk_score > self.risk_threshold
        result = {
            "risk_score": risk_score,
            "high_risk": high_risk,
            "variance": variance,
            "max_deviation": max_deviation,
        }
        self._add_history(result)
        logger.debug(f"[RiskAssessor.assess] risk={risk_score:.4f} high={high_risk}")
        return result

    def _add_history(self, result: Dict[str, Any]) -> None:
        self.history.append(result)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        logger.debug(f"[RiskAssessor._add_history] size={len(self.history)}")

    def get_state(self) -> Dict[str, Any]:
        return {
            "risk_threshold": self.risk_threshold,
            "assessment_count": len(self.history),
        }


class SimulationModule:
    """复杂环境模拟与沙箱推演主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[SimulationModule.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.sandbox = SandboxEngine(config.get("sandbox", {}))
        logger.debug("[SimulationModule.__init__] sandbox created")
        self.planner = CounterfactualPlanner(config.get("planner", {}))
        logger.debug("[SimulationModule.__init__] planner created")
        self.risk = RiskAssessor(config.get("risk", {}))
        logger.debug("[SimulationModule.__init__] risk created")
        logger.info("SimulationModule initialized", "simulate")

    def simulate(self, initial_state: List[float], actions: List[List[float]]) -> Dict[str, Any]:
        logger.debug("[SimulationModule.simulate] start")
        scenario = self.sandbox.run_scenario(initial_state, actions)
        risk_result = self.risk.assess(scenario["trajectory"])
        return {
            "scenario": scenario,
            "risk": risk_result,
        }

    def plan_counterfactual(self, initial_state: List[float], action_candidates: List[List[float]]) -> Dict[str, Any]:
        logger.debug("[SimulationModule.plan_counterfactual] start")
        branches = self.planner.plan(initial_state, action_candidates)
        best = None
        best_score = float("inf")
        for branch in branches:
            traj = [initial_state, branch["final_state"]]
            risk = self.risk.assess(traj)
            if risk["risk_score"] < best_score:
                best_score = risk["risk_score"]
                best = branch
        return {
            "branches": branches,
            "best_branch": best,
            "best_risk_score": best_score,
        }

    def get_state(self) -> Dict[str, Any]:
        return {
            "sandbox": self.sandbox.get_state(),
            "planner": self.planner.get_state(),
            "risk": self.risk.get_state(),
        }
