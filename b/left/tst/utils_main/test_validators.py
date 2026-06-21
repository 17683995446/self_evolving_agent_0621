"""验证器单元测试"""
import pytest
from root.left.app.left.src.utils_main.validators import Validator, ConfigValidator
from root.left.app.left.src.utils_main.exceptions import ValidationError, ConfigurationError


class TestValidatorRequireType:
    """测试require_type"""

    def test_normal_value(self) -> None:
        Validator.require_type("hello", str, "name")

    def test_empty_string(self) -> None:
        Validator.require_type("", str, "name")

    def test_boundary_none(self) -> None:
        with pytest.raises(ValidationError):
            Validator.require_type(None, str, "name")

    def test_invalid_format_int_as_str(self) -> None:
        with pytest.raises(ValidationError):
            Validator.require_type(123, str, "name")


class TestValidatorRequireNonEmpty:
    """测试require_non_empty"""

    def test_normal_value(self) -> None:
        Validator.require_non_empty("hello", "name")

    def test_empty_string(self) -> None:
        with pytest.raises(ValidationError):
            Validator.require_non_empty("", "name")

    def test_boundary_whitespace(self) -> None:
        Validator.require_non_empty(" ", "name")

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            Validator.require_non_empty(None, "name")


class TestValidatorRequireRange:
    """测试require_range"""

    def test_normal_value(self) -> None:
        Validator.require_range(0.5, 0.0, 1.0, "alpha")

    def test_boundary_min(self) -> None:
        Validator.require_range(0.0, 0.0, 1.0, "alpha")

    def test_boundary_max(self) -> None:
        Validator.require_range(1.0, 0.0, 1.0, "alpha")

    def test_invalid_format_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            Validator.require_range(1.5, 0.0, 1.0, "alpha")


class TestValidatorRequirePositive:
    """测试require_positive"""

    def test_normal_value(self) -> None:
        Validator.require_positive(1.0, "value")

    def test_boundary_zero(self) -> None:
        with pytest.raises(ValidationError):
            Validator.require_positive(0.0, "value")

    def test_boundary_small_positive(self) -> None:
        Validator.require_positive(0.0001, "value")

    def test_invalid_format_negative(self) -> None:
        with pytest.raises(ValidationError):
            Validator.require_positive(-1.0, "value")


class TestValidatorRequireNonNegative:
    """测试require_non_negative"""

    def test_normal_value(self) -> None:
        Validator.require_non_negative(0.0, "value")

    def test_boundary_zero(self) -> None:
        Validator.require_non_negative(0.0, "value")

    def test_boundary_positive(self) -> None:
        Validator.require_non_negative(1.0, "value")

    def test_invalid_format_negative(self) -> None:
        with pytest.raises(ValidationError):
            Validator.require_non_negative(-0.1, "value")


class TestConfigValidator:
    """测试ConfigValidator"""

    def test_normal_config(self) -> None:
        config = {
            "phase1": {"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}},
            "phase2": {"task_pool": {}, "decision": {}, "memory": {}},
            "phase3": {"evolution": {}},
        }
        ConfigValidator.validate_config(config)

    def test_empty_config(self) -> None:
        with pytest.raises(ConfigurationError):
            ConfigValidator.validate_config({})

    def test_boundary_missing_one_key(self) -> None:
        with pytest.raises(ConfigurationError):
            ConfigValidator.validate_config({"phase1": {}, "phase2": {}, "phase3": {}})

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            ConfigValidator.validate_config(None)

    def test_invalid_phase_type(self) -> None:
        with pytest.raises(ValidationError):
            ConfigValidator.validate_config({
                "phase1": "not_a_dict",
                "phase2": {},
                "phase3": {"evolution": {}},
            })

    def test_invalid_loop_interval(self) -> None:
        with pytest.raises(ConfigurationError):
            ConfigValidator.validate_config({
                "phase1": {"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}},
                "phase2": {"task_pool": {}, "decision": {}, "memory": {}},
                "phase3": {"evolution": {}},
                "loop_interval": -1.0,
            })

    def test_invalid_loop_interval_type(self) -> None:
        with pytest.raises(ConfigurationError):
            ConfigValidator.validate_config({
                "phase1": {"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}},
                "phase2": {"task_pool": {}, "decision": {}, "memory": {}},
                "phase3": {"evolution": {}},
                "loop_interval": "fast",
            })

    def test_invalid_max_loops(self) -> None:
        with pytest.raises(ConfigurationError):
            ConfigValidator.validate_config({
                "phase1": {"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}},
                "phase2": {"task_pool": {}, "decision": {}, "memory": {}},
                "phase3": {"evolution": {}},
                "max_loops": -1,
            })

    def test_invalid_log_level(self) -> None:
        with pytest.raises(ConfigurationError):
            ConfigValidator.validate_config({
                "phase1": {"sensory": {}, "drive": {}, "prediction": {}, "adjustment": {}},
                "phase2": {"task_pool": {}, "decision": {}, "memory": {}},
                "phase3": {"evolution": {}},
                "log_level": "VERBOSE",
            })
