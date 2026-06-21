"""安全边界与攻击面加固模块"""
import re
import threading
from typing import Any, Dict, Final, List

from root.left.app.left.src.utils_main.exceptions import SafetyBoundaryException
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class InputSanitizer:
    """输入消毒器"""

    PATH_TRAVERSAL_PATTERN: Final[str] = r"\.\./|\.\.\\|~\/|%2e%2e"
    SQL_INJECTION_PATTERN: Final[str] = r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|--|;|\'|\"|\`))"
    COMMAND_INJECTION_PATTERN: Final[str] = r"[;&|`$]|\$\(|\`\`|\|\|"

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[InputSanitizer.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.max_string_length: int = int(config.get("max_string_length", 10000))
        self.allowed_chars: str = str(config.get("allowed_chars", ""))
        logger.info(f"InputSanitizer initialized max_len={self.max_string_length}", "security")

    def sanitize_string(self, value: str, field_name: str = "unknown") -> str:
        logger.debug(f"[InputSanitizer.sanitize_string] field={field_name}")
        if not isinstance(value, str):
            logger.debug("[InputSanitizer.sanitize_string] not string -> str()")
            value = str(value)
        if len(value) > self.max_string_length:
            logger.warning(f"[InputSanitizer.sanitize_string] truncated field={field_name}", "security")
            value = value[:self.max_string_length]
        sanitized = re.sub(self.PATH_TRAVERSAL_PATTERN, "", value)
        sanitized = re.sub(self.SQL_INJECTION_PATTERN, "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(self.COMMAND_INJECTION_PATTERN, "", sanitized)
        logger.debug("[InputSanitizer.sanitize_string] done")
        return sanitized

    def validate_path(self, path: str) -> str:
        logger.debug(f"[InputSanitizer.validate_path] path={path}")
        sanitized = self.sanitize_string(path, "path")
        if re.search(self.PATH_TRAVERSAL_PATTERN, path):
            logger.error(f"[InputSanitizer.validate_path] path traversal detected: {path}", "security")
            raise SafetyBoundaryException("Path traversal detected", "filesystem", "read_file")
        logger.debug("[InputSanitizer.validate_path] ok")
        return sanitized

    def validate_sql_safe(self, value: str) -> str:
        logger.debug(f"[InputSanitizer.validate_sql_safe] value={value[:50]}")
        if re.search(self.SQL_INJECTION_PATTERN, value, re.IGNORECASE):
            logger.error("[InputSanitizer.validate_sql_safe] SQL injection detected", "security")
            raise SafetyBoundaryException("SQL injection detected", "database", "query")
        logger.debug("[InputSanitizer.validate_sql_safe] ok")
        return value


class SensitiveDataFilter:
    """敏感数据过滤器"""

    SENSITIVE_KEYS: Final[List[str]] = [
        "password", "token", "secret", "api_key", "private_key",
        "credential", "auth", "passwd", "pwd", "key"
    ]

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[SensitiveDataFilter.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.mask: str = str(config.get("mask", "***"))
        logger.info("SensitiveDataFilter initialized", "security")

    def filter_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[SensitiveDataFilter.filter_dict] start")
        result = {}
        for key, value in data.items():
            if self._is_sensitive(key):
                result[key] = self.mask
                logger.debug(f"[SensitiveDataFilter.filter_dict] masked key={key}")
            elif isinstance(value, dict):
                result[key] = self.filter_dict(value)
            else:
                result[key] = value
        logger.debug("[SensitiveDataFilter.filter_dict] done")
        return result

    def _is_sensitive(self, key: str) -> bool:
        lower = key.lower()
        result = any(s in lower for s in self.SENSITIVE_KEYS)
        logger.debug(f"[SensitiveDataFilter._is_sensitive] key={key} result={result}")
        return result

    def filter_string(self, text: str) -> str:
        logger.debug("[SensitiveDataFilter.filter_string] start")
        for pattern in [r"token[=:]\s*\S+", r"api_key[=:]\s*\S+", r"secret[=:]\s*\S+"]:
            text = re.sub(pattern, lambda m: m.group(0).split("=")[0] + "=" + self.mask, text, flags=re.IGNORECASE)
        logger.debug("[SensitiveDataFilter.filter_string] done")
        return text


class RateLimiter:
    """速率限制器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[RateLimiter.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.max_requests: int = int(config.get("max_requests", 100))
        self.window_seconds: float = float(config.get("window_seconds", 60.0))
        self._requests: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
        logger.info(f"RateLimiter initialized max={self.max_requests}/window={self.window_seconds}s", "security")

    def is_allowed(self, key: str) -> bool:
        logger.debug(f"[RateLimiter.is_allowed] key={key}")
        now = __import__("time").time()
        with self._lock:
            if key not in self._requests:
                self._requests[key] = []
            window = [t for t in self._requests[key] if now - t < self.window_seconds]
            self._requests[key] = window
            if len(window) >= self.max_requests:
                logger.warning(f"[RateLimiter.is_allowed] rate limit exceeded for {key}", "security")
                return False
            self._requests[key].append(now)
            logger.debug(f"[RateLimiter.is_allowed] allowed key={key} count={len(self._requests[key])}")
            return True


class ResourceGuard:
    """资源守卫"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[ResourceGuard.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.max_file_size: int = int(config.get("max_file_size", 10 * 1024 * 1024))
        self.max_memory_mb: int = int(config.get("max_memory_mb", 512))
        self.max_cpu_percent: float = float(config.get("max_cpu_percent", 80.0))
        logger.info(f"ResourceGuard initialized max_file={self.max_file_size}", "security")

    def check_file_size(self, size: int) -> bool:
        logger.debug(f"[ResourceGuard.check_file_size] size={size}")
        if size > self.max_file_size:
            logger.error(f"[ResourceGuard.check_file_size] exceeded: {size}>{self.max_file_size}", "security")
            raise SafetyBoundaryException("File size exceeded", "filesystem", "write_file")
        logger.debug("[ResourceGuard.check_file_size] ok")
        return True

    def check_memory_usage(self, current_mb: float) -> bool:
        logger.debug(f"[ResourceGuard.check_memory_usage] current={current_mb}")
        if current_mb > self.max_memory_mb:
            logger.error(f"[ResourceGuard.check_memory_usage] exceeded: {current_mb}>{self.max_memory_mb}", "security")
            raise SafetyBoundaryException("Memory limit exceeded", "resource", "allocate")
        logger.debug("[ResourceGuard.check_memory_usage] ok")
        return True


class SecurityModule:
    """安全模块主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[SecurityModule.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.sanitizer = InputSanitizer(config.get("sanitizer", {}))
        logger.debug("[SecurityModule.__init__] sanitizer created")
        self.data_filter = SensitiveDataFilter(config.get("data_filter", {}))
        logger.debug("[SecurityModule.__init__] data_filter created")
        self.rate_limiter = RateLimiter(config.get("rate_limiter", {}))
        logger.debug("[SecurityModule.__init__] rate_limiter created")
        self.resource_guard = ResourceGuard(config.get("resource_guard", {}))
        logger.debug("[SecurityModule.__init__] resource_guard created")
        logger.info("SecurityModule initialized", "security")

    def sanitize_input(self, value: str, field_name: str = "unknown") -> str:
        logger.debug(f"[SecurityModule.sanitize_input] field={field_name}")
        return self.sanitizer.sanitize_string(value, field_name)

    def filter_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[SecurityModule.filter_sensitive_data] start")
        return self.data_filter.filter_dict(data)

    def check_rate_limit(self, key: str) -> bool:
        logger.debug(f"[SecurityModule.check_rate_limit] key={key}")
        return self.rate_limiter.is_allowed(key)

    def guard_file_write(self, size: int) -> bool:
        logger.debug(f"[SecurityModule.guard_file_write] size={size}")
        return self.resource_guard.check_file_size(size)

    def guard_memory(self, current_mb: float) -> bool:
        logger.debug(f"[SecurityModule.guard_memory] current={current_mb}")
        return self.resource_guard.check_memory_usage(current_mb)
