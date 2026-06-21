"""Phase Three核心单元测试"""
import pytest
from root.left.app.left.src.core_mod.phase_three import PhaseThreeCore
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestPhaseThreeCore:
    """测试PhaseThreeCore"""

    def test_normal_init(self) -> None:
        core = PhaseThreeCore({"evolution": {}})
        assert core.evolution is not None

    def test_empty_config(self) -> None:
        core = PhaseThreeCore({"evolution": {}})
        assert core.performance_history == []

    def test_boundary_step(self) -> None:
        core = PhaseThreeCore({"evolution": {}})
        phase1 = {"performance": 0.5, "predictions": {}, "state": {}}
        phase2 = {"decision": {}, "task_pool_snapshot": {}, "memory_recent": []}
        result = core.step({}, phase1, phase2)
        assert "evolution_result" in result

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            PhaseThreeCore(None)

    def test_get_error_rate(self) -> None:
        core = PhaseThreeCore({"evolution": {}})
        phase1 = {"performance": 0.5, "predictions": {}, "state": {"system_metrics": {}}}
        phase2 = {"decision": {}, "task_pool_snapshot": {}, "memory_recent": []}
        core.step({}, phase1, phase2)
        assert len(core.performance_history) == 1

    def test_error_rate_with_predictions(self) -> None:
        core = PhaseThreeCore({"evolution": {}})
        preds = {"low": [{"target_metric": "cpu", "predicted_value": 50.0}]}
        phase1 = {"performance": 0.5, "predictions": preds, "state": {"system_metrics": {"cpu": 55.0}}}
        phase2 = {"decision": {}, "task_pool_snapshot": {}, "memory_recent": []}
        result = core.step({}, phase1, phase2)
        assert "should_rollback" in result
