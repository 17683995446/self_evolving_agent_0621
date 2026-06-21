"""Phase One核心单元测试"""
import pytest
from root.left.app.left.src.core_mod.phase_one import PhaseOneCore
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestPhaseOneCore:
    """测试PhaseOneCore"""

    def test_normal_init(self) -> None:
        core = PhaseOneCore({"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}})
        assert core.sensory is not None

    def test_empty_config(self) -> None:
        core = PhaseOneCore({"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}})
        assert core.drive_engine is not None

    def test_boundary_step(self) -> None:
        core = PhaseOneCore({"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}})
        result = core.step()
        assert "state" in result

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            PhaseOneCore(None)

    def test_step_returns_performance(self) -> None:
        core = PhaseOneCore({"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}})
        result = core.step()
        assert "performance" in result

    def test_calc_performance_range(self) -> None:
        core = PhaseOneCore({"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}})
        drive_state = {"total_reward": 0.5}
        perf = core._calc_performance(drive_state, 0.1)
        assert 0.0 <= perf <= 1.0
