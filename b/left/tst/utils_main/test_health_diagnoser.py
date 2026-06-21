"""健康诊断器测试"""
from root.left.app.left.src.utils_main.health_diagnoser import HealthDiagnoser, DiagnosticItem


class TestDiagnosticItem:
    """测试 DiagnosticItem"""

    def test_to_dict_passed(self) -> None:
        item = DiagnosticItem("test", True, "OK")
        d = item.to_dict()
        assert d["name"] == "test"
        assert d["passed"] is True
        assert d["message"] == "OK"
        assert d["detail"] == ""

    def test_to_dict_failed_with_detail(self) -> None:
        item = DiagnosticItem("test", False, "FAIL", "some detail")
        d = item.to_dict()
        assert d["passed"] is False
        assert d["detail"] == "some detail"


class TestHealthDiagnoser:
    """测试 HealthDiagnoser"""

    def test_run_full_diagnosis_with_agent(self) -> None:
        from root.left.app.left.src.main import SelfEvolvingAgent

        agent = SelfEvolvingAgent()
        try:
            diagnoser = HealthDiagnoser()
            items = diagnoser.run_full_diagnosis(agent)
            assert len(items) == 6
            names = [i.name for i in items]
            assert "python_version" in names
            assert "dependencies" in names
            assert "config" in names
            assert "modules_compliance" in names
            assert "modules_health" in names
            assert "modules_state" in names
        finally:
            agent.close()

    def test_all_items_pass_for_healthy_agent(self) -> None:
        from root.left.app.left.src.main import SelfEvolvingAgent

        agent = SelfEvolvingAgent()
        try:
            diagnoser = HealthDiagnoser()
            items = diagnoser.run_full_diagnosis(agent)
            for item in items:
                assert item.passed, f"{item.name} should pass: {item.message}"
        finally:
            agent.close()

    def test_format_report_all_passed(self) -> None:
        items = [
            DiagnosticItem("a", True, "OK"),
            DiagnosticItem("b", True, "OK"),
        ]
        diagnoser = HealthDiagnoser()
        report = diagnoser.format_report(items)
        assert "所有检查通过" in report
        assert "PASS" in report

    def test_format_report_has_failures(self) -> None:
        items = [
            DiagnosticItem("a", True, "OK"),
            DiagnosticItem("b", False, "BAD", "fix me"),
        ]
        diagnoser = HealthDiagnoser()
        report = diagnoser.format_report(items)
        assert "FAIL" in report
        assert "1 项检查失败" in report
        assert "fix me" in report

    def test_to_dict(self) -> None:
        items = [
            DiagnosticItem("a", True, "OK"),
            DiagnosticItem("b", False, "BAD"),
        ]
        diagnoser = HealthDiagnoser()
        d = diagnoser.to_dict(items)
        assert d["all_passed"] is False
        assert d["total"] == 2
        assert d["passed"] == 1
        assert d["failed"] == 1
        assert len(d["items"]) == 2
