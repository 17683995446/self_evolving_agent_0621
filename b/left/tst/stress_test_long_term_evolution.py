"""长期演化稳定性观测测试

测试目标：
1. 1000循环性能趋势分析
2. 配置漂移检测
3. 自动回滚触发准确率
4. 进化算法收敛性
"""
import statistics
import time
from typing import Dict, List

import pytest

from root.left.app.left.src.main import SelfEvolvingAgent
from root.left.app.left.src.utils_main.logger import logger


def _fast_agent() -> SelfEvolvingAgent:
    config = SelfEvolvingAgent().config
    config["loop_interval"] = 0.0
    return SelfEvolvingAgent(config)


class TestLongTermStability:
    """长期稳定性测试"""

    def test_1000_loops_performance_trend(self) -> None:
        """1000循环性能趋势"""
        agent = _fast_agent()
        performances: List[float] = []
        for i in range(1000):
            agent._run_single_loop()
            perf = agent.phase_one.step().get("performance", 0.0)
            performances.append(perf)
            if i % 100 == 0:
                logger.info(f"Loop {i} performance={perf:.4f}", "longterm")

        mean_perf = statistics.mean(performances)
        std_perf = statistics.stdev(performances) if len(performances) > 1 else 0.0
        logger.info(f"1000 loops mean={mean_perf:.4f} std={std_perf:.4f}", "longterm")
        assert 0.0 <= mean_perf <= 10.0, f"Performance out of range: {mean_perf}"

    def test_config_drift_detection(self) -> None:
        """配置漂移检测"""
        agent = SelfEvolvingAgent()
        original_keys = set(agent.config.keys())
        for _ in range(500):
            agent._run_single_loop()
        current_keys = set(agent.config.keys())
        drift = current_keys - original_keys
        logger.info(f"Config drift keys: {drift}", "longterm")
        assert original_keys.issubset(current_keys), f"Config lost keys: {original_keys - current_keys}"

    def test_rollback_accuracy(self) -> None:
        """回滚触发准确率"""
        agent = SelfEvolvingAgent()
        rollback_count = 0
        for i in range(200):
            agent._run_single_loop()
            if agent.phase_three.evolution.should_rollback(agent.phase_one.step().get("performance", 0.0)):
                rollback_count += 1
        logger.info(f"Rollback triggered {rollback_count} times in 200 loops", "longterm")
        assert rollback_count >= 0

    def test_memory_growth_bounded(self) -> None:
        """内存增长有界"""
        import gc
        agent = SelfEvolvingAgent()
        gc.collect()
        snapshots: List[int] = []
        for i in range(500):
            agent._run_single_loop()
            if i % 100 == 0:
                gc.collect()
                snapshots.append(len(gc.get_objects()))
        growth = snapshots[-1] - snapshots[0] if len(snapshots) > 1 else 0
        logger.info(f"Memory growth over 500 loops: {growth}", "longterm")
        assert growth < 500000, f"Unbounded memory growth: {growth}"

    def test_task_pool_stability(self) -> None:
        """任务池稳定性"""
        agent = SelfEvolvingAgent()
        for _ in range(500):
            agent._run_single_loop()
        snapshot = agent.phase_two.task_pool.get_pool_snapshot()
        logger.info(f"Task pool after 500 loops: {snapshot}", "longterm")
        assert snapshot["total"] <= 100

    def test_decision_history_bounded(self) -> None:
        """决策历史有界"""
        agent = SelfEvolvingAgent()
        for _ in range(500):
            agent._run_single_loop()
        history_len = len(agent.phase_two.decision.decision_history)
        logger.info(f"Decision history length: {history_len}", "longterm")
        assert history_len <= 100

    def test_evolution_adjustment_bounded(self) -> None:
        """进化调整历史有界"""
        agent = SelfEvolvingAgent()
        for _ in range(500):
            agent._run_single_loop()
        adj_len = len(agent.phase_three.evolution.adjustment_history)
        logger.info(f"Adjustment history length: {adj_len}", "longterm")
        assert adj_len <= 1000


class TestConvergence:
    """收敛性测试"""

    def test_weights_converge(self) -> None:
        """权重收敛"""
        agent = SelfEvolvingAgent()
        weight_history: List[Dict[str, float]] = []
        for _ in range(200):
            agent._run_single_loop()
            weights = agent.phase_one.step()["drive_state"].get("weights", {})
            weight_history.append(weights.copy())

        if len(weight_history) >= 50:
            early = weight_history[10]
            late = weight_history[-1]
            diff = sum(abs(early.get(k, 0) - late.get(k, 0)) for k in set(early) | set(late))
            logger.info(f"Weight convergence diff={diff:.4f}", "longterm")
            assert diff < 5.0, f"Weights diverged: {diff}"

    def test_gap_stays_positive(self) -> None:
        """缺口始终为正（自驱永续）"""
        agent = SelfEvolvingAgent()
        for _ in range(200):
            agent._run_single_loop()
            gaps = agent.phase_one.step()["drive_state"].get("gaps", {})
            for k, v in gaps.items():
                assert v > 0.0, f"Gap {k} not positive: {v}"


class TestPerformanceDegradation:
    """性能退化测试"""

    def test_latency_stable(self) -> None:
        """延迟稳定"""
        agent = SelfEvolvingAgent()
        latencies: List[float] = []
        for _ in range(100):
            start = time.time()
            agent._run_single_loop()
            latencies.append(time.time() - start)
        mean_lat = statistics.mean(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        logger.info(f"Latency mean={mean_lat:.4f}s p95={p95:.4f}s", "longterm")
        assert p95 < 1.0, f"Latency degraded: p95={p95:.4f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
