"""实用任务模板

提供可直接映射到 ActionExecutor 的任务模板，把抽象的 Gap 转化为
具体的、可执行的动作负载。
"""
from typing import Any, Dict, Final, List

from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class TaskTemplate:
    """任务模板"""

    def __init__(self, name: str, action_type: str, default_payload: Dict[str, Any]) -> None:
        self.name: str = name
        self.action_type: str = action_type
        self.default_payload: Final[Dict[str, Any]] = default_payload

    def build_payload(self, params: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(self.default_payload)
        payload.update(params)
        payload["action_type"] = self.action_type
        return payload


class TaskTemplateRegistry:
    """任务模板注册表"""

    TEMPLATES: Dict[str, TaskTemplate] = {
        "disk_cleanup": TaskTemplate(
            "disk_cleanup",
            "shell",
            {"command": "df -h", "description": "检查磁盘使用情况"},
        ),
        "send_alert": TaskTemplate(
            "send_alert",
            "http_post",
            {"url": "http://localhost:8080/alert", "body": '{"message": "agent alert"}'},
        ),
        "restart_service": TaskTemplate(
            "restart_service",
            "shell",
            {"command": "echo restart service", "description": "重启服务（默认dry_run）"},
        ),
        "adjust_config": TaskTemplate(
            "adjust_config",
            "file_write",
            {"path": "/tmp/agent_config_adjustment.log", "content": "config adjusted"},
        ),
        "health_check": TaskTemplate(
            "health_check",
            "http_get",
            {"url": "http://localhost:8080/health"},
        ),
        "log_scan": TaskTemplate(
            "log_scan",
            "shell",
            {"command": "echo scan logs", "description": "扫描日志异常"},
        ),
    }

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self._templates: Dict[str, TaskTemplate] = dict(self.TEMPLATES)
        self._register_custom()
        logger.info(f"TaskTemplateRegistry initialized with {len(self._templates)} templates", "template")

    def _register_custom(self) -> None:
        custom = self.config.get("custom_templates", {})
        for name, spec in custom.items():
            action_type = spec.get("action_type", "noop")
            default_payload = dict(spec.get("default_payload", {}))
            self._templates[name] = TaskTemplate(name, action_type, default_payload)

    def get_template(self, name: str) -> TaskTemplate:
        if name not in self._templates:
            raise KeyError(f"Task template not found: {name}")
        return self._templates[name]

    def build_payload(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        template = self.get_template(name)
        return template.build_payload(params)

    def list_templates(self) -> List[str]:
        return sorted(self._templates.keys())

    def get_state(self) -> Dict[str, Any]:
        """获取任务模板注册表状态"""
        return {
            "template_count": len(self._templates),
            "templates": self.list_templates(),
        }

    def reset(self) -> None:
        """重置任务模板注册表"""
        logger.debug("[TaskTemplateRegistry.reset] called", "template")
        self._templates = dict(self.TEMPLATES)
        self._register_custom()

    def health_check(self) -> bool:
        """健康检查"""
        logger.debug("[TaskTemplateRegistry.health_check] called", "template")
        return len(self._templates) > 0
