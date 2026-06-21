"""模块合规检查器测试

验证 ModuleComplianceInspector 能否正确识别模块是否实现了
统一接口：get_state / reset / health_check。
"""
from root.left.app.left.src.utils_main.module_inspector import (
    ModuleComplianceInspector,
    ModuleComplianceReport,
)


class CompliantModule:
    """完全合规的模块"""

    def get_state(self):
        return {}

    def reset(self):
        pass

    def health_check(self):
        return True


class MissingResetModule:
    """缺少 reset 的模块"""

    def get_state(self):
        return {}

    def health_check(self):
        return True


class MissingAllModule:
    """缺少所有方法的模块"""
    pass


class NotCallableModule:
    """方法存在但不是可调用的模块"""

    get_state = "not a method"
    reset = "not a method"
    health_check = "not a method"


class TestModuleComplianceReport:
    """测试合规报告"""

    def test_to_dict(self):
        report = ModuleComplianceReport("test", True, [])
        assert report.to_dict() == {"name": "test", "passed": True, "missing": []}


class TestModuleComplianceInspector:
    """测试模块合规检查器"""

    def test_compliant_module_passes(self):
        inspector = ModuleComplianceInspector()
        report = inspector.inspect("good", CompliantModule())
        assert report.passed is True
        assert report.missing == []

    def test_missing_single_method(self):
        inspector = ModuleComplianceInspector()
        report = inspector.inspect("missing_reset", MissingResetModule())
        assert report.passed is False
        assert "reset" in report.missing
        assert "get_state" not in report.missing
        assert "health_check" not in report.missing

    def test_missing_all_methods(self):
        inspector = ModuleComplianceInspector()
        report = inspector.inspect("bad", MissingAllModule())
        assert report.passed is False
        assert set(report.missing) == {"get_state", "reset", "health_check"}

    def test_not_callable_methods(self):
        inspector = ModuleComplianceInspector()
        report = inspector.inspect("not_callable", NotCallableModule())
        assert report.passed is False
        assert len(report.missing) == 3
        assert all("not callable" in m for m in report.missing)

    def test_inspect_many(self):
        modules = {
            "good": CompliantModule(),
            "bad": MissingAllModule(),
        }
        inspector = ModuleComplianceInspector()
        reports = inspector.inspect_many(modules)
        assert len(reports) == 2
        assert reports[0].name == "good"
        assert reports[1].name == "bad"

    def test_is_fully_compliant_true(self):
        modules = {"a": CompliantModule(), "b": CompliantModule()}
        inspector = ModuleComplianceInspector()
        assert inspector.is_fully_compliant(modules) is True

    def test_is_fully_compliant_false(self):
        modules = {"a": CompliantModule(), "b": MissingAllModule()}
        inspector = ModuleComplianceInspector()
        assert inspector.is_fully_compliant(modules) is False

    def test_list_violations(self):
        modules = {"a": CompliantModule(), "b": MissingAllModule()}
        inspector = ModuleComplianceInspector()
        violations = inspector.list_violations(modules)
        assert len(violations) == 1
        assert violations[0].name == "b"

    def test_required_methods_constant(self):
        assert ModuleComplianceInspector.REQUIRED_METHODS == (
            "get_state",
            "reset",
            "health_check",
        )
