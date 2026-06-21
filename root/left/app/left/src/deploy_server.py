"""部署服务器：HTTP健康检查、指标暴露与运行时控制"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional

from root.left.app.left.src.utils_main.logger import logger


class HealthHandler(BaseHTTPRequestHandler):
    """HTTP请求处理器"""

    agent_ref: Optional[Any] = None

    def log_message(self, format: str, *args: Any) -> None:
        logger.debug(f"[HTTP] {format % args}")

    def do_GET(self) -> None:
        logger.debug(f"[HealthHandler.do_GET] path={self.path}")
        if self.path == "/health":
            self._send_health()
        elif self.path == "/metrics":
            self._send_metrics()
        elif self.path == "/state":
            self._send_state()
        elif self.path == "/summary":
            self._send_summary()
        elif self.path == "/control/status":
            self._send_control_status()
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        logger.debug(f"[HealthHandler.do_POST] path={self.path}")
        if self.path == "/control/pause":
            self._handle_control_pause()
        elif self.path == "/control/resume":
            self._handle_control_resume()
        elif self.path == "/control/stop":
            self._handle_control_stop()
        elif self.path == "/control/reload":
            self._handle_control_reload()
        else:
            self._send_json(404, {"error": "not found"})

    def _send_health(self) -> None:
        agent = HealthHandler.agent_ref
        healthy = agent is not None and agent.running
        status = 200 if healthy else 503
        body = {
            "status": "healthy" if healthy else "unhealthy",
            "loop_count": getattr(agent, "loop_count", 0) if agent else 0,
        }
        self._send_json(status, body)

    def _send_metrics(self) -> None:
        agent = HealthHandler.agent_ref
        body: Dict[str, Any] = {
            "loop_count": getattr(agent, "loop_count", 0) if agent else 0,
            "running": getattr(agent, "running", False) if agent else False,
        }
        self._send_json(200, body)

    def _send_state(self) -> None:
        agent = HealthHandler.agent_ref
        if agent is None:
            self._send_json(503, {"error": "agent not initialized"})
            return
        try:
            state = agent.get_state() if hasattr(agent, "get_state") else {}
            self._send_json(200, state)
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _send_summary(self) -> None:
        agent = HealthHandler.agent_ref
        if agent is None:
            self._send_json(503, {"error": "agent not initialized"})
            return
        try:
            summary = {
                "running": getattr(agent, "running", False),
                "loop_count": getattr(agent, "loop_count", 0),
            }
            if hasattr(agent, "dashboard") and hasattr(agent, "phase_one"):
                dashboard = agent.dashboard
                phase1_result = agent.phase_one.step() if hasattr(agent.phase_one, "step") else {}
                state = phase1_result.get("state", {})
                drive_state = phase1_result.get("drive_state", {})
                report = dashboard.build_report(
                    state, drive_state, [], {}, {}, agent.loop_count
                )
                summary.update(dashboard.build_summary(report))
            self._send_json(200, summary)
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    # ------------------------------------------------------------------
    # 运行时控制端点
    # ------------------------------------------------------------------

    def _send_control_status(self) -> None:
        agent = HealthHandler.agent_ref
        if agent is None:
            self._send_json(503, {"error": "agent not initialized"})
            return
        try:
            status = agent.get_control_status() if hasattr(agent, "get_control_status") else {
                "running": getattr(agent, "running", False),
                "paused": False,
                "loop_count": getattr(agent, "loop_count", 0),
            }
            self._send_json(200, status)
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _handle_control_pause(self) -> None:
        agent = HealthHandler.agent_ref
        if agent is None:
            self._send_json(503, {"error": "agent not initialized"})
            return
        try:
            agent.pause()
            self._send_json(200, {"success": True, "message": "Agent 已暂停", "paused": True})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _handle_control_resume(self) -> None:
        agent = HealthHandler.agent_ref
        if agent is None:
            self._send_json(503, {"error": "agent not initialized"})
            return
        try:
            agent.resume()
            self._send_json(200, {"success": True, "message": "Agent 已恢复", "paused": False})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _handle_control_stop(self) -> None:
        agent = HealthHandler.agent_ref
        if agent is None:
            self._send_json(503, {"error": "agent not initialized"})
            return
        try:
            agent.stop()
            self._send_json(200, {"success": True, "message": "Agent 已停止", "running": False})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _handle_control_reload(self) -> None:
        agent = HealthHandler.agent_ref
        if agent is None:
            self._send_json(503, {"error": "agent not initialized"})
            return
        try:
            # 读取请求体获取 env 参数
            content_length = int(self.headers.get("Content-Length", 0))
            body_str = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            params = json.loads(body_str) if body_str else {}
            env = params.get("env", "dev")
            result = agent.reload_config(env) if hasattr(agent, "reload_config") else {
                "success": False, "message": "Agent 不支持配置热更新"
            }
            status_code = 200 if result.get("success") else 400
            self._send_json(status_code, result)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "请求体不是有效的 JSON"})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _send_json(self, status: int, body: Dict[str, Any]) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode("utf-8"))


class DeployServer:
    """部署HTTP服务器"""

    def __init__(self, port: int = 8080) -> None:
        logger.debug(f"[DeployServer.__init__] port={port}")
        self.port: int = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        logger.info(f"DeployServer initialized port={port}", "deploy")

    def start(self, agent: Any) -> None:
        logger.debug("[DeployServer.start] start")
        HealthHandler.agent_ref = agent
        self.server = HTTPServer(("0.0.0.0", self.port), HealthHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        logger.info(f"DeployServer started on port {self.port}", "deploy")

    def stop(self) -> None:
        logger.debug("[DeployServer.stop] start")
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            if self.thread is not None:
                self.thread.join(timeout=2.0)
            self.server = None
            self.thread = None
            logger.info("DeployServer stopped", "deploy")
