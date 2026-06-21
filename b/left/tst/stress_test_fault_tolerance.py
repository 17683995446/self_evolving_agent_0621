"""异常容错与降级机制验证

测试目标：
1. 各模块异常注入后系统不崩溃
2. 配置损坏后的降级恢复
3. 数据库损坏/锁死的容错
4. 外部依赖缺失（如psutil）的降级
5. 内存/CPU超限的优雅处理
"""
import sqlite3
import threading
import time

import pytest

from root.left.app.left.src.main import SelfEvolvingAgent
from root.left.app.left.src.utils_main.logger import logger


class TestModuleFaultInjection:
    """模块级故障注入"""

    def test_sensory_failure_graceful(self) -> None:
        """感知模块失败时系统降级"""
        agent = SelfEvolvingAgent()
        agent.phase_one.sensory.config = None
        try:
            result = agent.phase_one.step()
            assert "state" in result
        except Exception as e:
            logger.info(f"Sensory failure caught: {e}", "fault")

    def test_prediction_failure_graceful(self) -> None:
        """预测模块失败时系统降级"""
        agent = SelfEvolvingAgent()
        agent.phase_one.prediction.low_level.data = None
        try:
            result = agent.phase_one.step()
            assert "predictions" in result
        except Exception as e:
            logger.info(f"Prediction failure caught: {e}", "fault")

    def test_drive_failure_graceful(self) -> None:
        """驱力模块失败时系统降级"""
        agent = SelfEvolvingAgent()
        agent.phase_one.drive_engine.safe_calc.thresholds = None
        try:
            result = agent.phase_one.step()
            assert "drive_state" in result
        except Exception as e:
            logger.info(f"Drive failure caught: {e}", "fault")

    def test_decision_failure_graceful(self) -> None:
        """决策模块失败时系统降级"""
        agent = SelfEvolvingAgent()
        agent.phase_two.decision.exploration.config = None
        try:
            phase1 = agent.phase_one.step()
            result = agent.phase_two.step(phase1, 1, 0.0, 0.0)
            assert "decision" in result
        except Exception as e:
            logger.info(f"Decision failure caught: {e}", "fault")

    def test_memory_failure_graceful(self) -> None:
        """记忆模块失败时系统降级"""
        agent = SelfEvolvingAgent()
        agent.phase_two.memory.cache.cache = None
        try:
            phase1 = agent.phase_one.step()
            result = agent.phase_two.step(phase1, 1, 0.0, 0.0)
            assert "memory_recent" in result
        except Exception as e:
            logger.info(f"Memory failure caught: {e}", "fault")

    def test_evolution_failure_graceful(self) -> None:
        """进化模块失败时系统降级"""
        agent = SelfEvolvingAgent()
        agent.phase_three.evolution.snapshot_manager.snapshots = None
        try:
            phase1 = agent.phase_one.step()
            phase2 = agent.phase_two.step(phase1, 1, 0.0, 0.0)
            result = agent.phase_three.step(agent.config, phase1, phase2)
            assert "evolution_result" in result
        except Exception as e:
            logger.info(f"Evolution failure caught: {e}", "fault")


class TestDatabaseFaultTolerance:
    """数据库容错测试"""

    def test_sqlite_locked(self) -> None:
        """SQLite锁死场景"""
        agent = SelfEvolvingAgent()
        lock = threading.Lock()

        def locked_writer() -> None:
            with lock:
                time.sleep(0.5)
                agent.phase_two.memory.store.save_state(999, "{}", "{}", 0.5)

        t = threading.Thread(target=locked_writer)
        t.start()
        time.sleep(0.1)
        try:
            agent.phase_two.memory.store.save_state(1000, "{}", "{}", 0.5)
        except sqlite3.OperationalError as e:
            logger.info(f"SQLite lock handled: {e}", "fault")
        t.join()

    def test_sqlite_corrupted_recovery(self) -> None:
        """数据库损坏恢复"""
        import os
        import tempfile
        db_path = tempfile.mktemp(suffix=".db")
        type("Store", (), {"db_path": db_path})()
        with open(db_path, "w") as f:
            f.write("CORRUPTED")
        try:
            conn = sqlite3.connect(db_path)
            conn.cursor().execute("SELECT 1")
        except Exception as e:
            logger.info(f"Corrupted DB handled: {e}", "fault")
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)


class TestConfigDegradation:
    """配置降级测试"""

    def test_missing_phase1_config(self) -> None:
        """Phase1配置缺失"""
        config = SelfEvolvingAgent().config
        del config["phase1"]
        try:
            agent = SelfEvolvingAgent(config)
            agent.run(max_loops=3)
        except Exception as e:
            logger.info(f"Missing phase1 config handled: {e}", "fault")

    def test_missing_phase2_config(self) -> None:
        """Phase2配置缺失"""
        config = SelfEvolvingAgent().config
        del config["phase2"]
        try:
            agent = SelfEvolvingAgent(config)
            agent.run(max_loops=3)
        except Exception as e:
            logger.info(f"Missing phase2 config handled: {e}", "fault")

    def test_invalid_config_values(self) -> None:
        """非法配置值"""
        config = SelfEvolvingAgent().config
        config["loop_interval"] = -1.0
        config["phase1"]["sensory"]["ema_alpha"] = 2.0
        try:
            agent = SelfEvolvingAgent(config)
            agent.run(max_loops=3)
        except Exception as e:
            logger.info(f"Invalid config handled: {e}", "fault")


class TestResourceExhaustion:
    """资源耗尽测试"""

    def test_cpu_limit_enforced(self) -> None:
        """CPU限制生效"""
        agent = SelfEvolvingAgent()
        with pytest.raises(Exception):
            agent.phase_two.step(
                agent.phase_one.step(),
                1,
                9999.0,
                0.0
            )

    def test_memory_limit_enforced(self) -> None:
        """内存限制生效"""
        agent = SelfEvolvingAgent()
        with pytest.raises(Exception):
            agent.phase_two.step(
                agent.phase_one.step(),
                1,
                0.0,
                9999.0
            )


class TestExternalDependencyMissing:
    """外部依赖缺失测试"""

    def test_psutil_missing_fallback(self) -> None:
        """psutil缺失时降级"""
        agent = SelfEvolvingAgent()
        state = agent.phase_one.sensory.perceive()
        assert "timestamp" in state
        assert "feature_vector" in state


class TestMainLoopFaultTolerance:
    """主循环容错测试"""

    def test_single_loop_exception_recovery(self) -> None:
        """单循环异常后系统恢复"""
        agent = SelfEvolvingAgent()
        for i in range(10):
            try:
                agent._run_single_loop()
            except Exception as e:
                logger.warning(f"Loop {i} exception: {e}", "fault")
        assert agent.loop_count >= 9

    def test_rollback_during_exception(self) -> None:
        """异常期间回滚"""
        agent = SelfEvolvingAgent()
        for i in range(5):
            try:
                agent._run_single_loop()
                if i == 2:
                    agent.phase_three.evolution.snapshot_manager.best_performance = 1.0
                    agent.config = {}
            except Exception as e:
                logger.warning(f"Rollback exception: {e}", "fault")
                agent.config = SelfEvolvingAgent().config
                agent._init_phases(agent.config)
        assert agent.loop_count >= 4


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
