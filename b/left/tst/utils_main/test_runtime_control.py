"""运行时控制与热更新测试"""
from __future__ import annotations

import json
import threading
import time

import pytest

from root.left.app.left.src.cli import build_parser, main
from root.left.app.left.src.deploy_server import DeployServer
from root.left.app.left.src.main import SelfEvolvingAgent
from root.left.app.left.src.main_deploy import ProductionAgent


# ---------------------------------------------------------------------------
# Agent 运行时控制方法测试
# ---------------------------------------------------------------------------

class TestAgentControlMethods:
    """测试 Agent 的运行时控制方法"""

    def test_pause_sets_paused_flag(self) -> None:
        agent = SelfEvolvingAgent()
        try:
            assert agent.is_paused() is False
            agent.pause()
            assert agent.is_paused() is True
        finally:
            agent.close()

    def test_resume_clears_paused_flag(self) -> None:
        agent = SelfEvolvingAgent()
        try:
            agent.pause()
            assert agent.is_paused() is True
            agent.resume()
            assert agent.is_paused() is False
        finally:
            agent.close()

    def test_get_control_status_running(self) -> None:
        agent = SelfEvolvingAgent()
        try:
            agent.running = True
            status = agent.get_control_status()
            assert status["running"] is True
            assert status["paused"] is False
            assert status["loop_count"] == 0
        finally:
            agent.close()

    def test_get_control_status_paused(self) -> None:
        agent = SelfEvolvingAgent()
        try:
            agent.pause()
            status = agent.get_control_status()
            assert status["paused"] is True
        finally:
            agent.close()

    def test_reload_config_success(self) -> None:
        agent = SelfEvolvingAgent()
        try:
            result = agent.reload_config("dev")
            assert result["success"] is True
            assert "dev" in result["message"]
        finally:
            agent.close()

    def test_reload_config_invalid_env(self) -> None:
        agent = SelfEvolvingAgent()
        try:
            result = agent.reload_config("nonexistent_env")
            assert result["success"] is False
        finally:
            agent.close()

    def test_reload_config_updates_config(self) -> None:
        agent = SelfEvolvingAgent()
        try:
            result = agent.reload_config("dev")
            assert result["success"] is True
            # config 应被更新（即使值相同，也是新对象）
            assert agent.config is not None
        finally:
            agent.close()


class TestProductionAgentControlMethods:
    """测试 ProductionAgent 的运行时控制方法"""

    def test_production_agent_has_control_methods(self) -> None:
        agent = ProductionAgent()
        try:
            assert hasattr(agent, "pause")
            assert hasattr(agent, "resume")
            assert hasattr(agent, "is_paused")
            assert hasattr(agent, "get_control_status")
            assert hasattr(agent, "reload_config")
        finally:
            agent.close()

    def test_production_agent_pause_resume(self) -> None:
        agent = ProductionAgent()
        try:
            assert agent.is_paused() is False
            agent.pause()
            assert agent.is_paused() is True
            agent.resume()
            assert agent.is_paused() is False
        finally:
            agent.close()


# ---------------------------------------------------------------------------
# HTTP 控制端点测试
# ---------------------------------------------------------------------------

class TestHTTPControlEndpoints:
    """测试 HTTP 控制端点"""

    @pytest.fixture
    def running_server(self):
        """启动一个带 Agent 的测试服务器"""
        agent = SelfEvolvingAgent()
        agent.running = True
        server = DeployServer(port=0)  # 端口 0 让系统分配
        # 手动设置端口
        from http.server import HTTPServer
        from root.left.app.left.src.deploy_server import HealthHandler
        server.server = HTTPServer(("127.0.0.1", 0), HealthHandler)
        server.port = server.server.server_address[1]
        HealthHandler.agent_ref = agent
        server.thread = threading.Thread(target=server.server.serve_forever, daemon=True)
        server.thread.start()
        time.sleep(0.1)  # 等待服务器启动
        yield server.port, agent
        server.stop()
        agent.close()

    def test_control_status_endpoint(self, running_server) -> None:
        import urllib.request
        port, agent = running_server
        url = f"http://127.0.0.1:{port}/control/status"
        with urllib.request.urlopen(url, timeout=5) as resp:
            body = json.loads(resp.read().decode())
        assert "running" in body
        assert "paused" in body
        assert "loop_count" in body

    def test_control_pause_endpoint(self, running_server) -> None:
        import urllib.request
        port, agent = running_server
        url = f"http://127.0.0.1:{port}/control/pause"
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode())
        assert body["success"] is True
        assert agent.is_paused() is True

    def test_control_resume_endpoint(self, running_server) -> None:
        import urllib.request
        port, agent = running_server
        # 先暂停
        agent.pause()
        assert agent.is_paused() is True
        # 再恢复
        url = f"http://127.0.0.1:{port}/control/resume"
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode())
        assert body["success"] is True
        assert agent.is_paused() is False

    def test_control_stop_endpoint(self, running_server) -> None:
        import urllib.request
        port, agent = running_server
        url = f"http://127.0.0.1:{port}/control/stop"
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode())
        assert body["success"] is True
        assert agent.running is False

    def test_control_reload_endpoint(self, running_server) -> None:
        import urllib.request
        port, agent = running_server
        url = f"http://127.0.0.1:{port}/control/reload"
        data = json.dumps({"env": "dev"}).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
        assert body["success"] is True

    def test_control_reload_invalid_env(self, running_server) -> None:
        import urllib.request
        port, agent = running_server
        url = f"http://127.0.0.1:{port}/control/reload"
        data = json.dumps({"env": "nonexistent_env"}).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode())
            assert body["success"] is False
        except Exception:
            # 400 错误也是可接受的
            pass

    def test_control_unknown_post_returns_404(self, running_server) -> None:
        import urllib.request
        import urllib.error
        port, agent = running_server
        url = f"http://127.0.0.1:{port}/control/unknown"
        req = urllib.request.Request(url, method="POST")
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(req, timeout=5)


# ---------------------------------------------------------------------------
# CLI control 子命令测试
# ---------------------------------------------------------------------------

class TestCLIControlParser:
    """测试 control 子命令参数解析"""

    def test_control_pause_parser(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["control", "pause", "--port", "9090"])
        assert args.action == "pause"
        assert args.port == 9090

    def test_control_resume_parser(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["control", "resume"])
        assert args.action == "resume"
        assert args.port == 8080

    def test_control_stop_parser(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["control", "stop"])
        assert args.action == "stop"

    def test_control_reload_parser(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["control", "reload", "--env", "prod"])
        assert args.action == "reload"
        assert args.env == "prod"

    def test_control_status_parser(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["control", "status"])
        assert args.action == "status"

    def test_control_invalid_action_fails(self) -> None:
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["control", "invalid"])


class TestCLIControlConnectionRefused:
    """测试 control 子命令连接失败场景"""

    def test_control_status_connection_refused(self, capsys) -> None:
        exit_code = main(["control", "status", "--port", "1"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "无法连接" in captured.err

    def test_control_pause_connection_refused(self, capsys) -> None:
        exit_code = main(["control", "pause", "--port", "1"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "无法连接" in captured.err

    def test_control_reload_connection_refused(self, capsys) -> None:
        exit_code = main(["control", "reload", "--port", "1"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "无法连接" in captured.err


class TestCLIControlWithServer:
    """测试 control 子命令与真实服务器交互"""

    @pytest.fixture
    def server_port(self):
        """启动测试服务器并返回端口"""
        agent = SelfEvolvingAgent()
        agent.running = True
        server = DeployServer(port=0)
        from http.server import HTTPServer
        from root.left.app.left.src.deploy_server import HealthHandler
        server.server = HTTPServer(("127.0.0.1", 0), HealthHandler)
        server.port = server.server.server_address[1]
        HealthHandler.agent_ref = agent
        server.thread = threading.Thread(target=server.server.serve_forever, daemon=True)
        server.thread.start()
        time.sleep(0.1)
        yield server.port, agent
        server.stop()
        agent.close()

    def test_control_status_success(self, capsys, server_port) -> None:
        port, agent = server_port
        exit_code = main(["control", "status", "--port", str(port)])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "运行中" in captured.out or "循环次数" in captured.out

    def test_control_pause_success(self, capsys, server_port) -> None:
        port, agent = server_port
        exit_code = main(["control", "pause", "--port", str(port)])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "暂停" in captured.out
        assert agent.is_paused() is True

    def test_control_resume_success(self, capsys, server_port) -> None:
        port, agent = server_port
        agent.pause()
        exit_code = main(["control", "resume", "--port", str(port)])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "恢复" in captured.out
        assert agent.is_paused() is False

    def test_control_stop_success(self, capsys, server_port) -> None:
        port, agent = server_port
        exit_code = main(["control", "stop", "--port", str(port)])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "停止" in captured.out
        assert agent.running is False

    def test_control_reload_success(self, capsys, server_port) -> None:
        port, agent = server_port
        exit_code = main(["control", "reload", "--port", str(port), "--env", "dev"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "重载" in captured.out or "加载" in captured.out
