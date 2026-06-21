"""日志模块补充测试"""
from root.left.app.left.src.utils_main.logger import AgentLogger


class TestAgentLoggerExtra:
    """测试AgentLogger额外路径"""

    def test_debug(self) -> None:
        logger = AgentLogger()
        logger.debug("test debug")

    def test_warning(self) -> None:
        logger = AgentLogger()
        logger.warning("test warning")

    def test_critical(self) -> None:
        logger = AgentLogger()
        logger.critical("test critical")
