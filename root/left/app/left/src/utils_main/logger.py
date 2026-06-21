"""严格日志系统"""
import logging
import sys
from typing import Optional


class AgentLogger:
    """Agent专用日志器"""

    _instance: Optional["AgentLogger"] = None

    def __new__(cls) -> "AgentLogger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.logger = logging.getLogger("SelfEvolvingAgent")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def debug(self, message: str, module: Optional[str] = None) -> None:
        self._log(logging.DEBUG, message, module)

    def info(self, message: str, module: Optional[str] = None) -> None:
        self._log(logging.INFO, message, module)

    def warning(self, message: str, module: Optional[str] = None) -> None:
        self._log(logging.WARNING, message, module)

    def error(self, message: str, module: Optional[str] = None, exc_info: bool = False) -> None:
        self._log(logging.ERROR, message, module, exc_info)

    def critical(self, message: str, module: Optional[str] = None, exc_info: bool = True) -> None:
        self._log(logging.CRITICAL, message, module, exc_info)

    def _log(self, level: int, message: str, module: Optional[str], exc_info: bool = False) -> None:
        prefix = f"[{module}] " if module else ""
        self.logger.log(level, f"{prefix}{message}", exc_info=exc_info)


logger = AgentLogger()
