"""通知与告警系统测试"""
from __future__ import annotations

from typing import List

from root.left.app.left.src.cli import main
from root.left.app.left.src.utils_main.alert_system import (
    Alert,
    AlertLevel,
    AlertManager,
    AlertRule,
    ConsoleNotifier,
    LogNotifier,
    Notifier,
    create_default_rules,
    create_notifier,
    render_alert_summary,
    render_alerts,
    render_rules,
)


# ---------------------------------------------------------------------------
# AlertRule 测试
# ---------------------------------------------------------------------------

class TestAlertRule:
    """测试告警规则"""

    def test_to_dict(self):
        rule = AlertRule(
            name="high_cpu",
            metric="cpu_percent",
            operator=">",
            threshold=80.0,
            level=AlertLevel.WARNING,
            message="CPU 过高",
        )
        d = rule.to_dict()
        assert d["name"] == "high_cpu"
        assert d["metric"] == "cpu_percent"
        assert d["operator"] == ">"
        assert d["threshold"] == 80.0
        assert d["level"] == "warning"
        assert d["message"] == "CPU 过高"

    def test_evaluate_greater_than_triggered(self):
        rule = AlertRule("test", "cpu", ">", 80.0)
        assert rule.evaluate(90.0) is True

    def test_evaluate_greater_than_not_triggered(self):
        rule = AlertRule("test", "cpu", ">", 80.0)
        assert rule.evaluate(70.0) is False

    def test_evaluate_less_than(self):
        rule = AlertRule("test", "cpu", "<", 10.0)
        assert rule.evaluate(5.0) is True
        assert rule.evaluate(20.0) is False

    def test_evaluate_greater_equal(self):
        rule = AlertRule("test", "cpu", ">=", 80.0)
        assert rule.evaluate(80.0) is True
        assert rule.evaluate(79.0) is False

    def test_evaluate_less_equal(self):
        rule = AlertRule("test", "cpu", "<=", 80.0)
        assert rule.evaluate(80.0) is True
        assert rule.evaluate(81.0) is False

    def test_evaluate_equal(self):
        rule = AlertRule("test", "cpu", "==", 80.0)
        assert rule.evaluate(80.0) is True
        assert rule.evaluate(81.0) is False

    def test_evaluate_not_equal(self):
        rule = AlertRule("test", "cpu", "!=", 80.0)
        assert rule.evaluate(81.0) is True
        assert rule.evaluate(80.0) is False

    def test_evaluate_disabled_rule(self):
        rule = AlertRule("test", "cpu", ">", 80.0, enabled=False)
        assert rule.evaluate(90.0) is False

    def test_evaluate_invalid_operator(self):
        rule = AlertRule("test", "cpu", "~=", 80.0)
        assert rule.evaluate(90.0) is False

    def test_default_values(self):
        rule = AlertRule("test", "cpu", ">", 80.0)
        assert rule.level == AlertLevel.WARNING
        assert rule.message == ""
        assert rule.cooldown_seconds == 60.0
        assert rule.enabled is True


# ---------------------------------------------------------------------------
# Alert 测试
# ---------------------------------------------------------------------------

class TestAlert:
    """测试告警事件"""

    def test_to_dict(self):
        alert = Alert(
            rule_name="high_cpu",
            level=AlertLevel.WARNING,
            metric="cpu_percent",
            value=90.0,
            threshold=80.0,
            message="CPU 过高",
        )
        d = alert.to_dict()
        assert d["rule_name"] == "high_cpu"
        assert d["level"] == "warning"
        assert d["metric"] == "cpu_percent"
        assert d["value"] == 90.0
        assert d["threshold"] == 80.0
        assert d["message"] == "CPU 过高"

    def test_to_text(self):
        alert = Alert(
            rule_name="high_cpu",
            level=AlertLevel.ERROR,
            metric="cpu_percent",
            value=90.0,
            threshold=80.0,
            message="CPU 过高",
        )
        text = alert.to_text()
        assert "high_cpu" in text
        assert "ERROR" in text
        assert "CPU 过高" in text

    def test_to_text_default_message(self):
        alert = Alert(
            rule_name="test",
            level=AlertLevel.WARNING,
            metric="cpu",
            value=90.0,
            threshold=80.0,
            message="",
        )
        text = alert.to_text()
        assert "cpu=90.0" in text
        assert "80.0" in text

    def test_timestamp_default(self):
        alert = Alert(
            rule_name="test",
            level=AlertLevel.INFO,
            metric="cpu",
            value=50.0,
            threshold=80.0,
            message="",
        )
        assert alert.timestamp > 0


# ---------------------------------------------------------------------------
# 通知器测试
# ---------------------------------------------------------------------------

class TestConsoleNotifier:
    """测试控制台通知器"""

    def test_notify_outputs_text(self):
        outputs: List[str] = []
        notifier = ConsoleNotifier(output_fn=outputs.append)
        alert = Alert(
            rule_name="test",
            level=AlertLevel.WARNING,
            metric="cpu",
            value=90.0,
            threshold=80.0,
            message="test alert",
        )
        notifier.notify(alert)
        assert len(outputs) == 1
        assert "test" in outputs[0]
        assert "WARNING" in outputs[0]


class TestLogNotifier:
    """测试日志通知器"""

    def test_notify_does_not_raise(self):
        notifier = LogNotifier()
        alert = Alert(
            rule_name="test",
            level=AlertLevel.WARNING,
            metric="cpu",
            value=90.0,
            threshold=80.0,
            message="test",
        )
        # 不应抛出异常
        notifier.notify(alert)


class TestCreateNotifier:
    """测试通知器工厂"""

    def test_create_console(self):
        from root.left.app.left.src.utils_main.alert_system import AlertChannel
        n = create_notifier(AlertChannel.CONSOLE)
        assert isinstance(n, ConsoleNotifier)

    def test_create_log(self):
        from root.left.app.left.src.utils_main.alert_system import AlertChannel
        n = create_notifier(AlertChannel.LOG)
        assert isinstance(n, LogNotifier)

    def test_create_webhook(self):
        from root.left.app.left.src.utils_main.alert_system import AlertChannel, WebhookNotifier
        n = create_notifier(AlertChannel.WEBHOOK, url="http://example.com/hook")
        assert isinstance(n, WebhookNotifier)
        assert n.url == "http://example.com/hook"


# ---------------------------------------------------------------------------
# AlertManager 测试
# ---------------------------------------------------------------------------

class TestAlertManager:
    """测试告警管理器"""

    def test_add_and_get_rules(self):
        manager = AlertManager()
        rule = AlertRule("test", "cpu", ">", 80.0)
        manager.add_rule(rule)
        rules = manager.get_rules()
        assert len(rules) == 1
        assert rules[0].name == "test"

    def test_remove_rule(self):
        manager = AlertManager()
        manager.add_rule(AlertRule("test", "cpu", ">", 80.0))
        assert manager.remove_rule("test") is True
        assert len(manager.get_rules()) == 0

    def test_remove_nonexistent_rule(self):
        manager = AlertManager()
        assert manager.remove_rule("nonexistent") is False

    def test_add_notifier(self):
        manager = AlertManager()
        notifier = ConsoleNotifier()
        manager.add_notifier(notifier)
        # 通过 evaluate 验证通知器被调用
        rule = AlertRule("test", "cpu", ">", 80.0)
        manager.add_rule(rule)
        alerts = manager.evaluate({"cpu": 90.0})
        assert len(alerts) == 1

    def test_evaluate_triggers_alert(self):
        manager = AlertManager()
        manager.add_rule(AlertRule("high_cpu", "cpu_percent", ">", 80.0))
        alerts = manager.evaluate({"cpu_percent": 90.0})
        assert len(alerts) == 1
        assert alerts[0].rule_name == "high_cpu"
        assert alerts[0].value == 90.0

    def test_evaluate_no_trigger(self):
        manager = AlertManager()
        manager.add_rule(AlertRule("high_cpu", "cpu_percent", ">", 80.0))
        alerts = manager.evaluate({"cpu_percent": 70.0})
        assert len(alerts) == 0

    def test_evaluate_missing_metric(self):
        manager = AlertManager()
        manager.add_rule(AlertRule("high_cpu", "cpu_percent", ">", 80.0))
        alerts = manager.evaluate({"memory_percent": 90.0})
        assert len(alerts) == 0

    def test_evaluate_disabled_rule(self):
        manager = AlertManager()
        manager.add_rule(AlertRule("test", "cpu", ">", 80.0, enabled=False))
        alerts = manager.evaluate({"cpu": 90.0})
        assert len(alerts) == 0

    def test_cooldown_prevents_repeat(self):
        manager = AlertManager()
        manager.add_rule(AlertRule("test", "cpu", ">", 80.0, cooldown_seconds=60.0))
        # 第一次触发
        alerts1 = manager.evaluate({"cpu": 90.0})
        assert len(alerts1) == 1
        # 第二次应被冷却阻止
        alerts2 = manager.evaluate({"cpu": 90.0})
        assert len(alerts2) == 0

    def test_cooldown_expired(self):
        manager = AlertManager()
        manager.add_rule(AlertRule("test", "cpu", ">", 80.0, cooldown_seconds=0.0))
        # cooldown=0 应每次都触发
        alerts1 = manager.evaluate({"cpu": 90.0})
        alerts2 = manager.evaluate({"cpu": 90.0})
        assert len(alerts1) == 1
        assert len(alerts2) == 1

    def test_history(self):
        manager = AlertManager()
        manager.add_rule(AlertRule("test", "cpu", ">", 80.0, cooldown_seconds=0.0))
        manager.evaluate({"cpu": 90.0})
        manager.evaluate({"cpu": 95.0})
        history = manager.get_history()
        assert len(history) == 2

    def test_clear_history(self):
        manager = AlertManager()
        manager.add_rule(AlertRule("test", "cpu", ">", 80.0, cooldown_seconds=0.0))
        manager.evaluate({"cpu": 90.0})
        manager.clear_history()
        assert len(manager.get_history()) == 0

    def test_to_dict(self):
        manager = AlertManager()
        manager.add_rule(AlertRule("test", "cpu", ">", 80.0))
        d = manager.to_dict()
        assert d["history_count"] == 0
        assert len(d["rules"]) == 1

    def test_notifier_exception_handled(self):
        """通知器异常不应影响主流程"""
        class FailingNotifier(Notifier):
            def notify(self, alert: Alert) -> None:
                raise RuntimeError("notifier failed")

        manager = AlertManager()
        manager.add_notifier(FailingNotifier())
        manager.add_rule(AlertRule("test", "cpu", ">", 80.0))
        # 不应抛出异常
        alerts = manager.evaluate({"cpu": 90.0})
        assert len(alerts) == 1


# ---------------------------------------------------------------------------
# 默认规则测试
# ---------------------------------------------------------------------------

class TestDefaultRules:
    """测试默认告警规则"""

    def test_returns_list(self):
        rules = create_default_rules()
        assert isinstance(rules, list)
        assert len(rules) > 0

    def test_contains_cpu_rules(self):
        rules = create_default_rules()
        names = [r.name for r in rules]
        assert "high_cpu" in names
        assert "critical_cpu" in names

    def test_contains_memory_rules(self):
        rules = create_default_rules()
        names = [r.name for r in rules]
        assert "high_memory" in names
        assert "critical_memory" in names

    def test_contains_error_rule(self):
        rules = create_default_rules()
        names = [r.name for r in rules]
        assert "error_rate_high" in names

    def test_critical_level_for_critical_rules(self):
        rules = create_default_rules()
        critical_cpu = next(r for r in rules if r.name == "critical_cpu")
        assert critical_cpu.level == AlertLevel.CRITICAL


# ---------------------------------------------------------------------------
# 渲染测试
# ---------------------------------------------------------------------------

class TestRenderRules:
    """测试规则渲染"""

    def test_empty_rules(self):
        result = render_rules([])
        assert "无告警规则" in result

    def test_with_rules(self):
        rules = [AlertRule("test", "cpu", ">", 80.0, message="CPU 高")]
        result = render_rules(rules)
        assert "告警规则" in result
        assert "test" in result
        assert "cpu" in result

    def test_disabled_rule_displayed(self):
        rules = [AlertRule("test", "cpu", ">", 80.0, enabled=False)]
        result = render_rules(rules)
        assert "禁用" in result


class TestRenderAlerts:
    """测试告警渲染"""

    def test_empty_alerts(self):
        result = render_alerts([])
        assert "无告警记录" in result

    def test_with_alerts(self):
        alerts = [Alert(
            rule_name="test",
            level=AlertLevel.WARNING,
            metric="cpu",
            value=90.0,
            threshold=80.0,
            message="CPU 高",
        )]
        result = render_alerts(alerts)
        assert "告警记录" in result
        assert "test" in result
        assert "WARNING" in result


class TestRenderAlertSummary:
    """测试告警摘要渲染"""

    def test_empty_manager(self):
        manager = AlertManager()
        result = render_alert_summary(manager)
        assert "告警系统摘要" in result
        assert "规则总数" in result

    def test_with_rules_and_history(self):
        manager = AlertManager()
        manager.add_rule(AlertRule("test", "cpu", ">", 80.0, cooldown_seconds=0.0))
        manager.evaluate({"cpu": 90.0})
        result = render_alert_summary(manager)
        assert "告警系统摘要" in result
        assert "1" in result  # 1 条规则


# ---------------------------------------------------------------------------
# CLI 集成测试
# ---------------------------------------------------------------------------

class TestCLIAlert:
    """测试 alert 子命令"""

    def test_alert_no_args_shows_help(self, capsys):
        rc = main(["alert"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "用法" in captured.out

    def test_alert_list_rules(self, capsys):
        rc = main(["alert", "--list-rules"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "告警规则" in captured.out
        assert "high_cpu" in captured.out

    def test_alert_summary(self, capsys):
        rc = main(["alert", "--summary"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "告警系统摘要" in captured.out

    def test_alert_test(self, capsys):
        rc = main(["alert", "--test"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "测试指标" in captured.out

    def test_alert_evaluate_triggers(self, capsys):
        rc = main(["alert", "--evaluate", '{"cpu_percent": 90}'])
        captured = capsys.readouterr()
        assert rc == 0
        assert "high_cpu" in captured.out or "critical_cpu" in captured.out

    def test_alert_evaluate_no_trigger(self, capsys):
        rc = main(["alert", "--evaluate", '{"cpu_percent": 50}'])
        captured = capsys.readouterr()
        assert rc == 0
        assert "无告警触发" in captured.out

    def test_alert_evaluate_invalid_json(self, capsys):
        rc = main(["alert", "--evaluate", "invalid json"])
        captured = capsys.readouterr()
        assert rc == 2
        assert "错误" in captured.err


# ---------------------------------------------------------------------------
# 帮助系统集成
# ---------------------------------------------------------------------------

class TestHelpIntegration:
    """测试帮助系统是否包含 alert 命令"""

    def test_help_all_contains_alert(self, capsys):
        rc = main(["help"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "alert" in captured.out

    def test_help_alert(self, capsys):
        rc = main(["help", "alert"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "alert" in captured.out
        assert "告警" in captured.out
