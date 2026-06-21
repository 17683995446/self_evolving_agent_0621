"""主入口单元测试"""
import pytest
from root.left.app.left.src.main import SelfEvolvingAgent
from root.left.app.left.src.utils_main.exceptions import ConfigurationError
from root.left.app.left.src.utils_main.module_inspector import ModuleComplianceInspector


class TestSelfEvolvingAgent:
    """测试SelfEvolvingAgent"""

    def test_normal_init(self) -> None:
        config = {
            "phase1": {"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}},
            "phase2": {"task_pool": {}, "decision": {}, "memory": {}},
            "phase3": {"evolution": {}},
            "loop_interval": 0.01,
        }
        agent = SelfEvolvingAgent(config)
        try:
            assert agent.phase_one is not None
        finally:
            agent.close()

    def test_empty_config(self) -> None:
        with pytest.raises(ConfigurationError):
            SelfEvolvingAgent({})

    def test_boundary_run_one_loop(self) -> None:
        config = {
            "phase1": {"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}},
            "phase2": {"task_pool": {}, "decision": {}, "memory": {}},
            "phase3": {"evolution": {}},
            "loop_interval": 0.0,
        }
        agent = SelfEvolvingAgent(config)
        try:
            agent.run(max_loops=1)
            assert agent.loop_count == 1
        finally:
            agent.close()

    def test_invalid_format_none(self) -> None:
        agent = SelfEvolvingAgent(None)
        try:
            assert agent.config is not None
        finally:
            agent.close()

    def test_stop(self):
        config = {
            "phase1": {"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}},
            "phase2": {"task_pool": {}, "decision": {}, "memory": {}},
            "phase3": {"evolution": {}},
            "loop_interval": 0.0,
        }
        agent = SelfEvolvingAgent(config)
        try:
            agent.stop()
            assert agent.running is False
        finally:
            agent.close()

    def test_get_core_modules(self):
        config = {
            "phase1": {"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}},
            "phase2": {"task_pool": {}, "decision": {}, "memory": {}},
            "phase3": {"evolution": {}},
            "loop_interval": 0.0,
        }
        agent = SelfEvolvingAgent(config)
        try:
            modules = agent.get_core_modules()
            expected = {
                "action_executor",
                "effect_verifier",
                "recommendation_engine",
                "dashboard",
                "phase_one",
                "phase_two",
                "phase_three",
                "data_collector",
            }
            assert set(modules.keys()) == expected
        finally:
            agent.close()

    def test_core_modules_are_compliant(self):
        config = {
            "phase1": {"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}},
            "phase2": {"task_pool": {}, "decision": {}, "memory": {}},
            "phase3": {"evolution": {}},
            "loop_interval": 0.0,
        }
        agent = SelfEvolvingAgent(config)
        try:
            modules = agent.get_core_modules()
            inspector = ModuleComplianceInspector()
            assert inspector.is_fully_compliant(modules) is True
        finally:
            agent.close()

    def test_core_module_health_checks_pass(self):
        config = {
            "phase1": {"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}},
            "phase2": {"task_pool": {}, "decision": {}, "memory": {}},
            "phase3": {"evolution": {}},
            "loop_interval": 0.0,
        }
        agent = SelfEvolvingAgent(config)
        try:
            modules = agent.get_core_modules()
            for name, module in modules.items():
                assert module.health_check() is True, f"{name} health_check failed"
        finally:
            agent.close()

    def test_core_module_get_state_returns_dict(self):
        config = {
            "phase1": {"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}},
            "phase2": {"task_pool": {}, "decision": {}, "memory": {}},
            "phase3": {"evolution": {}},
            "loop_interval": 0.0,
        }
        agent = SelfEvolvingAgent(config)
        try:
            modules = agent.get_core_modules()
            for name, module in modules.items():
                state = module.get_state()
                assert isinstance(state, dict), f"{name}.get_state() must return dict"
        finally:
            agent.close()

    def test_close_closes_modules(self):
        config = {
            "phase1": {"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}},
            "phase2": {"task_pool": {}, "decision": {}, "memory": {}},
            "phase3": {"evolution": {}},
            "loop_interval": 0.0,
        }
        agent = SelfEvolvingAgent(config)
        agent.close()
        assert agent.running is False

    def test_close_is_idempotent(self):
        config = {
            "phase1": {"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}},
            "phase2": {"task_pool": {}, "decision": {}, "memory": {}},
            "phase3": {"evolution": {}},
            "loop_interval": 0.0,
        }
        agent = SelfEvolvingAgent(config)
        agent.close()
        agent.close()
