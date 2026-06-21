"""人工审批门

对破坏性动作进行审批控制，支持自动通过、自动拒绝、人工待定三种模式。
"""
import os
from typing import Any, Callable, Dict, Final, List, Optional

from root.left.app.left.src.utils_main.exceptions import SafetyBoundaryException
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class ApprovalGate:
    """审批门"""

    DESTRUCTIVE_ACTIONS: List[str] = ["file_delete", "restart_service", "rm", "shutdown", "reboot"]

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[ApprovalGate.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.mode: str = str(config.get("mode", "auto_pass"))
        self.destructive_actions: List[str] = list(config.get("destructive_actions", self.DESTRUCTIVE_ACTIONS))
        self.approval_file: str = str(config.get("approval_file", "/tmp/agent_approval.txt"))
        self._custom_handler: Optional[Callable[[str, Dict[str, Any]], bool]] = config.get("handler")
        logger.info(f"ApprovalGate initialized mode={self.mode}", "approval")

    def check(self, action_type: str, payload: Dict[str, Any]) -> bool:
        logger.debug(f"[ApprovalGate.check] action_type={action_type}", "approval")
        if not self._is_destructive(action_type, payload):
            logger.debug("[ApprovalGate.check] non-destructive -> True", "approval")
            return True
        logger.info(f"[ApprovalGate.check] destructive action needs approval: {action_type}", "approval")
        if self.mode == "auto_pass":
            return True
        if self.mode == "auto_reject":
            raise SafetyBoundaryException(
                "Destructive action rejected by policy",
                boundary="approval_gate",
                attempted_action=action_type,
            )
        if self.mode == "file_token":
            return self._check_approval_file(action_type, payload)
        if self.mode == "custom" and self._custom_handler:
            return self._custom_handler(action_type, payload)
        raise SafetyBoundaryException(
            "Destructive action pending approval",
            boundary="approval_gate",
            attempted_action=action_type,
        )

    def _is_destructive(self, action_type: str, payload: Dict[str, Any]) -> bool:
        if action_type in self.destructive_actions:
            return True
        if action_type == "shell":
            command = payload.get("command", "")
            lowered = command.lower()
            for keyword in ["rm -rf", "mkfs", "shutdown", "reboot", "kill -9"]:
                if keyword in lowered:
                    return True
        return False

    def _check_approval_file(self, action_type: str, payload: Dict[str, Any]) -> bool:
        if not os.path.isfile(self.approval_file):
            logger.warning(f"[ApprovalGate._check_approval_file] missing {self.approval_file}", "approval")
            raise SafetyBoundaryException(
                f"Approval file missing: {self.approval_file}",
                boundary="approval_gate",
                attempted_action=action_type,
            )
        with open(self.approval_file, "r", encoding="utf-8") as f:
            token = f.read().strip()
        expected = self._expected_token(action_type, payload)
        if token == expected or token == "ALL":
            logger.info("[ApprovalGate._check_approval_file] approved", "approval")
            return True
        raise SafetyBoundaryException(
            "Approval token mismatch",
            boundary="approval_gate",
            attempted_action=action_type,
        )

    def _expected_token(self, action_type: str, payload: Dict[str, Any]) -> str:
        target = payload.get("path", payload.get("command", ""))
        return f"{action_type}:{target}"

    def get_state(self) -> Dict[str, Any]:
        """获取审批门状态"""
        return {
            "mode": self.mode,
            "destructive_actions": self.destructive_actions,
            "approval_file": self.approval_file,
        }

    def reset(self) -> None:
        """重置审批门"""
        logger.debug("[ApprovalGate.reset] called", "approval")

    def health_check(self) -> bool:
        """健康检查"""
        logger.debug("[ApprovalGate.health_check] called", "approval")
        return self.mode in {"auto_pass", "auto_reject", "file_token", "custom"}
