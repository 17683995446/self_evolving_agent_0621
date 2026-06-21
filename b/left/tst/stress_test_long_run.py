"""长周期压力测试与复杂场景模拟

测试目标：
1. 长时间运行（1000+循环）内存泄漏检测
2. 大规模任务队列压力（1000+任务）
3. 错综复杂的配置回滚场景
4. 极端边界条件（空值/极大值/负数）
5. 并发访问SQLite存储
6. 随机异常注入验证容错
"""
import copy
import random
import threading
import time
from typing import List

import pytest

from root.left.app.left.src.main import SelfEvolvingAgent
from root.left.app.left.src.utils_main.logger import logger


def _fast_agent() -> SelfEvolvingAgent:
    config = SelfEvolvingAgent().config
    config["loop_interval"] = 0.0
    return SelfEvolvingAgent(config)


class TestLongRunStress:
    """长周期压力测试"""

    def test_1000_loops_no_crash(self) -> None:
        """1000次循环不崩溃"""
        agent = _fast_agent()
        agent.run(max_loops=1000)
        assert agent.loop_count == 1000

    def test_1000_loops_memory_stable(self) -> None:
        """1000次循环内存不泄漏"""
        import gc
        agent = _fast_agent()
        gc.collect()
        before = len(gc.get_objects())
        agent.run(max_loops=1000)
        gc.collect()
        after = len(gc.get_objects())
        growth = after - before
        logger.info(f"Memory growth after 1000 loops: {growth}", "stress")
        assert growth < 1500000, f"Memory leak detected: growth={growth}"

    def test_rapid_fire_loops(self) -> None:
        """极速循环（无间隔）"""
        agent = _fast_agent()
        start = time.time()
        agent.run(max_loops=500)
        elapsed = time.time() - start
        logger.info(f"500 rapid loops elapsed: {elapsed:.2f}s", "stress")
        assert elapsed < 30.0, f"Too slow: {elapsed:.2f}s"


class TestComplexScenarios:
    """复杂场景模拟"""

    def test_rollback_chain_scenario(self) -> None:
        """连续回滚链场景"""
        agent = SelfEvolvingAgent()
        for i in range(50):
            agent._run_single_loop()
            if i % 10 == 0:
                agent.config = copy.deepcopy(agent.config)
                agent._init_phases(agent.config)
        assert agent.loop_count == 50

    def test_empty_drive_state(self) -> None:
        """空驱动状态注入"""
        agent = SelfEvolvingAgent()
        phase1 = agent.phase_one.step()
        phase1["drive_state"] = {}
        result = agent.phase_two.step(phase1, 1, 0.0, 0.0)
        assert "decision" in result

    def test_extreme_performance_values(self) -> None:
        """极端性能值"""
        agent = SelfEvolvingAgent()
        for val in [0.0, 1.0, -1.0, 1e9, -1e9, float('inf'), float('-inf')]:
            phase1 = agent.phase_one.step()
            phase1["performance"] = val
            try:
                agent.phase_two.step(phase1, 1, 0.0, 0.0)
                agent.phase_three.step(agent.config, phase1, {"decision": {}})
            except Exception as e:
                logger.error(f"Exception with performance={val}: {e}", "stress")
                raise

    def test_massive_task_pool(self) -> None:
        """大规模任务池"""
        agent = SelfEvolvingAgent()
        for _ in range(100):
            drive_state = agent.phase_one.step()["drive_state"]
            agent.phase_two.task_pool.generate_and_enqueue(drive_state)
        snapshot = agent.phase_two.task_pool.get_pool_snapshot()
        logger.info(f"Massive pool total={snapshot['total']}", "stress")
        assert snapshot["total"] > 0

    def test_random_config_corruption(self) -> None:
        """随机配置损坏恢复"""
        agent = SelfEvolvingAgent()
        for i in range(20):
            if i == 10:
                agent.config["phase1"] = None
                try:
                    agent._init_phases(agent.config)
                except Exception:
                    agent.config = SelfEvolvingAgent().config
                    agent._init_phases(agent.config)
            else:
                agent._run_single_loop()
        assert agent.loop_count >= 19


class TestConcurrencyStress:
    """并发压力测试"""

    def test_concurrent_memory_access(self) -> None:
        """并发内存访问"""
        agent = SelfEvolvingAgent()
        errors: List[str] = []

        def writer() -> None:
            for i in range(100):
                try:
                    agent.phase_two.memory.record_state(i, {}, {}, 0.5)
                except Exception as e:
                    errors.append(str(e))

        def reader() -> None:
            for _ in range(100):
                try:
                    agent.phase_two.memory.get_recent_states(10)
                except Exception as e:
                    errors.append(str(e))

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=writer),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors, f"Concurrent errors: {errors[:5]}"

    def test_concurrent_task_pool(self) -> None:
        """并发任务池操作"""
        agent = SelfEvolvingAgent()
        errors: List[str] = []

        def producer() -> None:
            for _ in range(50):
                try:
                    drive = agent.phase_one.step()["drive_state"]
                    agent.phase_two.task_pool.generate_and_enqueue(drive)
                except Exception as e:
                    errors.append(str(e))

        def consumer() -> None:
            for _ in range(50):
                try:
                    task = agent.phase_two.task_pool.pool.get_next()
                    if task:
                        task.status = 3
                except Exception as e:
                    errors.append(str(e))

        threads = [
            threading.Thread(target=producer),
            threading.Thread(target=consumer),
            threading.Thread(target=producer),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors, f"Concurrent task pool errors: {errors[:5]}"


class TestEdgeCases:
    """边界与异常场景"""

    def test_none_config_fallback(self) -> None:
        """None配置回退"""
        try:
            agent = SelfEvolvingAgent(config=None)
            agent.run(max_loops=5)
        except Exception as e:
            logger.error(f"None config failed: {e}", "stress")
            raise

    def test_very_long_string_metric(self) -> None:
        """超长字符串指标"""
        agent = SelfEvolvingAgent()
        state = agent.phase_one.sensory.perceive()
        state["system_metrics"]["test_metric"] = "x" * 100000
        predictions = agent.phase_one.prediction.predict(state)
        assert isinstance(predictions, dict)

    def test_nested_dict_corruption(self) -> None:
        """嵌套字典损坏"""
        agent = SelfEvolvingAgent()
        phase1 = agent.phase_one.step()
        phase1["predictions"] = {"low": None, "mid": "invalid", "high": [1, 2, 3]}
        try:
            agent.phase_three.step(agent.config, phase1, {"decision": {}})
        except Exception as e:
            logger.warning(f"Expected exception for corrupted predictions: {e}", "stress")

    def test_simultaneous_rollback_and_evolve(self) -> None:
        """同时回滚与进化"""
        agent = SelfEvolvingAgent()
        for i in range(30):
            agent._run_single_loop()
            if i == 15:
                agent.phase_three.evolution.snapshot_manager.save(agent.config, 0.99)
                agent.phase_three.evolution.snapshot_manager.best_performance = 0.99
                agent.config["loop_interval"] = 0.001
                agent._init_phases(agent.config)
        assert agent.loop_count == 30


class TestChaosMonkey:
    """混沌测试"""

    def test_random_field_deletion(self) -> None:
        """随机字段删除"""
        agent = SelfEvolvingAgent()
        for _ in range(50):
            phase1 = agent.phase_one.step()
            if random.random() < 0.3:
                key = random.choice(list(phase1.keys()))
                del phase1[key]
            try:
                agent.phase_two.step(phase1, 1, 0.0, 0.0)
            except Exception as e:
                logger.warning(f"Expected error after field deletion: {e}", "stress")

    def test_random_type_mutation(self) -> None:
        """随机类型变异"""
        agent = SelfEvolvingAgent()
        for _ in range(50):
            phase1 = agent.phase_one.step()
            if random.random() < 0.3:
                phase1["performance"] = random.choice(["string", None, [], {}])
            try:
                agent.phase_three.step(agent.config, phase1, {"decision": {}})
            except Exception as e:
                logger.warning(f"Expected error after type mutation: {e}", "stress")

    def test_resource_exhaustion_simulation(self) -> None:
        """资源耗尽模拟"""
        agent = SelfEvolvingAgent()
        for i in range(20):
            try:
                agent.phase_two.step(
                    agent.phase_one.step(),
                    i,
                    9999.0,
                    9999.0
                )
            except Exception as e:
                logger.info(f"Resource exhaustion caught: {e}", "stress")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
