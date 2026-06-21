"""配置加载器

提供默认配置、文件加载、环境变量覆盖与安全取值。
"""
import os
from typing import Any, Dict, List, Optional

import yaml

from root.left.app.left.src.utils_main.exceptions import ConfigurationError


DEFAULT_CONFIG: Dict[str, Any] = {
    "phase1": {
        "sensory": {
            "collectors": {
                "system": {"enabled": True, "interval": 1.0, "history_size": 1000}
            },
            "normalizer": {"feature_order": ["cpu_percent", "memory_percent"]},
            "noise_filter": {"ema_alpha": 0.3},
        },
        "drive": {
            "safe": {
                "risk_weights": {"cpu_high": 0.2, "memory_high": 0.3},
                "thresholds": {"cpu_critical": 80.0, "memory_critical": 85.0},
            },
            "gain": {"error_history_size": 100},
            "eff": {"agent_cpu_limit": 20.0, "agent_memory_limit": 20.0},
            "weights": {
                "safe_weight": 0.4,
                "gain_weight": 0.4,
                "eff_weight": 0.2,
                "weight_smooth_alpha": 0.3,
            },
        },
        "prediction": {
            "low": {"ema_alpha": 0.3, "trend_beta": 0.1, "horizon": 1},
            "mid": {"window_size": 10, "horizon": 3},
            "high": {"n_clusters": 5, "horizon": 10},
            "anomaly_threshold": 3.0,
        },
        "adjustment": {"enabled": True},
    },
    "phase2": {
        "task_pool": {
            "pool": {"max_size": 100},
            "safe_gen": {"enabled": True},
            "gain_gen": {"enabled": True},
            "eff_gen": {"enabled": True},
        },
        "decision": {
            "exploration": {
                "base_exploration_ratio": 0.3,
                "min_exploration_ratio": 0.1,
                "max_exploration_ratio": 0.5,
            },
            "task_selector": {"strategy": "priority"},
            "resource_balancer": {"cpu_limit": 20.0, "memory_limit": 20.0},
        },
        "memory": {
            "cache": {"max_cache_size": 1000},
            "store": {"db_path": "agent_memory.db"},
        },
    },
    "phase3": {
        "evolution": {
            "snapshot": {"max_snapshots": 5},
            "refactor": {"error_threshold": 0.3, "stagnation_rounds": 100},
            "feature": {"enabled": True},
            "review": {"enabled": True},
            "gap_threshold": 0.1,
            "rollback_threshold": 0.1,
        }
    },
    "loop_interval": 1.0,
    "max_loops": 1000,
    "log_level": "INFO",
    "health_check": {"enabled": False, "port": 8080},
    "action_executor": {"dry_run": True, "timeout": 30.0},
    "effect_verifier": {"max_points": 10},
    "recommendation": {},
    "dashboard": {},
}


# 配置项描述表：路径 -> (类型, 说明)
CONFIG_DESCRIPTIONS: Dict[str, tuple] = {
    "phase1.sensory.collectors.system.enabled": ("bool", "是否启用系统指标采集器"),
    "phase1.sensory.collectors.system.interval": ("float", "采集间隔（秒）"),
    "phase1.sensory.collectors.system.history_size": ("int", "历史数据保留条数"),
    "phase1.sensory.noise_filter.ema_alpha": ("float", "指数移动平均平滑系数 [0,1]"),
    "phase1.drive.safe.risk_weights.cpu_high": ("float", "CPU 高负载风险权重"),
    "phase1.drive.safe.risk_weights.memory_high": ("float", "内存高负载风险权重"),
    "phase1.drive.safe.thresholds.cpu_critical": ("float", "CPU 危险阈值 (%)"),
    "phase1.drive.safe.thresholds.memory_critical": ("float", "内存危险阈值 (%)"),
    "phase1.drive.weights.safe_weight": ("float", "安全驱力权重"),
    "phase1.drive.weights.gain_weight": ("float", "收益驱力权重"),
    "phase1.drive.weights.eff_weight": ("float", "效率驱力权重"),
    "phase1.prediction.low.ema_alpha": ("float", "低层预测 EMA 系数"),
    "phase1.prediction.mid.window_size": ("int", "中层预测窗口大小"),
    "phase1.prediction.high.n_clusters": ("int", "高层预测聚类数"),
    "phase1.prediction.anomaly_threshold": ("float", "异常检测阈值（标准差倍数）"),
    "phase2.task_pool.pool.max_size": ("int", "任务池最大容量"),
    "phase2.decision.exploration.base_exploration_ratio": ("float", "基础探索率"),
    "phase2.decision.task_selector.strategy": ("str", "任务选择策略 (priority/random)"),
    "phase2.memory.cache.max_cache_size": ("int", "缓存最大条数"),
    "phase2.memory.store.db_path": ("str", "SQLite 数据库文件路径"),
    "phase3.evolution.snapshot.max_snapshots": ("int", "最大快照保留数"),
    "phase3.evolution.refactor.error_threshold": ("float", "重构错误阈值"),
    "phase3.evolution.refactor.stagnation_rounds": ("int", "停滞触发重构的轮数"),
    "phase3.evolution.gap_threshold": ("float", "差距阈值"),
    "phase3.evolution.rollback_threshold": ("float", "回滚阈值"),
    "loop_interval": ("float", "主循环间隔（秒）"),
    "max_loops": ("int", "最大循环次数 (0=无限)"),
    "log_level": ("str", "日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)"),
    "health_check.enabled": ("bool", "是否启用 HTTP 健康检查端点"),
    "health_check.port": ("int", "健康检查 HTTP 端口"),
    "action_executor.dry_run": ("bool", "是否仅模拟执行（不执行真实操作）"),
    "action_executor.timeout": ("float", "动作执行超时（秒）"),
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """递归合并配置，override 优先。"""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class ConfigHelper:
    """配置安全取值辅助类"""

    @staticmethod
    def get(config: Dict[str, Any], path: str, default: Any = None) -> Any:
        """按点分路径安全获取配置值，不存在则返回 default。"""
        current: Any = config
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    @staticmethod
    def get_nested(
        config: Dict[str, Any],
        path: List[str],
        default: Any = None
    ) -> Any:
        """按路径列表安全获取配置值。"""
        current: Any = config
        for part in path:
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current


class ConfigDescriber:
    """配置项描述生成器"""

    @staticmethod
    def describe(path: str) -> Optional[tuple]:
        """获取单个配置项的 (类型, 说明)。"""
        return CONFIG_DESCRIPTIONS.get(path)

    @staticmethod
    def describe_all() -> List[Dict[str, Any]]:
        """返回所有配置项的描述列表。"""
        result: List[Dict[str, Any]] = []
        for path, (type_name, desc) in sorted(CONFIG_DESCRIPTIONS.items()):
            default_value = ConfigHelper.get(DEFAULT_CONFIG, path, "N/A")
            result.append({
                "path": path,
                "type": type_name,
                "description": desc,
                "default": default_value,
            })
        return result

    @staticmethod
    def to_text() -> str:
        """生成纯文本配置说明（表格格式），适合终端输出。"""
        from root.left.app.left.src.utils_main.cli_formatter import render_section, render_table

        lines: List[str] = []
        lines.append("=== Agent 配置项说明 ===")
        lines.append("")

        # 按段分组
        sections: Dict[str, List[tuple]] = {}
        for path, (type_name, desc) in sorted(CONFIG_DESCRIPTIONS.items()):
            section = path.split(".")[0] if "." in path else "global"
            sections.setdefault(section, []).append((path, type_name, desc))

        for section, entries in sections.items():
            lines.append(render_section(section))
            rows = []
            for path, type_name, desc in entries:
                default_value = ConfigHelper.get(DEFAULT_CONFIG, path, "N/A")
                rows.append([path, type_name, str(default_value), desc])
            lines.append(render_table(["配置项", "类型", "默认", "说明"], rows))
            lines.append("")

        lines.append("提示: 可通过环境变量 AGENT_<path> 覆盖配置（用 __ 分隔层级）。")
        return "\n".join(lines)


class ConfigLoader:
    """配置加载器"""

    ENV_PREFIX = "AGENT_"

    @staticmethod
    def load_config(environment: str) -> Dict[str, Any]:
        """加载指定环境配置，并与默认配置合并，再应用环境变量覆盖。"""
        ConfigLoader._validate_environment(environment)
        file_config = ConfigLoader._load_file_config(environment)
        merged = _deep_merge(DEFAULT_CONFIG, file_config)
        return ConfigLoader._apply_env_overrides(merged)

    @staticmethod
    def _validate_environment(environment: Optional[str]) -> None:
        if not environment or not isinstance(environment, str):
            raise ConfigurationError(
                "Environment must be a non-empty string",
                config_key=str(environment)
            )

    @staticmethod
    def _load_file_config(environment: str) -> Dict[str, Any]:
        config_path = ConfigLoader._get_config_path(environment)
        if not os.path.exists(config_path):
            raise ConfigurationError(
                f"Config file not found: {config_path}",
                config_key=environment
            )
        try:
            with open(config_path, "r", encoding="utf-8") as file:
                config = yaml.safe_load(file)
        except yaml.YAMLError as error:
            raise ConfigurationError(
                f"Failed to parse config: {error}",
                config_key=environment
            )
        if config is None:
            return {}
        if not isinstance(config, dict):
            raise ConfigurationError(
                "Config file must contain a dictionary",
                config_key=environment
            )
        return config

    @staticmethod
    def _get_config_path(environment: str) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        return os.path.normpath(
            os.path.join(base_dir, "right", "cfg", "left", "dev", f"{environment}.yaml")
        )

    @staticmethod
    def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
        """应用 AGENT_* 环境变量覆盖配置。"""
        result = config
        for key, raw_value in os.environ.items():
            if not key.startswith(ConfigLoader.ENV_PREFIX):
                continue
            config_key = key[len(ConfigLoader.ENV_PREFIX):]
            if not config_key:
                continue
            parts = config_key.lower().split("__")
            value = ConfigLoader._parse_env_value(raw_value)
            result = ConfigLoader._set_nested_value(result, parts, value)
        return result

    @staticmethod
    def _parse_env_value(raw_value: str) -> Any:
        """尝试将环境变量字符串解析为 bool/int/float，否则保留字符串。"""
        lowered = raw_value.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        try:
            return int(raw_value)
        except ValueError:
            pass
        try:
            return float(raw_value)
        except ValueError:
            pass
        return raw_value

    @staticmethod
    def _set_nested_value(
        config: Dict[str, Any],
        parts: List[str],
        value: Any
    ) -> Dict[str, Any]:
        """在嵌套字典中设置值，路径使用小写下划线分段。"""
        result = dict(config)
        current: Dict[str, Any] = result
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            else:
                current[part] = dict(current[part])
            current = current[part]
        current[parts[-1]] = value
        return result
