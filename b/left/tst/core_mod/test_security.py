"""安全模块单元测试"""
import pytest

from root.left.app.left.src.core_mod.security import (
    InputSanitizer, SensitiveDataFilter, RateLimiter,
    ResourceGuard, SecurityModule,
)
from root.left.app.left.src.utils_main.exceptions import SafetyBoundaryException, ValidationError


class TestInputSanitizer:
    """测试InputSanitizer"""

    def test_normal_string(self) -> None:
        san = InputSanitizer({})
        assert san.sanitize_string("hello") == "hello"

    def test_path_traversal_blocked(self) -> None:
        san = InputSanitizer({})
        with pytest.raises(SafetyBoundaryException):
            san.validate_path("../../../etc/passwd")

    def test_sql_injection_blocked(self) -> None:
        san = InputSanitizer({})
        with pytest.raises(SafetyBoundaryException):
            san.validate_sql_safe("SELECT * FROM users")

    def test_command_injection_sanitized(self) -> None:
        san = InputSanitizer({})
        result = san.sanitize_string("hello; rm -rf /")
        assert ";" not in result

    def test_boundary_max_length(self) -> None:
        san = InputSanitizer({"max_string_length": 5})
        assert len(san.sanitize_string("123456789")) == 5

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            InputSanitizer(None)


class TestSensitiveDataFilter:
    """测试SensitiveDataFilter"""

    def test_normal_dict(self) -> None:
        filt = SensitiveDataFilter({})
        result = filt.filter_dict({"name": "test", "password": "secret"})
        assert result["name"] == "test"
        assert result["password"] == "***"

    def test_nested_dict(self) -> None:
        filt = SensitiveDataFilter({})
        result = filt.filter_dict({"user": {"api_key": "12345"}})
        assert result["user"]["api_key"] == "***"

    def test_string_filter(self) -> None:
        filt = SensitiveDataFilter({})
        result = filt.filter_string("token=abc123 secret=xyz")
        assert "abc123" not in result
        assert "***" in result


class TestRateLimiter:
    """测试RateLimiter"""

    def test_normal_allowed(self) -> None:
        rl = RateLimiter({"max_requests": 5, "window_seconds": 60.0})
        assert rl.is_allowed("key1") is True

    def test_boundary_exceeded(self) -> None:
        rl = RateLimiter({"max_requests": 2, "window_seconds": 60.0})
        rl.is_allowed("key1")
        rl.is_allowed("key1")
        assert rl.is_allowed("key1") is False

    def test_different_keys_isolated(self) -> None:
        rl = RateLimiter({"max_requests": 1, "window_seconds": 60.0})
        rl.is_allowed("key1")
        assert rl.is_allowed("key2") is True


class TestResourceGuard:
    """测试ResourceGuard"""

    def test_normal_file_size(self) -> None:
        rg = ResourceGuard({})
        assert rg.check_file_size(1024) is True

    def test_boundary_file_size_exceeded(self) -> None:
        rg = ResourceGuard({"max_file_size": 100})
        with pytest.raises(SafetyBoundaryException):
            rg.check_file_size(101)

    def test_boundary_memory_exceeded(self) -> None:
        rg = ResourceGuard({"max_memory_mb": 100})
        with pytest.raises(SafetyBoundaryException):
            rg.check_memory_usage(101.0)


class TestSecurityModule:
    """测试SecurityModule"""

    def test_normal_init(self) -> None:
        mod = SecurityModule({})
        assert mod.sanitizer is not None

    def test_sanitize_input(self) -> None:
        mod = SecurityModule({})
        assert mod.sanitize_input("hello") == "hello"

    def test_filter_sensitive(self) -> None:
        mod = SecurityModule({})
        result = mod.filter_sensitive_data({"token": "secret"})
        assert result["token"] == "***"

    def test_rate_limit(self) -> None:
        mod = SecurityModule({"rate_limiter": {"max_requests": 1, "window_seconds": 60.0}})
        assert mod.check_rate_limit("k1") is True
        assert mod.check_rate_limit("k1") is False

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            SecurityModule(None)
