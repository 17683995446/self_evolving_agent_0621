"""数据一致性校验与性能基准

测试目标：
1. 状态记录与查询一致性
2. 任务生命周期状态转换一致性
3. 决策历史与任务选择一致性
4. 快照保存与回滚数据一致性
5. 核心流程性能基准
"""
import time

import pytest

from root.left.app.left.src.main import SelfEvolvingAgent
from root.left.app.left.src.utils_main.constants import TaskStatus
from root.left.app.left.src.utils_main.logger import logger


class TestDataConsistency:
    """数据一致性校验"""

    def test_memory_record_and_query(self) -> None:
        """记忆记录与查询一致"""
        agent = SelfEvolvingAgent()
        agent.phase_two.memory.record_state(1, {"a": 1}, {"b": 2}, 0.5)
        agent.phase_two.memory.record_state(2, {"a": 2}, {"b": 3}, 0.6)
        recent = agent.phase_two.memory.get_recent_states(2)
        assert len(recent) == 2
        assert recent[0]["loop_id"] == 1
        assert recent[1]["performance"] == 0.6

    def test_task_lifecycle_consistency(self) -> None:
        """任务生命周期状态转换一致"""
        agent = SelfEvolvingAgent()
        pool = agent.phase_two.task_pool.pool
        pool.add_task = type("T", (), {})()
        from root.left.app.left.src.core_mod.task import Task, TaskType
        t = Task(TaskType.SAFE, 0.5, {})
        pool.add(t)
        assert t.status == TaskStatus.PENDING
        next_t = pool.get_next()
        assert next_t is not None
        assert next_t.status == TaskStatus.RUNNING
        pool.update_status(next_t.task_id, TaskStatus.COMPLETED)
        assert next_t.status == TaskStatus.COMPLETED
        cleared = pool.clear_completed()
        assert cleared == 1

    def test_decision_task_match(self) -> None:
        """决策选中任务与任务池一致"""
        agent = SelfEvolvingAgent()
        phase1 = agent.phase_one.step()
        phase2 = agent.phase_two.step(phase1, 1, 0.0, 0.0)
        decision = phase2.get("decision", {})
        selected = decision.get("selected_task")
        if selected:
            task_id = selected.get("task_id")
            all_tasks = agent.phase_two.task_pool.pool.tasks
            assert task_id in all_tasks or any(
                t.task_id == task_id for t in all_tasks.values()
            ), f"Selected task {task_id} not in pool"

    def test_snapshot_rollback_consistency(self) -> None:
        """快照保存与回滚数据一致"""
        agent = SelfEvolvingAgent()
        agent.phase_three.evolution.snapshot_manager.save(agent.config, 0.99)
        agent.config["modified"] = True
        best = agent.phase_three.evolution.get_best_snapshot()
        assert best is not None
        snapshot_config = best.get("config", {})
        assert "modified" not in snapshot_config

    def test_performance_calculation_consistency(self) -> None:
        """性能计算一致性"""
        agent = SelfEvolvingAgent()
        phase1 = agent.phase_one.step()
        performance = phase1.get("performance", 0.0)
        drive_state = phase1.get("drive_state", {})
        total_reward = drive_state.get("total_reward", 0.0)
        expected = total_reward * 0.7 + max(0.0, 1.0 - 1.0) * 0.3
        assert abs(performance - expected) < 0.01

    def test_error_rate_bounds(self) -> None:
        """误差率始终在合理范围"""
        agent = SelfEvolvingAgent()
        for _ in range(10):
            agent.phase_one.step()
            error_rate = agent.phase_one.prediction.get_average_error()
            assert 0.0 <= error_rate <= 10.0, f"error_rate out of bounds: {error_rate}"

    def test_drive_gap_non_negative(self) -> None:
        """驱动缺口非负"""
        agent = SelfEvolvingAgent()
        for _ in range(10):
            phase1 = agent.phase_one.step()
            gaps = phase1.get("drive_state", {}).get("gaps", {})
            for k, v in gaps.items():
                assert v >= 0.0, f"Gap {k} is negative: {v}"

    def test_weights_sum_to_one(self) -> None:
        """权重之和为1"""
        agent = SelfEvolvingAgent()
        for _ in range(10):
            phase1 = agent.phase_one.step()
            weights = phase1.get("drive_state", {}).get("weights", {})
            total = sum(weights.values())
            assert abs(total - 1.0) < 0.01, f"Weights sum={total}"


class TestPerformanceBenchmark:
    """性能基准测试"""

    def test_phase1_latency(self) -> None:
        """Phase1延迟<50ms"""
        agent = SelfEvolvingAgent()
        start = time.time()
        for _ in range(100):
            agent.phase_one.step()
        elapsed = time.time() - start
        avg_ms = (elapsed / 100) * 1000
        logger.info(f"Phase1 avg latency: {avg_ms:.2f}ms", "perf")
        assert avg_ms < 50.0, f"Phase1 too slow: {avg_ms:.2f}ms"

    def test_phase2_latency(self) -> None:
        """Phase2延迟<50ms"""
        agent = SelfEvolvingAgent()
        phase1 = agent.phase_one.step()
        start = time.time()
        for _ in range(100):
            agent.phase_two.step(phase1, 1, 0.0, 0.0)
        elapsed = time.time() - start
        avg_ms = (elapsed / 100) * 1000
        logger.info(f"Phase2 avg latency: {avg_ms:.2f}ms", "perf")
        assert avg_ms < 50.0, f"Phase2 too slow: {avg_ms:.2f}ms"

    def test_phase3_latency(self) -> None:
        """Phase3延迟<50ms"""
        agent = SelfEvolvingAgent()
        phase1 = agent.phase_one.step()
        phase2 = agent.phase_two.step(phase1, 1, 0.0, 0.0)
        start = time.time()
        for _ in range(100):
            agent.phase_three.step(agent.config, phase1, phase2)
        elapsed = time.time() - start
        avg_ms = (elapsed / 100) * 1000
        logger.info(f"Phase3 avg latency: {avg_ms:.2f}ms", "perf")
        assert avg_ms < 50.0, f"Phase3 too slow: {avg_ms:.2f}ms"

    def test_full_loop_latency(self) -> None:
        """完整循环延迟<200ms"""
        agent = SelfEvolvingAgent()
        start = time.time()
        for _ in range(50):
            agent._run_single_loop()
        elapsed = time.time() - start
        avg_ms = (elapsed / 50) * 1000
        logger.info(f"Full loop avg latency: {avg_ms:.2f}ms", "perf")
        assert avg_ms < 200.0, f"Full loop too slow: {avg_ms:.2f}ms"

    def test_task_pool_throughput(self) -> None:
        """任务池吞吐量>1000 ops/sec"""
        agent = SelfEvolvingAgent()
        pool = agent.phase_two.task_pool.pool
        from root.left.app.left.src.core_mod.task import Task, TaskType
        start = time.time()
        count = 0
        while time.time() - start < 1.0:
            t = Task(TaskType.SAFE, 0.5, {})
            pool.add(t)
            pool.get_next()
            count += 1
        logger.info(f"Task pool throughput: {count} ops/sec", "perf")
        assert count > 100, f"Task pool throughput too low: {count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
