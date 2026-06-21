"""快速压力测试（100循环版）"""
import gc
import time

from root.left.app.left.src.main import SelfEvolvingAgent
from root.left.app.left.src.utils_main.logger import logger


def _fast_agent() -> SelfEvolvingAgent:
    config = SelfEvolvingAgent().config
    config["loop_interval"] = 0.0
    return SelfEvolvingAgent(config)


def test_100_loops_no_crash() -> None:
    agent = _fast_agent()
    agent.run(max_loops=100)
    assert agent.loop_count == 100


def test_100_loops_memory_stable() -> None:
    agent = _fast_agent()
    gc.collect()
    before = len(gc.get_objects())
    agent.run(max_loops=100)
    gc.collect()
    after = len(gc.get_objects())
    growth = after - before
    logger.info(f"Memory growth after 100 loops: {growth}", "stress")
    assert growth < 300000, f"Memory leak detected: growth={growth}"


def test_rapid_fire_100() -> None:
    agent = _fast_agent()
    start = time.time()
    agent.run(max_loops=100)
    elapsed = time.time() - start
    logger.info(f"100 rapid loops elapsed: {elapsed:.2f}s", "stress")
    assert elapsed < 10.0, f"Too slow: {elapsed:.2f}s"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
