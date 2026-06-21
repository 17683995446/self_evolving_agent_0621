"""全局常量定义"""
from enum import Enum


class MetricType(Enum):
    SYSTEM = "system"
    LOG = "log"
    FILE = "file"
    SELF = "self"


class DriveType(Enum):
    SAFE = "safe"
    GAIN = "gain"
    EFF = "eff"


class TaskType(Enum):
    SAFE = "safe"
    GAIN = "gain"
    EFF = "eff"


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    FROZEN = "frozen"


class PredictionLevel(Enum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"


class ScenarioType(Enum):
    NORMAL = "normal"
    EMERGENCY = "emergency"
    STABLE_IDLE = "stable_idle"
    RESOURCE_TIGHT = "resource_tight"


class AdjustmentType(Enum):
    WEIGHT = "weight"
    LEARNING_RATE = "lr"
    THRESHOLD = "threshold"
    SMOOTHING = "smoothing"


class ErrorCode(Enum):
    SUCCESS = 0
    INVALID_PARAMETER = 1001
    MISSING_PARAMETER = 1002
    TYPE_MISMATCH = 1003
    OUT_OF_RANGE = 1004
    CONFIGURATION_ERROR = 2001
    MISSING_CONFIG_KEY = 2002
    SENSORY_ERROR = 3001
    DRIVE_ENGINE_ERROR = 4001
    PREDICTION_ERROR = 5001
    TASK_POOL_ERROR = 6001
    DECISION_ERROR = 7001
    MEMORY_ERROR = 8001
    EVOLUTION_ERROR = 9001
    RESOURCE_LIMIT_EXCEEDED = 10001
    SAFETY_BOUNDARY_VIOLATED = 11001
    COLLABORATION_ERROR = 12001
    EXTERNAL_INTEGRATION_ERROR = 13001
    MODULE_NOT_FOUND = 14001
