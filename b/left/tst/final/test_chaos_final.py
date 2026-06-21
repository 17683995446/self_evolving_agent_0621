"""最终混沌与边界场景测试

补充高强度异常注入测试，覆盖配置随机变异、并发模块访问、
快速配置回滚、内存存储溢出、决策模块过载等场景。
"""
import copy
import random
import threading
import time
from typing import List

import pytest

from root.left.app.left.src.main import SelfEvolvingAgent
from root.left.app.left.src.utils_main.logger import logger


# 固定随机种子，确保测试可复现
random.seed(42)


class TestConfigChaos:
    """配置混沌测试"""

    def test_random_config_mutation(self) -> None:
        """配置随机字段变异后系统仍可继续运行"""
        random.seed(42)
        agent = SelfEvolvingAgent()
        for i in range(30):
            agent._run_single_loop()
            if i % 5 == 0:
                mutated = copy.deepcopy(agent.config)
                key = random.choice(list(mutated.keys()))
                if isinstance(mutated[key], dict):
                    sub_key = random.choice(list(mutated[key].keys()))
                    mutated[key][sub_key] = random.choice([None, {}, [], 0, -1, "chaos"])
                else:
                    mutated[key] = random.choice([None, 0, -1, "chaos"])
                try:
                    agent._init_phases(mutated)
                    agent.config = mutated
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"Config mutation rollback: {exc}", "chaos")
                    agent.config = SelfEvolvingAgent().config
                    agent._init_phases(agent.config)
        assert agent.loop_count >= 30


class TestConcurrentChaos:
    """并发混沌测试"""

    def test_concurrent_module_access(self) -> None:
        """多线程并发访问感知、决策、任务池模块"""
        agent = SelfEvolvingAgent()
        errors: List[str] = []
        loops_per_thread = 30

        def phase1_worker() -> None:
            for _ in range(loops_per_thread):
                try:
                    agent.phase_one.step()
                except Exception as e:
                    errors.append(str(e))

        def phase2_worker() -> None:
            for i in range(loops_per_thread):
                try:
                    phase1 = agent.phase_one.step()
                    agent.phase_two.step(phase1, i, 0.0, 0.0)
                except Exception as e:
                    errors.append(str(e))

        def pool_worker() -> None:
            for _ in range(loops_per_thread):
                try:
                    drive = agent.phase_one.step()["drive_state"]
                    agent.phase_two.task_pool.generate_and_enqueue(drive)
                except Exception as e:
                    errors.append(str(e))

        threads = [
            threading.Thread(target=phase1_worker),
            threading.Thread(target=phase2_worker),
            threading.Thread(target=pool_worker),
            threading.Thread(target=phase2_worker),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"并发访问出现错误: {errors[:5]}"


class TestRollbackChaos:
    """回滚混沌测试"""

    def test_rapid_config_rollback(self) -> None:
        """快速连续触发配置回滚"""
        agent = SelfEvolvingAgent()
        baseline_config = copy.deepcopy(agent.config)
        rollback_count = 0
        for i in range(50):
            agent._run_single_loop()
            if i % 7 == 0:
                agent.phase_three.evolution.snapshot_manager.save(
                    agent.config,
                    agent.phase_one.step().get("performance", 0.0),
                )
            if i % 11 == 0:
                # 注入非法配置，触发异常后回滚到基线配置
                corrupted = copy.deepcopy(baseline_config)
                corrupted["phase1"] = None
                agent.config = corrupted
                try:
                    agent._init_phases(agent.config)
                except Exception:  # noqa: BLE001
                    agent.config = copy.deepcopy(baseline_config)
                    agent._init_phases(agent.config)
                    rollback_count += 1
        assert agent.loop_count >= 50
        assert rollback_count >= 1


class TestMemoryStoreChaos:
    """内存存储混沌测试"""

    def test_memory_store_overflow(self) -> None:
        """向 SQLite 存储写入大量记录，验证截断与稳定性"""
        agent = SelfEvolvingAgent()
        store = agent.phase_two.memory.store
        original_max = store.max_records
        store.max_records = 50
        try:
            for i in range(200):
                store.save_state(i, "{}", "{}", float(i % 10))
            count = store._get_conn().cursor().execute("SELECT COUNT(*) FROM states").fetchone()[0]
            assert count <= store.max_records, f"记录数超过最大限制: {count}"
        finally:
            store.max_records = original_max

    def test_memory_record_race(self) -> None:
        """多线程并发写入记忆记录"""
        agent = SelfEvolvingAgent()
        errors: List[str] = []

        def writer(start: int) -> None:
            for i in range(start, start + 50):
                try:
                    agent.phase_two.memory.record_state(i, {"i": i}, {"j": i}, 0.5)
                except Exception as e:
                    errors.append(str(e))

        threads = [
            threading.Thread(target=writer, args=(1,)),
            threading.Thread(target=writer, args=(1000,)),
            threading.Thread(target=writer, args=(2000,)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"并发记忆写入错误: {errors[:5]}"


class TestDecisionOverload:
    """决策模块过载测试"""

    def test_decision_module_overload(self) -> None:
        """向决策模块投喂超大任务池与高频调用"""
        agent = SelfEvolvingAgent()
        drive = agent.phase_one.step()["drive_state"]
        pool = agent.phase_two.task_pool
        for _ in range(300):
            pool.generate_and_enqueue(drive)

        decision_count = 0
        start = time.time()
        while time.time() - start < 1.0:
            phase1 = agent.phase_one.step()
            agent.phase_two.step(phase1, decision_count, 0.0, 0.0)
            decision_count += 1

        assert decision_count > 10, f"决策模块调用次数过低: {decision_count}"

    def test_decision_with_extreme_history(self) -> None:
        """决策历史被撑满后仍可正常工作"""
        agent = SelfEvolvingAgent()
        decision = agent.phase_two.decision
        max_history = decision.max_history
        for i in range(max_history + 50):
            decision.decision_history.append({"loop": i, "choice": "explore"})
        decision.decision_history = decision.decision_history[-max_history:]

        phase1 = agent.phase_one.step()
        result = agent.phase_two.step(phase1, 1, 0.0, 0.0)
        assert "decision" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
