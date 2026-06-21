"""Phase集成测试"""
from root.left.app.left.src.core_mod.phase_one import PhaseOneCore
from root.left.app.left.src.core_mod.phase_two import PhaseTwoCore
from root.left.app.left.src.core_mod.phase_three import PhaseThreeCore
from root.left.app.left.src.main import SelfEvolvingAgent


class TestPhaseOneToTwoIntegration:
    """测试Phase 1到Phase 2集成"""

    def test_phase1_to_phase2_flow(self) -> None:
        phase1 = PhaseOneCore({"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}})
        phase2 = PhaseTwoCore({"task_pool": {}, "decision": {}, "memory": {}})
        result1 = phase1.step()
        result2 = phase2.step(result1, 1, 0.0, 0.0)
        assert "decision" in result2
        assert "task_pool_snapshot" in result2

    def test_phase2_pause_trigger(self) -> None:
        phase1 = PhaseOneCore({"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}})
        phase2 = PhaseTwoCore({"task_pool": {}, "decision": {}, "memory": {}})
        result1 = phase1.step()
        assert isinstance(phase2.should_pause(result1), bool)


class TestPhaseTwoToThreeIntegration:
    """测试Phase 2到Phase 3集成"""

    def test_phase2_to_phase3_flow(self) -> None:
        phase1 = PhaseOneCore({"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}})
        phase2 = PhaseTwoCore({"task_pool": {}, "decision": {}, "memory": {}})
        phase3 = PhaseThreeCore({"evolution": {}})
        result1 = phase1.step()
        result2 = phase2.step(result1, 1, 0.0, 0.0)
        result3 = phase3.step({}, result1, result2)
        assert "evolution_result" in result3
        assert "should_rollback" in result3


class TestEndToEndAgent:
    """端到端Agent测试"""

    def test_agent_single_loop(self) -> None:
        config = {
            "phase1": {"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}},
            "phase2": {"task_pool": {}, "decision": {}, "memory": {}},
            "phase3": {"evolution": {}},
            "loop_interval": 0.0,
        }
        agent = SelfEvolvingAgent(config)
        agent.run(max_loops=1)
        assert agent.loop_count == 1
        assert agent.running is False

    def test_agent_multiple_loops(self) -> None:
        config = {
            "phase1": {"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}},
            "phase2": {"task_pool": {}, "decision": {}, "memory": {}},
            "phase3": {"evolution": {}},
            "loop_interval": 0.0,
        }
        agent = SelfEvolvingAgent(config)
        agent.run(max_loops=3)
        assert agent.loop_count == 3

    def test_agent_stop_midway(self) -> None:
        config = {
            "phase1": {"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}},
            "phase2": {"task_pool": {}, "decision": {}, "memory": {}},
            "phase3": {"evolution": {}},
            "loop_interval": 0.0,
        }
        agent = SelfEvolvingAgent(config)
        agent.run(max_loops=1)
        agent.stop()
        assert agent.running is False
