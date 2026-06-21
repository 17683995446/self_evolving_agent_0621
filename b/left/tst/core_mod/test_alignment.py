"""价值对齐与伦理约束模块测试"""
import pytest

from root.left.app.left.src.core_mod.alignment import (
    AlignmentModule,
    BiasDetector,
    EthicalConstraint,
    FairnessAuditor,
    ValueAlignment,
)
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestValueAlignment:
    """ValueAlignment 单元测试"""

    def test_init_normal(self) -> None:
        va = ValueAlignment({"values": {"safety": 1.0}, "min_score": 0.7})
        assert va.values["safety"] == 1.0
        assert va.min_score == 0.7

    def test_init_defaults(self) -> None:
        va = ValueAlignment({})
        assert "safety" in va.values
        assert va.min_score == 0.6

    def test_evaluate_aligned(self) -> None:
        va = ValueAlignment({})
        result = va.evaluate({"id": "a1", "metadata": {}})
        assert result["aligned"] is True
        assert result["total"] > 0.9

    def test_evaluate_flagged(self) -> None:
        va = ValueAlignment({"min_score": 0.8})
        result = va.evaluate({
            "id": "a1",
            "metadata": {"flagged_dimensions": ["safety"]}
        })
        assert result["aligned"] is False
        assert result["scores"]["safety"] == 0.0

    def test_alignment_rate(self) -> None:
        va = ValueAlignment({"min_score": 0.8})
        assert va.get_alignment_rate() == 1.0
        va.evaluate({"id": "a1", "metadata": {"flagged_dimensions": ["safety"]}})
        assert va.get_alignment_rate() == 0.0

    def test_history_trim(self) -> None:
        va = ValueAlignment({"max_history": 2})
        for i in range(5):
            va.evaluate({"id": f"a{i}", "metadata": {}})
        assert len(va.history) == 2

    def test_get_state(self) -> None:
        va = ValueAlignment({})
        s = va.get_state()
        assert "values" in s
        assert "alignment_rate" in s


class TestEthicalConstraint:
    """EthicalConstraint 单元测试"""

    def test_init_normal(self) -> None:
        ec = EthicalConstraint({"rules": [{"id": "r1", "pattern": "bad", "action": "block"}]})
        assert len(ec.rules) == 1

    def test_init_defaults(self) -> None:
        ec = EthicalConstraint({})
        assert len(ec.rules) == 3

    def test_check_allowed(self) -> None:
        ec = EthicalConstraint({})
        result = ec.check({"id": "a1", "description": "normal action"})
        assert result["allowed"] is True
        assert result["triggered_rules"] == []

    def test_check_blocked(self) -> None:
        ec = EthicalConstraint({})
        result = ec.check({"id": "a1", "description": "this will harm users"})
        assert result["allowed"] is False
        assert "no_harm" in result["triggered_rules"]

    def test_check_warn(self) -> None:
        ec = EthicalConstraint({})
        result = ec.check({"id": "a1", "description": "data leak detected"})
        assert result["allowed"] is True
        assert "privacy_protect" in result["triggered_rules"]

    def test_add_rule(self) -> None:
        ec = EthicalConstraint({})
        ec.add_rule({"id": "new", "pattern": "test", "action": "block"})
        assert len(ec.rules) == 4

    def test_add_rule_invalid(self) -> None:
        ec = EthicalConstraint({})
        with pytest.raises(ValidationError):
            ec.add_rule({"id": "new"})

    def test_remove_rule(self) -> None:
        ec = EthicalConstraint({})
        removed = ec.remove_rule("no_harm")
        assert removed is True
        assert len(ec.rules) == 2

    def test_remove_rule_missing(self) -> None:
        ec = EthicalConstraint({})
        removed = ec.remove_rule("missing")
        assert removed is False

    def test_violation_trim(self) -> None:
        ec = EthicalConstraint({"max_violations": 2})
        for i in range(5):
            ec.check({"id": f"a{i}", "description": "harm"})
        assert len(ec.violations) == 2

    def test_get_state(self) -> None:
        ec = EthicalConstraint({})
        s = ec.get_state()
        assert s["rule_count"] == 3


class TestBiasDetector:
    """BiasDetector 单元测试"""

    def test_init_normal(self) -> None:
        bd = BiasDetector({"threshold": 0.3, "min_samples": 5})
        assert bd.threshold == 0.3
        assert bd.min_samples == 5

    def test_detect_insufficient_groups(self) -> None:
        bd = BiasDetector({})
        bd.record("A", 1.0)
        assert bd.detect() is None

    def test_detect_insufficient_samples(self) -> None:
        bd = BiasDetector({"min_samples": 5})
        for i in range(3):
            bd.record("A", 1.0)
            bd.record("B", 0.0)
        assert bd.detect() is None

    def test_detect_no_bias(self) -> None:
        bd = BiasDetector({"threshold": 0.5, "min_samples": 5})
        for i in range(5):
            bd.record("A", 0.5)
            bd.record("B", 0.5)
        result = bd.detect()
        assert result is not None
        assert result["biased"] is False

    def test_detect_bias(self) -> None:
        bd = BiasDetector({"threshold": 0.1, "min_samples": 5})
        for i in range(5):
            bd.record("A", 1.0)
            bd.record("B", 0.0)
        result = bd.detect()
        assert result is not None
        assert result["biased"] is True
        assert result["gap"] == 1.0

    def test_record_trim(self) -> None:
        bd = BiasDetector({})
        for i in range(1005):
            bd.record("A", 1.0)
        assert len(bd.group_stats["A"]["outcomes"]) <= 1000

    def test_get_state(self) -> None:
        bd = BiasDetector({})
        s = bd.get_state()
        assert s["group_count"] == 0


class TestFairnessAuditor:
    """FairnessAuditor 单元测试"""

    def test_init_normal(self) -> None:
        fa = FairnessAuditor({"epsilon": 0.1})
        assert fa.epsilon == 0.1

    def test_audit_single_group(self) -> None:
        fa = FairnessAuditor({})
        result = fa.audit({"group": "A", "outcome": True})
        assert result["fair"] is True

    def test_audit_fair(self) -> None:
        fa = FairnessAuditor({"epsilon": 0.2})
        for i in range(10):
            fa.audit({"group": "A", "outcome": True})
            fa.audit({"group": "B", "outcome": True})
        result = fa.audit({"group": "A", "outcome": True})
        assert result["fair"] is True

    def test_audit_unfair(self) -> None:
        fa = FairnessAuditor({"epsilon": 0.01})
        for i in range(10):
            fa.audit({"group": "A", "outcome": True})
            fa.audit({"group": "B", "outcome": False})
        result = fa.audit({"group": "A", "outcome": True})
        assert result["fair"] is False

    def test_decision_trim(self) -> None:
        fa = FairnessAuditor({"max_decisions": 2})
        for i in range(5):
            fa.audit({"group": "A", "outcome": True})
        assert len(fa.decisions) == 2

    def test_get_state(self) -> None:
        fa = FairnessAuditor({})
        fa.audit({"group": "A", "outcome": True})
        s = fa.get_state()
        assert s["decision_count"] == 1


class TestAlignmentModule:
    """AlignmentModule 集成测试"""

    def test_init_normal(self) -> None:
        mod = AlignmentModule({})
        assert mod.value_alignment is not None
        assert mod.ethical is not None
        assert mod.bias is not None
        assert mod.fairness is not None

    def test_review_action_approved(self) -> None:
        mod = AlignmentModule({})
        result = mod.review_action({"id": "a1", "description": "normal", "metadata": {}})
        assert result["approved"] is True
        assert result["ethical"]["allowed"] is True
        assert result["value_alignment"]["aligned"] is True

    def test_review_action_blocked(self) -> None:
        mod = AlignmentModule({})
        result = mod.review_action({
            "id": "a1",
            "description": "harm users",
            "metadata": {"flagged_dimensions": ["safety"]}
        })
        assert result["approved"] is False
        assert result["ethical"]["allowed"] is False

    def test_review_action_value_only_fail(self) -> None:
        mod = AlignmentModule({"value_alignment": {"min_score": 0.8}})
        result = mod.review_action({
            "id": "a1",
            "description": "normal",
            "metadata": {"flagged_dimensions": ["safety"]}
        })
        assert result["approved"] is False
        assert result["ethical"]["allowed"] is True
        assert result["value_alignment"]["aligned"] is False

    def test_record_outcome_and_check_bias(self) -> None:
        mod = AlignmentModule({"bias": {"threshold": 0.1, "min_samples": 5}})
        for i in range(5):
            mod.record_outcome("A", 1.0)
            mod.record_outcome("B", 0.0)
        result = mod.check_bias()
        assert result is not None
        assert result["biased"] is True

    def test_audit_decision(self) -> None:
        mod = AlignmentModule({"fairness": {"epsilon": 0.01}})
        for i in range(10):
            mod.audit_decision({"group": "A", "outcome": True})
            mod.audit_decision({"group": "B", "outcome": False})
        result = mod.audit_decision({"group": "A", "outcome": True})
        assert result["fair"] is False

    def test_get_state(self) -> None:
        mod = AlignmentModule({})
        s = mod.get_state()
        assert "value_alignment" in s
        assert "ethical" in s
        assert "bias" in s
        assert "fairness" in s

    def test_boundary_empty_action(self) -> None:
        mod = AlignmentModule({})
        result = mod.review_action({"id": "a1", "description": "", "metadata": {}})
        assert result["approved"] is True

    def test_boundary_missing_description(self) -> None:
        mod = AlignmentModule({})
        result = mod.review_action({"id": "a1", "metadata": {}})
        assert result["approved"] is True

    def test_boundary_large_history(self) -> None:
        mod = AlignmentModule({"value_alignment": {"max_history": 5}})
        for i in range(100):
            mod.review_action({"id": f"a{i}", "description": "normal", "metadata": {}})
        assert len(mod.value_alignment.history) <= 5
