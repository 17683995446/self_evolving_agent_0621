"""复杂环境模拟与沙箱推演模块测试"""
import numpy as np

from root.left.app.left.src.core_mod.simulate import (
    CounterfactualPlanner,
    EnvironmentSimulator,
    RiskAssessor,
    SandboxEngine,
    SimulationModule,
)


class TestEnvironmentSimulator:
    """EnvironmentSimulator 单元测试"""

    def test_init_normal(self) -> None:
        es = EnvironmentSimulator({"state_dim": 3, "noise_std": 0.01})
        assert es.state_dim == 3
        assert es.noise_std == 0.01

    def test_step(self) -> None:
        es = EnvironmentSimulator({"state_dim": 3})
        state = [0.5, 0.5, 0.5]
        action = [0.1, 0.1, 0.1]
        next_state = es.step(state, action)
        assert len(next_state) == 3
        assert all(0.0 <= v <= 1.0 for v in next_state)

    def test_step_pad(self) -> None:
        es = EnvironmentSimulator({"state_dim": 5})
        next_state = es.step([1.0], [0.1])
        assert len(next_state) == 5

    def test_step_truncate(self) -> None:
        es = EnvironmentSimulator({"state_dim": 2})
        next_state = es.step([0.1, 0.2, 0.3, 0.4], [0.1, 0.2, 0.3])
        assert len(next_state) == 2

    def test_reset(self) -> None:
        es = EnvironmentSimulator({"state_dim": 3})
        old = es.transition_matrix.copy()
        es.reset()
        assert not np.array_equal(old, es.transition_matrix)

    def test_get_state(self) -> None:
        es = EnvironmentSimulator({})
        s = es.get_state()
        assert s["state_dim"] == 5


class TestSandboxEngine:
    """SandboxEngine 单元测试"""

    def test_init_normal(self) -> None:
        se = SandboxEngine({"max_steps": 10})
        assert se.max_steps == 10

    def test_run_scenario(self) -> None:
        se = SandboxEngine({"max_steps": 5})
        result = se.run_scenario(
            [0.5, 0.5, 0.5],
            [[0.1, 0.1, 0.1] for _ in range(3)]
        )
        assert len(result["trajectory"]) == 4
        assert result["steps"] == 3

    def test_run_scenario_max_steps(self) -> None:
        se = SandboxEngine({"max_steps": 2})
        result = se.run_scenario(
            [0.5, 0.5],
            [[0.1, 0.1] for _ in range(10)]
        )
        assert result["steps"] == 2

    def test_run_scenario_empty_actions(self) -> None:
        se = SandboxEngine({})
        result = se.run_scenario([0.5, 0.5], [])
        assert result["steps"] == 0
        assert result["final_state"] == [0.5, 0.5]

    def test_get_state(self) -> None:
        se = SandboxEngine({})
        se.run_scenario([0.5], [])
        s = se.get_state()
        assert s["scenario_count"] == 1


class TestCounterfactualPlanner:
    """CounterfactualPlanner 单元测试"""

    def test_init_normal(self) -> None:
        cp = CounterfactualPlanner({"branch_factor": 2, "horizon": 3})
        assert cp.branch_factor == 2
        assert cp.horizon == 3

    def test_plan(self) -> None:
        cp = CounterfactualPlanner({"branch_factor": 2, "horizon": 2})
        branches = cp.plan(
            [0.5, 0.5],
            [[0.1, 0.1], [0.2, 0.2], [0.3, 0.3]]
        )
        assert len(branches) == 2
        assert "final_state" in branches[0]

    def test_plan_empty(self) -> None:
        cp = CounterfactualPlanner({})
        branches = cp.plan([0.5], [])
        assert branches == []

    def test_get_state(self) -> None:
        cp = CounterfactualPlanner({})
        s = cp.get_state()
        assert s["branch_factor"] == 3


class TestRiskAssessor:
    """RiskAssessor 单元测试"""

    def test_init_normal(self) -> None:
        ra = RiskAssessor({"risk_threshold": 0.5})
        assert ra.risk_threshold == 0.5

    def test_assess_empty(self) -> None:
        ra = RiskAssessor({})
        result = ra.assess([])
        assert result["risk_score"] == 0.0
        assert result["high_risk"] is False

    def test_assess_low_risk(self) -> None:
        ra = RiskAssessor({"risk_threshold": 0.5})
        traj = [[0.5, 0.5], [0.51, 0.49], [0.5, 0.5]]
        result = ra.assess(traj)
        assert result["risk_score"] < 0.5
        assert result["high_risk"] is False

    def test_assess_high_risk(self) -> None:
        ra = RiskAssessor({"risk_threshold": 0.1})
        traj = [[0.0], [1.0], [0.0], [1.0]]
        result = ra.assess(traj)
        assert result["high_risk"] is True

    def test_history_trim(self) -> None:
        ra = RiskAssessor({"max_history": 2})
        for i in range(5):
            ra.assess([[float(i)]])
        assert len(ra.history) == 2

    def test_get_state(self) -> None:
        ra = RiskAssessor({})
        s = ra.get_state()
        assert s["risk_threshold"] == 0.3


class TestSimulationModule:
    """SimulationModule 集成测试"""

    def test_init_normal(self) -> None:
        mod = SimulationModule({})
        assert mod.sandbox is not None
        assert mod.planner is not None
        assert mod.risk is not None

    def test_simulate(self) -> None:
        mod = SimulationModule({})
        result = mod.simulate(
            [0.5, 0.5],
            [[0.1, 0.1], [0.1, 0.1]]
        )
        assert "scenario" in result
        assert "risk" in result
        assert result["scenario"]["steps"] == 2

    def test_plan_counterfactual(self) -> None:
        mod = SimulationModule({"planner": {"branch_factor": 2, "horizon": 2}})
        result = mod.plan_counterfactual(
            [0.5, 0.5],
            [[0.1, 0.1], [0.2, 0.2], [0.3, 0.3]]
        )
        assert "branches" in result
        assert "best_branch" in result
        assert len(result["branches"]) == 2

    def test_plan_counterfactual_empty(self) -> None:
        mod = SimulationModule({})
        result = mod.plan_counterfactual([0.5], [])
        assert result["branches"] == []
        assert result["best_branch"] is None

    def test_get_state(self) -> None:
        mod = SimulationModule({})
        s = mod.get_state()
        assert "sandbox" in s
        assert "planner" in s
        assert "risk" in s

    def test_boundary_single_state(self) -> None:
        mod = SimulationModule({})
        result = mod.simulate([0.5], [])
        assert result["scenario"]["steps"] == 0

    def test_boundary_large_trajectory(self) -> None:
        mod = SimulationModule({})
        actions = [[0.01] * 5 for _ in range(100)]
        result = mod.simulate([0.5] * 5, actions)
        assert result["scenario"]["steps"] <= 50
