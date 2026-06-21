"""Phase Two核心单元测试"""
import pytest
from root.left.app.left.src.core_mod.phase_two import PhaseTwoCore
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestPhaseTwoCore:
    """测试PhaseTwoCore"""

    def test_normal_init(self) -> None:
        core = PhaseTwoCore({"task_pool": {}, "decision": {}, "memory": {}})
        assert core.task_pool is not None

    def test_empty_config(self) -> None:
        core = PhaseTwoCore({"task_pool": {}, "decision": {}, "memory": {}})
        assert core.decision is not None

    def test_boundary_step(self) -> None:
        core = PhaseTwoCore({"task_pool": {}, "decision": {}, "memory": {}})
        phase1 = {"drive_state": {"gaps": {}}, "performance": 0.5, "state": {}}
        result = core.step(phase1, 1, 0.0, 0.0)
        assert "decision" in result

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            PhaseTwoCore(None)

    def test_should_pause(self) -> None:
        core = PhaseTwoCore({"task_pool": {}, "decision": {}, "memory": {}})
        phase1 = {"drive_state": {"gaps": {}}}
        result = core.should_pause(phase1)
        assert isinstance(result, bool)

    def test_step_with_tasks(self) -> None:
        core = PhaseTwoCore({"task_pool": {}, "decision": {}, "memory": {}})
        phase1 = {"drive_state": {"gaps": {}, "scenario": "normal"}, "performance": 0.5, "state": {}}
        result = core.step(phase1, 1, 0.0, 0.0)
        assert "task_pool_snapshot" in result
