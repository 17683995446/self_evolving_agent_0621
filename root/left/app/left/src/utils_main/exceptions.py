"""严格异常层次结构"""
from typing import Optional, Any, Dict

from root.left.app.left.src.utils_main.constants import ErrorCode


class AgentException(Exception):
    """Agent基础异常"""

    # 子类可覆盖：用户友好的修复建议
    user_suggestion: Optional[str] = None

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}
        self.module = "unknown"
        self.severity = "error"

    def format_for_user(self) -> str:
        """返回用户友好的错误描述，包含修复建议。"""
        parts = [f"[{self.module}] {self.args[0] if self.args else '未知错误'}"]
        if self.user_suggestion:
            parts.append(f"建议: {self.user_suggestion}")
        return "\n".join(parts)


class ConfigurationError(AgentException):
    """配置错误"""

    user_suggestion = "请检查配置文件格式与必填项，可运行 'python -m root.left.app.left.src.cli config --show-defaults' 查看默认配置。"

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        expected_type: Optional[str] = None,
        actual_value: Optional[Any] = None
    ) -> None:
        context = {
            "config_key": config_key,
            "expected_type": expected_type,
            "actual_value": actual_value,
        }
        super().__init__(message, ErrorCode.CONFIGURATION_ERROR, context)
        self.module = "config"


class ValidationError(AgentException):
    """数据验证错误"""

    user_suggestion = "请检查输入参数的类型与取值范围。"

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        expected_range: Optional[str] = None,
        actual_value: Optional[Any] = None
    ) -> None:
        context = {
            "field": field,
            "expected_range": expected_range,
            "actual_value": actual_value,
        }
        super().__init__(message, ErrorCode.INVALID_PARAMETER, context)
        self.module = "validation"


class SensoryException(AgentException):
    """感知模块异常"""

    user_suggestion = "请检查系统采集器是否正常运行，确认 psutil 已安装。"

    def __init__(
        self,
        message: str,
        collector: Optional[str] = None
    ) -> None:
        context = {"collector": collector}
        super().__init__(message, ErrorCode.SENSORY_ERROR, context)
        self.module = "sensory"


class DriveEngineException(AgentException):
    """驱力引擎异常"""

    user_suggestion = "请检查驱力权重配置是否合法（safe/gain/eff 权重之和应为 1.0）。"

    def __init__(
        self,
        message: str,
        drive_type: Optional[str] = None
    ) -> None:
        context = {"drive_type": drive_type}
        super().__init__(message, ErrorCode.DRIVE_ENGINE_ERROR, context)
        self.module = "drive_engine"


class PredictionException(AgentException):
    """预测模块异常"""

    user_suggestion = "请检查预测模块的历史数据是否充足，确认 EMA 参数在 [0,1] 范围内。"

    def __init__(
        self,
        message: str,
        level: Optional[str] = None,
        metric: Optional[str] = None
    ) -> None:
        context = {"level": level, "metric": metric}
        super().__init__(message, ErrorCode.PREDICTION_ERROR, context)
        self.module = "prediction"


class TaskPoolException(AgentException):
    """任务池异常"""

    user_suggestion = "请检查任务池容量配置，确认任务 ID 是否存在。"

    def __init__(
        self,
        message: str,
        task_id: Optional[str] = None
    ) -> None:
        context = {"task_id": task_id}
        super().__init__(message, ErrorCode.TASK_POOL_ERROR, context)
        self.module = "task_pool"


class DecisionException(AgentException):
    """决策模块异常"""

    user_suggestion = "请检查决策模块的探索率配置，确认任务池中有可选任务。"

    def __init__(
        self,
        message: str,
        task_count: Optional[int] = None
    ) -> None:
        context = {"task_count": task_count}
        super().__init__(message, ErrorCode.DECISION_ERROR, context)
        self.module = "decision"


class MemoryException(AgentException):
    """记忆模块异常"""

    user_suggestion = "请检查数据库路径是否可写，确认磁盘空间充足。"

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None
    ) -> None:
        context = {"operation": operation}
        super().__init__(message, ErrorCode.MEMORY_ERROR, context)
        self.module = "memory"


class EvolutionException(AgentException):
    """进化模块异常"""

    user_suggestion = "请检查进化模块的快照配置与回滚阈值。"

    def __init__(
        self,
        message: str,
        phase: Optional[str] = None
    ) -> None:
        context = {"phase": phase}
        super().__init__(message, ErrorCode.EVOLUTION_ERROR, context)
        self.module = "evolution"


class ResourceLimitException(AgentException):
    """资源限制异常"""

    user_suggestion = "Agent 资源使用超限，请降低循环频率或增加系统资源。"

    def __init__(
        self,
        message: str,
        resource_type: str,
        current_value: float,
        limit_value: float
    ) -> None:
        context = {
            "resource_type": resource_type,
            "current_value": current_value,
            "limit_value": limit_value,
        }
        super().__init__(message, ErrorCode.RESOURCE_LIMIT_EXCEEDED, context)
        self.module = "resource"
        self.severity = "critical"


class SafetyBoundaryException(AgentException):
    """安全边界异常"""

    user_suggestion = "Agent 尝试了超出安全边界的操作，已自动阻止。请检查安全策略配置。"

    def __init__(
        self,
        message: str,
        boundary: str,
        attempted_action: str
    ) -> None:
        context = {
            "boundary": boundary,
            "attempted_action": attempted_action,
        }
        super().__init__(message, ErrorCode.SAFETY_BOUNDARY_VIOLATED, context)
        self.module = "safety"
        self.severity = "critical"


class CollaborationException(AgentException):
    """协作模块异常"""

    user_suggestion = "请检查协作节点配置与网络连通性。"

    def __init__(
        self,
        message: str,
        peer_id: Optional[str] = None
    ) -> None:
        context = {"peer_id": peer_id}
        super().__init__(message, ErrorCode.COLLABORATION_ERROR, context)
        self.module = "collaboration"


class ExternalIntegrationException(AgentException):
    """外部集成异常"""

    user_suggestion = "请检查外部服务地址与连通性，确认 API 密钥是否有效。"

    def __init__(
        self,
        message: str,
        service: Optional[str] = None
    ) -> None:
        context = {"service": service}
        super().__init__(message, ErrorCode.EXTERNAL_INTEGRATION_ERROR, context)
        self.module = "external"


class ModuleNotFoundException(AgentException):
    """模块未找到异常"""

    user_suggestion = "请检查模块名称拼写，确认模块已正确注册。"

    def __init__(
        self,
        message: str,
        module_name: Optional[str] = None
    ) -> None:
        context = {"module_name": module_name}
        super().__init__(message, ErrorCode.MODULE_NOT_FOUND, context)
        self.module = "interfaces"
