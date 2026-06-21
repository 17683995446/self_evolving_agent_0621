"""通知与告警系统

提供阈值告警规则定义、事件订阅与多渠道通知能力。

设计原则（第一性原理）：
1. 可配置：用户定义阈值规则（如 CPU > 80% 触发告警）
2. 可订阅：用户订阅感兴趣的事件类型
3. 可通知：支持多种通知渠道（控制台、日志、Webhook）
4. 非侵入式：告警系统独立于主循环，可选启用
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List

from root.left.app.left.src.utils_main.cli_formatter import (
    Color,
    colorize,
    render_divider,
    render_key_value,
    render_section,
    render_table,
)


# ---------------------------------------------------------------------------
# 枚举与常量
# ---------------------------------------------------------------------------

class AlertLevel(str, Enum):
    """告警级别。"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    """通知渠道。"""

    CONSOLE = "console"
    LOG = "log"
    WEBHOOK = "webhook"


# 级别到颜色的映射
LEVEL_COLORS: Dict[str, Color] = {
    AlertLevel.INFO.value: Color.CYAN,
    AlertLevel.WARNING.value: Color.YELLOW,
    AlertLevel.ERROR.value: Color.RED,
    AlertLevel.CRITICAL.value: Color.MAGENTA,
}


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class AlertRule:
    """告警规则。

    定义何时触发告警：当某指标满足比较条件时。
    """

    name: str
    metric: str  # 指标名（如 cpu_percent, memory_percent, loop_count）
    operator: str  # 比较运算符: >, <, >=, <=, ==, !=
    threshold: float  # 阈值
    level: AlertLevel = AlertLevel.WARNING
    message: str = ""
    cooldown_seconds: float = 60.0  # 冷却时间，避免重复告警
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "metric": self.metric,
            "operator": self.operator,
            "threshold": self.threshold,
            "level": self.level.value,
            "message": self.message,
            "cooldown_seconds": self.cooldown_seconds,
            "enabled": self.enabled,
        }

    def evaluate(self, value: float) -> bool:
        """评估规则是否触发。

        Args:
            value: 当前指标值

        Returns:
            是否触发告警
        """
        if not self.enabled:
            return False
        ops: Dict[str, Callable[[float, float], bool]] = {
            ">": lambda a, b: a > b,
            "<": lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
        }
        op_func = ops.get(self.operator)
        if op_func is None:
            return False
        return op_func(value, self.threshold)


@dataclass
class Alert:
    """告警事件。"""

    rule_name: str
    level: AlertLevel
    metric: str
    value: float
    threshold: float
    message: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "level": self.level.value,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "message": self.message,
            "timestamp": self.timestamp,
        }

    def to_text(self) -> str:
        """渲染告警为文本。"""
        level_display = colorize(
            f"[{self.level.value.upper()}]",
            LEVEL_COLORS.get(self.level.value, Color.GRAY),
        )
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp))
        msg = self.message or f"{self.metric}={self.value} (阈值{self.threshold})"
        return f"{time_str} {level_display} [{self.rule_name}] {msg}"


# ---------------------------------------------------------------------------
# 通知渠道
# ---------------------------------------------------------------------------

class Notifier:
    """通知器基类。"""

    def notify(self, alert: Alert) -> None:
        """发送通知。"""
        raise NotImplementedError

    def close(self) -> None:
        """清理资源。"""
        pass


class ConsoleNotifier(Notifier):
    """控制台通知器。"""

    def __init__(self, output_fn: Callable[[str], None] = print) -> None:
        self.output_fn = output_fn

    def notify(self, alert: Alert) -> None:
        self.output_fn(alert.to_text())


class LogNotifier(Notifier):
    """日志通知器。"""

    def __init__(self) -> None:
        from root.left.app.left.src.utils_main.logger import logger
        self._logger = logger

    def notify(self, alert: Alert) -> None:
        level_map = {
            AlertLevel.INFO: "info",
            AlertLevel.WARNING: "warning",
            AlertLevel.ERROR: "error",
            AlertLevel.CRITICAL: "critical",
        }
        method_name = level_map.get(alert.level, "info")
        msg = f"[{alert.rule_name}] {alert.metric}={alert.value} (阈值{alert.threshold})"
        if alert.message:
            msg = f"{msg} - {alert.message}"
        log_fn = getattr(self._logger, method_name, self._logger.info)
        log_fn(msg, "alert")


class WebhookNotifier(Notifier):
    """Webhook 通知器。

    通过 HTTP POST 发送告警到指定 URL。
    """

    def __init__(self, url: str, timeout: float = 5.0) -> None:
        self.url = url
        self.timeout = timeout

    def notify(self, alert: Alert) -> None:
        import urllib.error
        import urllib.request

        payload = json.dumps(alert.to_dict(), ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.url,
            data=payload,
            method="POST",
        )
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp.read()
        except (urllib.error.URLError, OSError):
            pass  # 静默失败，避免影响主流程


def create_notifier(channel: AlertChannel, **kwargs: Any) -> Notifier:
    """创建通知器。

    Args:
        channel: 通知渠道
        **kwargs: 渠道特定参数

    Returns:
        Notifier 实例
    """
    if channel == AlertChannel.CONSOLE:
        return ConsoleNotifier(**kwargs)
    if channel == AlertChannel.LOG:
        return LogNotifier()
    if channel == AlertChannel.WEBHOOK:
        return WebhookNotifier(**kwargs)
    raise ValueError(f"未知通知渠道: {channel}")


# ---------------------------------------------------------------------------
# 告警管理器
# ---------------------------------------------------------------------------

class AlertManager:
    """告警管理器。

    管理告警规则、评估指标、发送通知。
    """

    def __init__(self) -> None:
        self._rules: Dict[str, AlertRule] = {}
        self._notifiers: List[Notifier] = []
        self._last_triggered: Dict[str, float] = {}  # 规则名 -> 上次触发时间
        self._history: List[Alert] = []

    def add_rule(self, rule: AlertRule) -> None:
        """添加告警规则。"""
        self._rules[rule.name] = rule

    def remove_rule(self, name: str) -> bool:
        """移除告警规则。"""
        if name in self._rules:
            del self._rules[name]
            return True
        return False

    def get_rules(self) -> List[AlertRule]:
        """获取所有规则。"""
        return list(self._rules.values())

    def add_notifier(self, notifier: Notifier) -> None:
        """添加通知器。"""
        self._notifiers.append(notifier)

    def clear_notifiers(self) -> None:
        """清空通知器。"""
        for n in self._notifiers:
            n.close()
        self._notifiers.clear()

    def evaluate(self, metrics: Dict[str, float]) -> List[Alert]:
        """评估所有规则。

        Args:
            metrics: 指标字典 {指标名: 值}

        Returns:
            触发的告警列表
        """
        triggered: List[Alert] = []
        now = time.time()

        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if rule.metric not in metrics:
                continue

            value = metrics[rule.metric]
            if not rule.evaluate(value):
                continue

            # 冷却检查
            last = self._last_triggered.get(rule.name, 0)
            if now - last < rule.cooldown_seconds:
                continue

            alert = Alert(
                rule_name=rule.name,
                level=rule.level,
                metric=rule.metric,
                value=value,
                threshold=rule.threshold,
                message=rule.message,
                timestamp=now,
            )
            triggered.append(alert)
            self._last_triggered[rule.name] = now
            self._history.append(alert)

            # 发送通知
            for notifier in self._notifiers:
                try:
                    notifier.notify(alert)
                except Exception:
                    pass  # 通知失败不影响主流程

        return triggered

    def get_history(self, limit: int = 100) -> List[Alert]:
        """获取告警历史。"""
        return self._history[-limit:]

    def clear_history(self) -> None:
        """清空告警历史。"""
        self._history.clear()
        self._last_triggered.clear()

    def to_dict(self) -> Dict[str, Any]:
        """导出告警管理器状态。"""
        return {
            "rules": [r.to_dict() for r in self._rules.values()],
            "history_count": len(self._history),
            "notifier_count": len(self._notifiers),
        }


# ---------------------------------------------------------------------------
# 预设规则
# ---------------------------------------------------------------------------

def create_default_rules() -> List[AlertRule]:
    """创建默认告警规则集。"""
    return [
        AlertRule(
            name="high_cpu",
            metric="cpu_percent",
            operator=">",
            threshold=80.0,
            level=AlertLevel.WARNING,
            message="CPU 使用率过高",
            cooldown_seconds=60.0,
        ),
        AlertRule(
            name="critical_cpu",
            metric="cpu_percent",
            operator=">",
            threshold=95.0,
            level=AlertLevel.CRITICAL,
            message="CPU 使用率危险",
            cooldown_seconds=30.0,
        ),
        AlertRule(
            name="high_memory",
            metric="memory_percent",
            operator=">",
            threshold=85.0,
            level=AlertLevel.WARNING,
            message="内存使用率过高",
            cooldown_seconds=60.0,
        ),
        AlertRule(
            name="critical_memory",
            metric="memory_percent",
            operator=">",
            threshold=95.0,
            level=AlertLevel.CRITICAL,
            message="内存使用率危险",
            cooldown_seconds=30.0,
        ),
        AlertRule(
            name="error_rate_high",
            metric="error_count",
            operator=">",
            threshold=10.0,
            level=AlertLevel.ERROR,
            message="错误数量过多",
            cooldown_seconds=120.0,
        ),
    ]


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------

def render_rules(rules: List[AlertRule]) -> str:
    """渲染告警规则列表。"""
    if not rules:
        return "无告警规则。"

    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section(f"告警规则（共 {len(rules)} 条）"))
    lines.append(render_divider())
    lines.append("")

    rows: List[List[str]] = []
    for r in rules:
        status = colorize("启用", Color.GREEN) if r.enabled else colorize("禁用", Color.GRAY)
        level = colorize(
            r.level.value.upper(),
            LEVEL_COLORS.get(r.level.value, Color.GRAY),
        )
        condition = f"{r.metric} {r.operator} {r.threshold}"
        rows.append([r.name, level, condition, status, r.message])

    lines.append(render_table(["名称", "级别", "条件", "状态", "说明"], rows))
    return "\n".join(lines)


def render_alerts(alerts: List[Alert]) -> str:
    """渲染告警列表。"""
    if not alerts:
        return "无告警记录。"

    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section(f"告警记录（共 {len(alerts)} 条）"))
    lines.append(render_divider())
    lines.append("")

    for alert in alerts:
        lines.append(alert.to_text())

    lines.append("")
    lines.append(render_divider())
    return "\n".join(lines)


def render_alert_summary(manager: AlertManager) -> str:
    """渲染告警管理器摘要。"""
    rules = manager.get_rules()
    history = manager.get_history()

    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section("告警系统摘要"))
    lines.append(render_divider())
    lines.append("")

    # 按级别统计
    level_counts: Dict[str, int] = {}
    for alert in history:
        level = alert.level.value
        level_counts[level] = level_counts.get(level, 0) + 1

    lines.append(render_key_value([
        ("规则总数", len(rules)),
        ("启用规则", sum(1 for r in rules if r.enabled)),
        ("告警总数", len(history)),
        ("info 告警", level_counts.get("info", 0)),
        ("warning 告警", level_counts.get("warning", 0)),
        ("error 告警", level_counts.get("error", 0)),
        ("critical 告警", level_counts.get("critical", 0)),
    ]))

    return "\n".join(lines)
