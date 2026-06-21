"""异常类单元测试"""
import pytest
from root.left.app.left.src.utils_main.exceptions import (
    AgentException, ConfigurationError, ValidationError,
    SensoryException, DriveEngineException, PredictionException,
    TaskPoolException, DecisionException, MemoryException,
    EvolutionException, ResourceLimitException, SafetyBoundaryException,
)
from root.left.app.left.src.utils_main.constants import ErrorCode


class TestAgentException:
    """测试AgentException"""

    def test_normal_value(self) -> None:
        exc = AgentException("test", ErrorCode.SUCCESS)
        assert exc.error_code == ErrorCode.SUCCESS

    def test_empty_message(self) -> None:
        exc = AgentException("", ErrorCode.SUCCESS)
        assert str(exc) == ""

    def test_boundary_none_context(self) -> None:
        exc = AgentException("test", ErrorCode.SUCCESS, None)
        assert exc.context == {}

    def test_invalid_format_no_args(self) -> None:
        with pytest.raises(TypeError):
            AgentException()


class TestConfigurationError:
    """测试ConfigurationError"""

    def test_normal_value(self) -> None:
        exc = ConfigurationError("bad config", config_key="key")
        assert exc.module == "config"

    def test_empty_message(self) -> None:
        exc = ConfigurationError("")
        assert exc.error_code == ErrorCode.CONFIGURATION_ERROR

    def test_boundary_none_values(self) -> None:
        exc = ConfigurationError("test", None, None, None)
        assert exc.context["config_key"] is None

    def test_invalid_format_wrong_type(self) -> None:
        with pytest.raises(TypeError):
            ConfigurationError()


class TestValidationError:
    """测试ValidationError"""

    def test_normal_value(self) -> None:
        exc = ValidationError("bad value", field="f", expected_range="0-1", actual_value=2)
        assert exc.context["field"] == "f"

    def test_empty_message(self) -> None:
        exc = ValidationError("")
        assert exc.error_code == ErrorCode.INVALID_PARAMETER

    def test_boundary_none_values(self) -> None:
        exc = ValidationError("test", None, None, None)
        assert exc.context["field"] is None

    def test_invalid_format_no_args(self) -> None:
        with pytest.raises(TypeError):
            ValidationError()


class TestSensoryException:
    """测试SensoryException"""

    def test_normal_value(self) -> None:
        exc = SensoryException("fail", collector="cpu")
        assert exc.module == "sensory"

    def test_empty_message(self) -> None:
        exc = SensoryException("")
        assert exc.error_code == ErrorCode.SENSORY_ERROR

    def test_boundary_none_collector(self) -> None:
        exc = SensoryException("test", None)
        assert exc.context["collector"] is None

    def test_invalid_format_no_args(self) -> None:
        with pytest.raises(TypeError):
            SensoryException()


class TestDriveEngineException:
    """测试DriveEngineException"""

    def test_normal_value(self) -> None:
        exc = DriveEngineException("fail", drive_type="safe")
        assert exc.module == "drive_engine"

    def test_empty_message(self) -> None:
        exc = DriveEngineException("")
        assert exc.error_code == ErrorCode.DRIVE_ENGINE_ERROR

    def test_boundary_none_drive(self) -> None:
        exc = DriveEngineException("test", None)
        assert exc.context["drive_type"] is None

    def test_invalid_format_no_args(self) -> None:
        with pytest.raises(TypeError):
            DriveEngineException()


class TestPredictionException:
    """测试PredictionException"""

    def test_normal_value(self) -> None:
        exc = PredictionException("fail", level="low", metric="cpu")
        assert exc.module == "prediction"

    def test_empty_message(self) -> None:
        exc = PredictionException("")
        assert exc.error_code == ErrorCode.PREDICTION_ERROR

    def test_boundary_none_level(self) -> None:
        exc = PredictionException("test", None, None)
        assert exc.context["level"] is None

    def test_invalid_format_no_args(self) -> None:
        with pytest.raises(TypeError):
            PredictionException()


class TestTaskPoolException:
    """测试TaskPoolException"""

    def test_normal_value(self) -> None:
        exc = TaskPoolException("full", task_id="t1")
        assert exc.module == "task_pool"

    def test_empty_message(self) -> None:
        exc = TaskPoolException("")
        assert exc.error_code == ErrorCode.TASK_POOL_ERROR

    def test_boundary_none_task(self) -> None:
        exc = TaskPoolException("test", None)
        assert exc.context["task_id"] is None

    def test_invalid_format_no_args(self) -> None:
        with pytest.raises(TypeError):
            TaskPoolException()


class TestDecisionException:
    """测试DecisionException"""

    def test_normal_value(self) -> None:
        exc = DecisionException("bad", task_count=1)
        assert exc.module == "decision"

    def test_empty_message(self) -> None:
        exc = DecisionException("")
        assert exc.error_code == ErrorCode.DECISION_ERROR

    def test_boundary_none_count(self) -> None:
        exc = DecisionException("test", None)
        assert exc.context["task_count"] is None

    def test_invalid_format_no_args(self) -> None:
        with pytest.raises(TypeError):
            DecisionException()


class TestMemoryException:
    """测试MemoryException"""

    def test_normal_value(self) -> None:
        exc = MemoryException("fail", operation="read")
        assert exc.module == "memory"

    def test_empty_message(self) -> None:
        exc = MemoryException("")
        assert exc.error_code == ErrorCode.MEMORY_ERROR

    def test_boundary_none_op(self) -> None:
        exc = MemoryException("test", None)
        assert exc.context["operation"] is None

    def test_invalid_format_no_args(self) -> None:
        with pytest.raises(TypeError):
            MemoryException()


class TestEvolutionException:
    """测试EvolutionException"""

    def test_normal_value(self) -> None:
        exc = EvolutionException("fail", phase="refactor")
        assert exc.module == "evolution"

    def test_empty_message(self) -> None:
        exc = EvolutionException("")
        assert exc.error_code == ErrorCode.EVOLUTION_ERROR

    def test_boundary_none_phase(self) -> None:
        exc = EvolutionException("test", None)
        assert exc.context["phase"] is None

    def test_invalid_format_no_args(self) -> None:
        with pytest.raises(TypeError):
            EvolutionException()


class TestResourceLimitException:
    """测试ResourceLimitException"""

    def test_normal_value(self) -> None:
        exc = ResourceLimitException("limit", "cpu", 50.0, 20.0)
        assert exc.module == "resource"

    def test_empty_message(self) -> None:
        exc = ResourceLimitException("", "cpu", 0.0, 0.0)
        assert exc.error_code == ErrorCode.RESOURCE_LIMIT_EXCEEDED

    def test_boundary_zero_values(self) -> None:
        exc = ResourceLimitException("test", "mem", 0.0, 0.0)
        assert exc.context["current_value"] == 0.0

    def test_invalid_format_no_args(self) -> None:
        with pytest.raises(TypeError):
            ResourceLimitException()


class TestSafetyBoundaryException:
    """测试SafetyBoundaryException"""

    def test_normal_value(self) -> None:
        exc = SafetyBoundaryException("unsafe", "cpu", "kill")
        assert exc.module == "safety"

    def test_empty_message(self) -> None:
        exc = SafetyBoundaryException("", "", "")
        assert exc.error_code == ErrorCode.SAFETY_BOUNDARY_VIOLATED

    def test_boundary_none_values(self) -> None:
        exc = SafetyBoundaryException("test", None, None)
        assert exc.context["boundary"] is None

    def test_invalid_format_no_args(self) -> None:
        with pytest.raises(TypeError):
            SafetyBoundaryException()


class TestFormatForUser:
    """测试 format_for_user 用户友好错误信息"""

    def test_configuration_error_has_suggestion(self) -> None:
        exc = ConfigurationError("missing key", config_key="phase1")
        text = exc.format_for_user()
        assert "[config]" in text
        assert "missing key" in text
        assert "建议:" in text
        assert "cli config --show-defaults" in text

    def test_validation_error_has_suggestion(self) -> None:
        exc = ValidationError("bad type", field="name")
        text = exc.format_for_user()
        assert "[validation]" in text
        assert "建议:" in text

    def test_memory_error_has_suggestion(self) -> None:
        exc = MemoryException("db locked", operation="write")
        text = exc.format_for_user()
        assert "[memory]" in text
        assert "磁盘空间" in text

    def test_safety_error_has_suggestion(self) -> None:
        exc = SafetyBoundaryException("over limit", "cpu", "kill")
        text = exc.format_for_user()
        assert "[safety]" in text
        assert "安全边界" in text

    def test_base_exception_no_suggestion(self) -> None:
        exc = AgentException("base error", ErrorCode.SUCCESS)
        text = exc.format_for_user()
        assert "[unknown]" in text
        assert "base error" in text
        assert "建议" not in text

    def test_all_subclasses_have_suggestion(self) -> None:
        from root.left.app.left.src.utils_main import exceptions as exc_mod

        for name in dir(exc_mod):
            obj = getattr(exc_mod, name)
            if (
                isinstance(obj, type)
                and issubclass(obj, AgentException)
                and obj is not AgentException
            ):
                assert obj.user_suggestion is not None, f"{name} 缺少 user_suggestion"
