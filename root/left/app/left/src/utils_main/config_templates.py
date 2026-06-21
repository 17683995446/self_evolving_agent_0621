"""配置模板与快速初始化

提供预定义的配置模板，让用户无需手写 YAML 即可快速创建配置文件。

设计原则（第一性原理）：
1. 合理默认：用户应能立即用可用配置启动
2. 场景模板：为常见场景提供预构建配置
3. 非破坏性：未经确认不覆盖已有配置文件
4. 可发现：用户能列出和查看可用模板
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import yaml

from root.left.app.left.src.utils_main.config_loader import DEFAULT_CONFIG


# ---------------------------------------------------------------------------
# 配置模板定义
# ---------------------------------------------------------------------------

# 每个模板是 DEFAULT_CONFIG 的覆盖层，仅包含需要调整的键

CONFIG_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "minimal": {
        "description": "最小化配置：dry-run 模式，少量循环，适合快速验证",
        "config": {
            "loop_interval": 0.5,
            "max_loops": 10,
            "log_level": "INFO",
            "action_executor": {"dry_run": True, "timeout": 10.0},
            "health_check": {"enabled": False, "port": 8080},
            "phase1": {
                "sensory": {
                    "collectors": {
                        "system": {"enabled": True, "interval": 0.5, "history_size": 100}
                    },
                },
            },
            "phase2": {
                "task_pool": {"pool": {"max_size": 20}},
                "memory": {"cache": {"max_cache_size": 100}},
            },
            "phase3": {
                "evolution": {"snapshot": {"max_snapshots": 3}},
            },
        },
    },
    "standard": {
        "description": "标准配置：平衡的默认设置，适合日常开发",
        "config": {
            "loop_interval": 1.0,
            "max_loops": 1000,
            "log_level": "INFO",
            "action_executor": {"dry_run": True, "timeout": 30.0},
            "health_check": {"enabled": False, "port": 8080},
        },
    },
    "production": {
        "description": "生产配置：启用健康检查，更长间隔，更多循环",
        "config": {
            "loop_interval": 2.0,
            "max_loops": 0,
            "log_level": "WARNING",
            "action_executor": {"dry_run": False, "timeout": 60.0},
            "health_check": {"enabled": True, "port": 8080},
            "phase1": {
                "sensory": {
                    "collectors": {
                        "system": {"enabled": True, "interval": 2.0, "history_size": 2000}
                    },
                },
            },
            "phase2": {
                "task_pool": {"pool": {"max_size": 200}},
                "memory": {"cache": {"max_cache_size": 5000}},
            },
            "phase3": {
                "evolution": {"snapshot": {"max_snapshots": 10}},
            },
        },
    },
    "high-frequency": {
        "description": "高频监控配置：短间隔采集，适合密集监控场景",
        "config": {
            "loop_interval": 0.2,
            "max_loops": 5000,
            "log_level": "DEBUG",
            "action_executor": {"dry_run": True, "timeout": 5.0},
            "health_check": {"enabled": True, "port": 8080},
            "phase1": {
                "sensory": {
                    "collectors": {
                        "system": {"enabled": True, "interval": 0.1, "history_size": 5000}
                    },
                    "noise_filter": {"ema_alpha": 0.5},
                },
            },
            "phase2": {
                "task_pool": {"pool": {"max_size": 500}},
                "memory": {"cache": {"max_cache_size": 10000}},
            },
        },
    },
}


def list_templates() -> List[Dict[str, str]]:
    """列出所有可用模板。

    Returns:
        模板信息列表，每项包含 name 和 description
    """
    return [
        {"name": name, "description": info["description"]}
        for name, info in CONFIG_TEMPLATES.items()
    ]


def get_template(name: str) -> Optional[Dict[str, Any]]:
    """获取指定模板的配置（已与默认配置合并）。

    Args:
        name: 模板名称

    Returns:
        合并后的完整配置字典，模板不存在则返回 None
    """
    template = CONFIG_TEMPLATES.get(name)
    if template is None:
        return None
    # 深拷贝默认配置，再合并模板覆盖
    import copy
    merged = copy.deepcopy(DEFAULT_CONFIG)
    _deep_merge_inplace(merged, template["config"])
    return merged


def get_template_raw(name: str) -> Optional[Dict[str, Any]]:
    """获取模板的原始覆盖配置（不含默认值）。

    Args:
        name: 模板名称

    Returns:
        模板覆盖配置字典，模板不存在则返回 None
    """
    template = CONFIG_TEMPLATES.get(name)
    if template is None:
        return None
    import copy
    return copy.deepcopy(template["config"])


def render_template(name: str) -> str:
    """将模板渲染为 YAML 文本。

    Args:
        name: 模板名称

    Returns:
        YAML 格式的配置文本

    Raises:
        ValueError: 模板不存在
    """
    config = get_template(name)
    if config is None:
        raise ValueError(f"未知模板: {name}，可用模板: {', '.join(CONFIG_TEMPLATES.keys())}")
    return yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=False)


def save_template(name: str, env: str, force: bool = False) -> str:
    """将模板保存为配置文件。

    Args:
        name: 模板名称
        env: 目标环境名称（用作文件名）
        force: 是否覆盖已有文件

    Returns:
        保存的文件路径

    Raises:
        ValueError: 模板不存在
        FileExistsError: 文件已存在且 force=False
    """
    config = get_template(name)
    if config is None:
        raise ValueError(f"未知模板: {name}，可用模板: {', '.join(CONFIG_TEMPLATES.keys())}")

    config_path = _get_config_file_path(env)
    if os.path.exists(config_path) and not force:
        raise FileExistsError(f"配置文件已存在: {config_path}（使用 force=True 覆盖）")

    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    yaml_text = yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=False)
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(yaml_text)
    return config_path


def _get_config_file_path(env: str) -> str:
    """获取配置文件路径（与 ConfigLoader 路径解析一致）。"""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    return os.path.normpath(
        os.path.join(base_dir, "right", "cfg", "left", "dev", f"{env}.yaml")
    )


def _deep_merge_inplace(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    """将 overlay 深度合并到 base（就地修改）。"""
    for key, value in overlay.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge_inplace(base[key], value)
        else:
            base[key] = value
    return base


# ---------------------------------------------------------------------------
# 交互式配置构建器
# ---------------------------------------------------------------------------

def build_custom_config(
    env: str = "dev",
    max_loops: int = 100,
    loop_interval: float = 1.0,
    dry_run: bool = True,
    health_check: bool = False,
    health_port: int = 8080,
    log_level: str = "INFO",
) -> Dict[str, Any]:
    """根据用户输入构建自定义配置。

    Args:
        env: 环境名称
        max_loops: 最大循环次数 (0=无限)
        loop_interval: 循环间隔秒数
        dry_run: 是否 dry-run 模式
        health_check: 是否启用健康检查
        health_port: 健康检查端口
        log_level: 日志级别

    Returns:
        完整配置字典
    """
    import copy
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["loop_interval"] = loop_interval
    config["max_loops"] = max_loops
    config["log_level"] = log_level
    config["action_executor"]["dry_run"] = dry_run
    config["health_check"]["enabled"] = health_check
    config["health_check"]["port"] = health_port
    return config
