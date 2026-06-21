"""配置差异对比与变更审计

提供配置字典的深度对比、差异渲染与审计报告生成能力。

设计原则（第一性原理）：
1. 可追溯：用户能看清任意两份配置之间的差异
2. 可理解：差异以点分路径呈现，附带配置项说明
3. 可审计：生成审计报告，记录变更类型与影响范围
4. 非侵入式：仅做只读对比，不修改任何配置
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml

from root.left.app.left.src.utils_main.cli_formatter import (
    Color,
    colorize,
    render_divider,
    render_key_value,
    render_section,
    render_table,
)
from root.left.app.left.src.utils_main.config_loader import (
    DEFAULT_CONFIG,
    CONFIG_DESCRIPTIONS,
    ConfigLoader,
)


# ---------------------------------------------------------------------------
# 差异数据结构
# ---------------------------------------------------------------------------

@dataclass
class ConfigDiff:
    """单条配置差异。"""

    path: str
    old_value: Any
    new_value: Any
    change_type: str  # 'added' | 'removed' | 'modified'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "change_type": self.change_type,
        }

    @property
    def description(self) -> str:
        """获取该配置项的说明文本。"""
        desc = CONFIG_DESCRIPTIONS.get(self.path)
        return desc[1] if desc else ""


# ---------------------------------------------------------------------------
# 深度对比
# ---------------------------------------------------------------------------

def diff_configs(
    config_a: Dict[str, Any],
    config_b: Dict[str, Any],
    prefix: str = "",
) -> List[ConfigDiff]:
    """深度对比两个配置字典。

    Args:
        config_a: 基准配置（旧值来源）
        config_b: 目标配置（新值来源）
        prefix: 当前路径前缀（递归用）

    Returns:
        ConfigDiff 列表，按路径排序
    """
    diffs: List[ConfigDiff] = []
    all_keys = set(config_a.keys()) | set(config_b.keys())

    for key in sorted(all_keys):
        path = f"{prefix}.{key}" if prefix else key
        in_a = key in config_a
        in_b = key in config_b
        val_a = config_a.get(key)
        val_b = config_b.get(key)

        if in_a and not in_b:
            diffs.append(ConfigDiff(path, val_a, None, "removed"))
        elif not in_a and in_b:
            diffs.append(ConfigDiff(path, None, val_b, "added"))
        elif isinstance(val_a, dict) and isinstance(val_b, dict):
            diffs.extend(diff_configs(val_a, val_b, path))
        elif val_a != val_b:
            diffs.append(ConfigDiff(path, val_a, val_b, "modified"))

    return diffs


def diff_against_defaults(config: Dict[str, Any]) -> List[ConfigDiff]:
    """对比配置与默认配置的差异。

    Args:
        config: 待对比的配置

    Returns:
        ConfigDiff 列表（config 相对 DEFAULT_CONFIG 的变更）
    """
    return diff_configs(DEFAULT_CONFIG, config)


def diff_envs(env_a: str, env_b: str) -> List[ConfigDiff]:
    """对比两个环境的配置差异。

    Args:
        env_a: 基准环境名
        env_b: 目标环境名

    Returns:
        ConfigDiff 列表（env_b 相对 env_a 的变更）
    """
    config_a = ConfigLoader.load_config(env_a)
    config_b = ConfigLoader.load_config(env_b)
    return diff_configs(config_a, config_b)


def diff_files(file_a: str, file_b: str) -> List[ConfigDiff]:
    """对比两个 YAML 配置文件的差异。

    Args:
        file_a: 基准配置文件路径
        file_b: 目标配置文件路径

    Returns:
        ConfigDiff 列表（file_b 相对 file_a 的变更）

    Raises:
        FileNotFoundError: 文件不存在
        yaml.YAMLError: YAML 解析失败
    """
    config_a = _load_yaml_file(file_a)
    config_b = _load_yaml_file(file_b)
    return diff_configs(config_a, config_b)


def _load_yaml_file(file_path: str) -> Dict[str, Any]:
    """加载 YAML 文件为字典。"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"配置文件不存在: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------------------
# 差异渲染
# ---------------------------------------------------------------------------

def render_diff(diffs: List[ConfigDiff], show_description: bool = False) -> str:
    """渲染配置差异为可读文本。

    Args:
        diffs: ConfigDiff 列表
        show_description: 是否显示配置项说明

    Returns:
        可读文本
    """
    if not diffs:
        return "无差异（配置完全一致）。"

    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section(f"配置差异（共 {len(diffs)} 项）"))
    lines.append(render_divider())
    lines.append("")

    # 按变更类型分组统计
    added = [d for d in diffs if d.change_type == "added"]
    removed = [d for d in diffs if d.change_type == "removed"]
    modified = [d for d in diffs if d.change_type == "modified"]

    lines.append(render_key_value([
        ("新增", len(added)),
        ("删除", len(removed)),
        ("修改", len(modified)),
    ]))
    lines.append("")

    # 表格形式展示
    headers = ["路径", "变更", "旧值", "新值"]
    if show_description:
        headers.append("说明")

    rows: List[List[str]] = []
    for d in diffs:
        change_display = _format_change_type(d.change_type)
        old_display = _format_value(d.old_value)
        new_display = _format_value(d.new_value)
        row = [d.path, change_display, old_display, new_display]
        if show_description:
            row.append(d.description or "-")
        rows.append(row)

    lines.append(render_table(headers, rows))
    return "\n".join(lines)


def _format_change_type(change_type: str) -> str:
    """格式化变更类型。"""
    if change_type == "added":
        return colorize("新增", Color.GREEN)
    if change_type == "removed":
        return colorize("删除", Color.RED)
    if change_type == "modified":
        return colorize("修改", Color.YELLOW)
    return change_type


def _format_value(value: Any) -> str:
    """格式化配置值用于显示。"""
    if value is None:
        return colorize("(无)", Color.GRAY)
    if isinstance(value, dict):
        return f"{{...}}({len(value)} keys)"
    if isinstance(value, list):
        return f"[...]({len(value)} items)"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, str) and len(value) > 50:
        return value[:47] + "..."
    return str(value)


# ---------------------------------------------------------------------------
# 审计报告
# ---------------------------------------------------------------------------

@dataclass
class AuditReport:
    """配置审计报告。"""

    generated_at: str
    env: str
    total_changes: int
    added_count: int
    removed_count: int
    modified_count: int
    diffs: List[ConfigDiff] = field(default_factory=list)
    config_source: str = "file"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "env": self.env,
            "total_changes": self.total_changes,
            "added_count": self.added_count,
            "removed_count": self.removed_count,
            "modified_count": self.modified_count,
            "config_source": self.config_source,
            "diffs": [d.to_dict() for d in self.diffs],
        }

    def to_text(self) -> str:
        """渲染审计报告为文本。"""
        lines: List[str] = []
        lines.append(render_divider())
        lines.append(render_section("配置审计报告"))
        lines.append(render_divider())
        lines.append("")

        lines.append(render_key_value([
            ("生成时间", self.generated_at),
            ("环境", self.env),
            ("配置来源", self.config_source),
            ("变更总数", self.total_changes),
            ("新增", self.added_count),
            ("删除", self.removed_count),
            ("修改", self.modified_count),
        ]))
        lines.append("")

        if self.diffs:
            lines.append(render_section("变更明细"))
            lines.append("")
            lines.append(render_diff(self.diffs, show_description=True))
        else:
            lines.append("配置与默认值一致，无变更。")

        lines.append("")
        lines.append(render_divider())
        return "\n".join(lines)

    def to_json(self) -> str:
        """渲染审计报告为 JSON。"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str)


def generate_audit_report(
    config: Dict[str, Any],
    env: str = "unknown",
    baseline: Optional[Dict[str, Any]] = None,
    config_source: str = "file",
) -> AuditReport:
    """生成配置审计报告。

    Args:
        config: 待审计的配置
        env: 环境名
        baseline: 基准配置（默认为 DEFAULT_CONFIG）
        config_source: 配置来源描述

    Returns:
        AuditReport 实例
    """
    from datetime import datetime

    if baseline is None:
        baseline = DEFAULT_CONFIG

    diffs = diff_configs(baseline, config)

    added = sum(1 for d in diffs if d.change_type == "added")
    removed = sum(1 for d in diffs if d.change_type == "removed")
    modified = sum(1 for d in diffs if d.change_type == "modified")

    return AuditReport(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        env=env,
        total_changes=len(diffs),
        added_count=added,
        removed_count=removed,
        modified_count=modified,
        diffs=diffs,
        config_source=config_source,
    )


def save_audit_report(report: AuditReport, output_path: str, fmt: str = "text") -> str:
    """保存审计报告到文件。

    Args:
        report: 审计报告
        output_path: 输出路径
        fmt: 格式 (text/json)

    Returns:
        保存的文件路径
    """
    content = report.to_json() if fmt == "json" else report.to_text()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path
