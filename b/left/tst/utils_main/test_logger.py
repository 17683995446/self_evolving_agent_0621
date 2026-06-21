"""日志单元测试"""
import logging
from root.left.app.left.src.utils_main.logger import AgentLogger


class TestAgentLogger:
    """测试AgentLogger"""

    def test_normal_singleton(self) -> None:
        logger1 = AgentLogger()
        logger2 = AgentLogger()
        assert logger1 is logger2

    def test_empty_name(self) -> None:
        logger = AgentLogger()
        assert logger.logger is not None

    def test_boundary_level(self) -> None:
        logger = AgentLogger()
        assert logger.logger.level == logging.DEBUG

    def test_invalid_format_direct_init_no_error(self) -> None:
        logger = AgentLogger()
        assert isinstance(logger.logger, logging.Logger)
