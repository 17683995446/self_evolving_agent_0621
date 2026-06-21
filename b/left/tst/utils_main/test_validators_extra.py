"""验证器补充测试"""
import pytest
from root.left.app.left.src.utils_main.validators import Validator, ConfigValidator
from root.left.app.left.src.utils_main.exceptions import ValidationError, ConfigurationError


class TestValidatorRequireNonEmpty:
    """测试require_non_empty"""

    def test_empty_string(self) -> None:
        with pytest.raises(ValidationError):
            Validator.require_non_empty("", "name")

    def test_whitespace(self) -> None:
        Validator.require_non_empty(" ", "name")

    def test_none(self) -> None:
        with pytest.raises(ValidationError):
            Validator.require_non_empty(None, "name")


class TestConfigValidatorExtra:
    """测试ConfigValidator额外路径"""

    def test_missing_phase1_keys(self) -> None:
        with pytest.raises(ConfigurationError):
            ConfigValidator.validate_config({
                "phase1": {}, "phase2": {}, "phase3": {}
            })
