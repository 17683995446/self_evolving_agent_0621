"""生产部署入口测试"""
import signal
import socket
import time
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from root.left.app.left.src.main_deploy import ProductionAgent, main


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture
def disable_signals() -> Generator[None, None, None]:
    with patch.object(signal, "signal", return_value=None):
        yield


@pytest.fixture
def fast_sleep() -> Generator[None, None, None]:
    with patch.object(time, "sleep", return_value=None):
        yield


class TestProductionAgent:
    """ProductionAgent 测试"""

    def test_init_default_config(self, disable_signals: None) -> None:
        agent = ProductionAgent()
        try:
            assert agent.config is not None
            assert agent.loop_count == 0
            assert agent.running is False
            assert agent.server is None
        finally:
            agent.close()

    def test_init_custom_config(self, disable_signals: None) -> None:
        base = ProductionAgent().config
        base["loop_interval"] = 0.0
        agent = ProductionAgent(base)
        try:
            assert agent.config == base
        finally:
            agent.close()

    def test_signal_handler(self, disable_signals: None) -> None:
        agent = ProductionAgent()
        try:
            agent.running = True
            agent._handle_signal(signal.SIGTERM, None)
            assert agent.running is False
        finally:
            agent.close()

    def test_start_server_disabled(self, disable_signals: None) -> None:
        config = ProductionAgent().config
        config["health_check"] = {"enabled": False}
        agent = ProductionAgent(config)
        try:
            agent.start_server()
            assert agent.server is None
        finally:
            agent.close()

    def test_start_server_enabled(self, disable_signals: None) -> None:
        port = _free_port()
        config = ProductionAgent().config
        config["health_check"] = {"enabled": True, "port": port}
        agent = ProductionAgent(config)
        try:
            agent.start_server()
            assert agent.server is not None
            assert agent.server.thread is not None
            assert agent.server.thread.is_alive()
        finally:
            agent.stop()
            agent.close()
            time.sleep(0.2)

    def test_should_stop_none(self, disable_signals: None) -> None:
        agent = ProductionAgent()
        try:
            assert agent._should_stop(None) is False
        finally:
            agent.close()

    def test_should_stop_reached(self, disable_signals: None) -> None:
        agent = ProductionAgent()
        try:
            agent.loop_count = 5
            assert agent._should_stop(5) is True
        finally:
            agent.close()

    def test_run_single_loop(self, disable_signals: None) -> None:
        agent = ProductionAgent()
        try:
            agent._run_single_loop()
            assert agent.loop_count == 1
        finally:
            agent.close()

    def test_execute_selected_task(self, disable_signals: None) -> None:
        agent = ProductionAgent()
        try:
            phase2 = agent.phase_two.step(agent.phase_one.step(), 1, 0.0, 0.0)
            agent._execute_selected_task(phase2)
        finally:
            agent.close()

    def test_handle_rollback(self, disable_signals: None) -> None:
        agent = ProductionAgent()
        try:
            original_config = agent.config.copy()
            modified_config = agent.config.copy()
            modified_config["rollback_marker"] = True
            agent.phase_three.evolution.snapshot_manager.save(modified_config, 0.99)
            result = {
                "should_rollback": True,
                "best_snapshot": agent.phase_three.evolution.get_best_snapshot(),
            }
            agent._handle_rollback(result)
            assert agent.config.get("rollback_marker") is True
            assert "rollback_marker" not in original_config
        finally:
            agent.close()

    def test_handle_rollback_no_snapshot(self, disable_signals: None) -> None:
        agent = ProductionAgent()
        try:
            result = {"should_rollback": True, "best_snapshot": None}
            agent._handle_rollback(result)
        finally:
            agent.close()

    def test_stop(self, disable_signals: None) -> None:
        agent = ProductionAgent()
        try:
            agent.running = True
            agent.stop()
            assert agent.running is False
        finally:
            agent.close()

    def test_get_state(self, disable_signals: None) -> None:
        agent = ProductionAgent()
        try:
            state = agent.get_state()
            assert "running" in state
            assert "loop_count" in state
            assert "config" in state
        finally:
            agent.close()

    def test_close_stops_server_and_modules(self, disable_signals: None) -> None:
        port = _free_port()
        config = ProductionAgent().config
        config["health_check"] = {"enabled": True, "port": port}
        agent = ProductionAgent(config)
        try:
            agent.start_server()
            assert agent.server is not None
            agent.close()
            assert agent.server is None
            assert agent.running is False
        finally:
            agent.close()

    def test_close_is_idempotent(self, disable_signals: None) -> None:
        agent = ProductionAgent()
        agent.close()
        agent.close()

    def test_run_with_max_loops(self, disable_signals: None, fast_sleep: None) -> None:
        config = ProductionAgent().config
        config["loop_interval"] = 0.0
        config["max_loops"] = 3
        agent = ProductionAgent(config)
        try:
            agent.run(max_loops=3)
            assert agent.loop_count == 3
            assert agent.running is False
        finally:
            agent.close()

    def test_run_stop_after_start(self, disable_signals: None, fast_sleep: None) -> None:
        config = ProductionAgent().config
        config["loop_interval"] = 0.0
        agent = ProductionAgent(config)
        try:
            def stop_after_one() -> None:
                while agent.loop_count < 1:
                    time.sleep(0.01)
                agent.stop()

            import threading
            t = threading.Thread(target=stop_after_one)
            t.start()
            agent.run()
            t.join()
            assert agent.loop_count >= 1
        finally:
            agent.close()


class TestMainEntry:
    """main() 入口测试"""

    def test_main_zero_max_loops(self, disable_signals: None, fast_sleep: None) -> None:
        with patch.dict("os.environ", {"AGENT_ENV": "test"}):
            with patch("root.left.app.left.src.main_deploy.ProductionAgent") as mock_cls:
                instance = MagicMock()
                instance.config = {"max_loops": 0}
                instance.run = MagicMock()
                mock_cls.return_value = instance
                main()
                instance.run.assert_called_once()

    def test_main_agent_exception(self, disable_signals: None, fast_sleep: None) -> None:
        from root.left.app.left.src.utils_main.exceptions import AgentException
        from root.left.app.left.src.utils_main.constants import ErrorCode
        with patch.dict("os.environ", {"AGENT_ENV": "test"}):
            with patch("root.left.app.left.src.main_deploy.ProductionAgent") as mock_cls:
                instance = MagicMock()
                instance.config = {"max_loops": 0}
                instance.run.side_effect = AgentException("boom", ErrorCode.CONFIGURATION_ERROR)
                mock_cls.return_value = instance
                with pytest.raises(SystemExit) as exc:
                    main()
                assert exc.value.code == 1

    def test_main_unexpected_exception(self, disable_signals: None, fast_sleep: None) -> None:
        with patch.dict("os.environ", {"AGENT_ENV": "test"}):
            with patch("root.left.app.left.src.main_deploy.ProductionAgent") as mock_cls:
                instance = MagicMock()
                instance.config = {"max_loops": 0}
                instance.run.side_effect = RuntimeError("boom")
                mock_cls.return_value = instance
                with pytest.raises(SystemExit) as exc:
                    main()
                assert exc.value.code == 1
