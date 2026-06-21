"""形式化验证与可解释性模块单元测试"""
import pytest

from root.left.app.left.src.core_mod.verify import (
    SafetyInvariant, LivenessProperty, DecisionTracer,
    FeatureAttributor, VerificationModule,
)
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestSafetyInvariant:
    """测试安全性不变式"""

    def test_normal_safe(self) -> None:
        inv = SafetyInvariant({})
        inv.register("cpu_ok", lambda s: s.get("cpu", 0) < 1.0)
        result = inv.check({"cpu": 0.5})
        assert result["safe"] is True
        assert result["checks"]["cpu_ok"] == "safe"

    def test_violated(self) -> None:
        inv = SafetyInvariant({})
        inv.register("cpu_ok", lambda s: s.get("cpu", 0) < 1.0)
        result = inv.check({"cpu": 1.5})
        assert result["safe"] is False
        assert result["checks"]["cpu_ok"] == "VIOLATED"
        assert len(inv.get_violations()) == 1

    def test_exception_in_check(self) -> None:
        inv = SafetyInvariant({})
        inv.register("bad", lambda s: s["missing"] > 0)
        result = inv.check({})
        assert result["safe"] is False

    def test_violations_bounded(self) -> None:
        inv = SafetyInvariant({"max_violations": 2})
        inv.register("v", lambda s: False)
        for _ in range(5):
            inv.check({})
        assert len(inv.get_violations()) == 2


class TestLivenessProperty:
    """测试活性属性"""

    def test_satisfied(self) -> None:
        lp = LivenessProperty({})
        lp.register("perf_improved", lambda s: s.get("perf", 0) > 0.5, 10)
        result = lp.check(1, {"perf": 0.6})
        assert result["alive"] is True
        assert result["checks"]["perf_improved"] == "satisfied"

    def test_pending(self) -> None:
        lp = LivenessProperty({})
        lp.register("perf_improved", lambda s: s.get("perf", 0) > 0.5, 10)
        result = lp.check(1, {"perf": 0.3})
        assert result["checks"]["perf_improved"] == "pending"

    def test_timeout(self) -> None:
        lp = LivenessProperty({})
        lp.register("perf_improved", lambda s: s.get("perf", 0) > 0.5, 2)
        lp.check(1, {"perf": 0.3})
        result = lp.check(5, {"perf": 0.3})
        assert result["alive"] is False
        assert result["checks"]["perf_improved"] == "TIMEOUT"

    def test_already_satisfied(self) -> None:
        lp = LivenessProperty({})
        lp.register("perf_improved", lambda s: s.get("perf", 0) > 0.5, 10)
        lp.check(1, {"perf": 0.6})
        result = lp.check(2, {"perf": 0.3})
        assert result["checks"]["perf_improved"] == "satisfied"


class TestDecisionTracer:
    """测试决策追踪"""

    def test_trace_and_explain(self) -> None:
        dt = DecisionTracer({})
        dt.trace("select_task", {"pool_size": 5}, "task_1", "highest priority")
        explain = dt.explain_last()
        assert "select_task" in explain
        assert "highest priority" in explain

    def test_trace_bounded(self) -> None:
        dt = DecisionTracer({"max_traces": 2})
        for i in range(5):
            dt.trace("step", {}, i, "reason")
        assert len(dt.get_all_traces()) == 2

    def test_empty_explain(self) -> None:
        dt = DecisionTracer({})
        assert dt.explain_last() == "No trace available"


class TestFeatureAttributor:
    """测试特征归因"""

    def test_gradient_method(self) -> None:
        fa = FeatureAttributor({"method": "gradient"})
        features = [1.0, 2.0, 3.0]
        names = ["a", "b", "c"]

        def predict_fn(x):
            return sum(x)

        attrs = fa.attribute(features, names, predict_fn)
        assert len(attrs) == 3
        assert abs(sum(attrs.values()) - 1.0) < 0.01

    def test_perturbation_method(self) -> None:
        fa = FeatureAttributor({"method": "perturbation"})
        features = [1.0, 2.0]
        names = ["a", "b"]

        def predict_fn(x):
            return x[0] * 2 + x[1] * 0.5

        attrs = fa.attribute(features, names, predict_fn)
        assert len(attrs) == 2
        assert attrs["a"] > attrs["b"]

    def test_unknown_method(self) -> None:
        fa = FeatureAttributor({"method": "unknown"})
        attrs = fa.attribute([1.0], ["a"], lambda x: x[0])
        assert attrs["a"] == 0.0


class TestVerificationModule:
    """测试验证模块主控"""

    def test_normal_init(self) -> None:
        mod = VerificationModule({})
        assert mod.safety is not None

    def test_safety_check(self) -> None:
        mod = VerificationModule({})
        mod.register_safety("cpu_ok", lambda s: s.get("cpu", 0) < 1.0)
        result = mod.check_safety({"cpu": 0.5})
        assert result["safe"] is True

    def test_liveness_check(self) -> None:
        mod = VerificationModule({})
        mod.register_liveness("improved", lambda s: s.get("p", 0) > 0.5, 10)
        result = mod.check_liveness(1, {"p": 0.6})
        assert result["alive"] is True

    def test_trace_and_explain(self) -> None:
        mod = VerificationModule({})
        mod.trace_decision("test", {}, "out", "reason")
        assert "test" in mod.explain_decision()

    def test_attribute(self) -> None:
        mod = VerificationModule({})
        attrs = mod.attribute_features([1.0, 2.0], ["a", "b"], lambda x: sum(x))
        assert len(attrs) == 2

    def test_verification_state(self) -> None:
        mod = VerificationModule({})
        state = mod.get_verification_state()
        assert "safety_violations" in state
        assert "trace_count" in state

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            VerificationModule(None)
