"""部署服务器测试"""
import json
import socket
import time
from typing import Any, Dict

import pytest

from root.left.app.left.src.deploy_server import DeployServer


class DummyAgent:
    """模拟Agent"""

    def __init__(self) -> None:
        self.running = True
        self.loop_count = 42

    def get_state(self) -> Dict[str, Any]:
        return {"running": self.running, "loop_count": self.loop_count}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class TestDeployServer:
    """DeployServer 测试"""

    def test_init_normal(self) -> None:
        port = _free_port()
        server = DeployServer(port=port)
        assert server.port == port
        assert server.server is None

    def test_start_stop(self) -> None:
        agent = DummyAgent()
        port = _free_port()
        server = DeployServer(port=port)
        server.start(agent)
        assert server.server is not None
        assert server.thread is not None
        assert server.thread.is_alive()
        server.stop()
        time.sleep(0.3)
        assert server.server is None
        assert server.thread is None

    def test_stop_closes_socket(self) -> None:
        agent = DummyAgent()
        port = _free_port()
        server = DeployServer(port=port)
        server.start(agent)
        time.sleep(0.2)
        try:
            assert server.server is not None
            socket_fd = server.server.socket.fileno()
            server.stop()
            time.sleep(0.2)
            assert server.server is None
            with pytest.raises(OSError):
                import os
                os.fstat(socket_fd)
        finally:
            server.stop()
            time.sleep(0.2)

    def test_health_endpoint(self) -> None:
        agent = DummyAgent()
        port = _free_port()
        server = DeployServer(port=port)
        server.start(agent)
        time.sleep(0.2)
        try:
            import urllib.request
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health") as req:
                body = json.loads(req.read().decode())
            assert body["status"] == "healthy"
            assert body["loop_count"] == 42
        finally:
            server.stop()
            time.sleep(0.2)

    def test_metrics_endpoint(self) -> None:
        agent = DummyAgent()
        port = _free_port()
        server = DeployServer(port=port)
        server.start(agent)
        time.sleep(0.2)
        try:
            import urllib.request
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics") as req:
                body = json.loads(req.read().decode())
            assert body["running"] is True
            assert body["loop_count"] == 42
        finally:
            server.stop()
            time.sleep(0.2)

    def test_state_endpoint(self) -> None:
        agent = DummyAgent()
        port = _free_port()
        server = DeployServer(port=port)
        server.start(agent)
        time.sleep(0.2)
        try:
            import urllib.request
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/state") as req:
                body = json.loads(req.read().decode())
            assert body["loop_count"] == 42
        finally:
            server.stop()
            time.sleep(0.2)

    def test_summary_endpoint(self) -> None:
        agent = DummyAgent()
        port = _free_port()
        server = DeployServer(port=port)
        server.start(agent)
        time.sleep(0.2)
        try:
            import urllib.request
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/summary") as req:
                body = json.loads(req.read().decode())
            assert body["running"] is True
            assert body["loop_count"] == 42
        finally:
            server.stop()
            time.sleep(0.2)

    def test_404_endpoint(self) -> None:
        agent = DummyAgent()
        port = _free_port()
        server = DeployServer(port=port)
        server.start(agent)
        time.sleep(0.2)
        try:
            import urllib.request
            import urllib.error
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/unknown")
            response = exc_info.value
            try:
                assert response.code == 404
                body = json.loads(response.read().decode())
                assert body["error"] == "not found"
            finally:
                response.close()
        finally:
            server.stop()
            time.sleep(0.2)

    def test_health_unhealthy(self) -> None:
        agent = DummyAgent()
        agent.running = False
        port = _free_port()
        server = DeployServer(port=port)
        server.start(agent)
        time.sleep(0.2)
        try:
            import urllib.request
            import urllib.error
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/health")
                assert False, "should raise 503"
            except urllib.error.HTTPError as e:
                try:
                    assert e.code == 503
                    body = json.loads(e.read().decode())
                    assert body["status"] == "unhealthy"
                finally:
                    e.close()
        finally:
            server.stop()
            time.sleep(0.2)
