"""自我建模与元认知模块测试"""

from root.left.app.left.src.core_mod.selfaware import (
    ConfidenceEstimator,
    IntrospectionEngine,
    MetaCognition,
    SelfAwarenessModule,
    SelfModel,
)


class TestSelfModel:
    """SelfModel 单元测试"""

    def test_init_normal(self) -> None:
        sm = SelfModel({"capabilities": {"a": 0.8}, "task_capacity": 50})
        assert sm.capabilities["a"] == 0.8
        assert sm.resources["task_capacity"] == 50.0

    def test_update_capability(self) -> None:
        sm = SelfModel({})
        sm.update_capability("prediction", 0.9)
        assert sm.capabilities["prediction"] == 0.9

    def test_update_capability_clip(self) -> None:
        sm = SelfModel({})
        sm.update_capability("prediction", 1.5)
        assert sm.capabilities["prediction"] == 1.0
        sm.update_capability("prediction", -0.5)
        assert sm.capabilities["prediction"] == 0.0

    def test_record_performance(self) -> None:
        sm = SelfModel({})
        sm.record_performance(0.8)
        assert len(sm.performance_log) == 1

    def test_performance_trim(self) -> None:
        sm = SelfModel({"max_log": 3})
        for i in range(5):
            sm.record_performance(float(i) * 0.1)
        assert len(sm.performance_log) == 3

    def test_get_trend_positive(self) -> None:
        sm = SelfModel({})
        for i in range(20):
            sm.record_performance(float(i) * 0.01)
        trend = sm.get_trend()
        assert trend > 0.0

    def test_get_trend_negative(self) -> None:
        sm = SelfModel({})
        for i in range(20):
            sm.record_performance(1.0 - float(i) * 0.01)
        trend = sm.get_trend()
        assert trend < 0.0

    def test_get_trend_insufficient(self) -> None:
        sm = SelfModel({})
        assert sm.get_trend() == 0.0

    def test_get_state(self) -> None:
        sm = SelfModel({})
        s = sm.get_state()
        assert "capabilities" in s
        assert "trend" in s


class TestConfidenceEstimator:
    """ConfidenceEstimator 单元测试"""

    def test_init_normal(self) -> None:
        ce = ConfidenceEstimator({"confidence_threshold": 0.8})
        assert ce.confidence_threshold == 0.8

    def test_estimate_no_data(self) -> None:
        ce = ConfidenceEstimator({})
        assert ce.estimate("t1") == 0.5

    def test_estimate_perfect(self) -> None:
        ce = ConfidenceEstimator({})
        for _ in range(5):
            ce.record_prediction("t1", 1.0, 1.0)
        conf = ce.estimate("t1")
        assert conf > 0.99
        assert ce.is_confident("t1") is True

    def test_estimate_poor(self) -> None:
        ce = ConfidenceEstimator({"confidence_threshold": 0.9})
        for _ in range(5):
            ce.record_prediction("t1", 0.0, 1.0)
        conf = ce.estimate("t1")
        assert conf < 0.5
        assert ce.is_confident("t1") is False

    def test_history_trim(self) -> None:
        ce = ConfidenceEstimator({"max_history": 3})
        for i in range(5):
            ce.record_prediction("t1", float(i), float(i) + 1.0)
        assert len(ce.prediction_history["t1"]) == 3

    def test_get_state(self) -> None:
        ce = ConfidenceEstimator({})
        ce.record_prediction("t1", 1.0, 1.0)
        s = ce.get_state()
        assert s["tracked_tasks"] == 1


class TestIntrospectionEngine:
    """IntrospectionEngine 单元测试"""

    def test_init_normal(self) -> None:
        ie = IntrospectionEngine({"bias_patterns": {"custom": {"threshold": 0.5, "count": 0}}})
        assert "custom" in ie.bias_patterns

    def test_analyze_insufficient(self) -> None:
        ie = IntrospectionEngine({})
        result = ie.analyze()
        assert result["recommendation"] == "insufficient data"

    def test_detect_overconfidence(self) -> None:
        ie = IntrospectionEngine({})
        for i in range(10):
            ie.log_decision({"confidence": 0.95, "action": "a"})
        result = ie.analyze()
        assert "overconfidence" in result["biases_detected"]
        assert result["recommendation"] == "reduce exploration"

    def test_detect_neglect(self) -> None:
        ie = IntrospectionEngine({})
        for i in range(10):
            ie.log_decision({"confidence": 0.05, "action": "a"})
        result = ie.analyze()
        assert "neglect" in result["biases_detected"]
        assert result["recommendation"] == "increase exploration"

    def test_detect_none(self) -> None:
        ie = IntrospectionEngine({})
        for i in range(10):
            ie.log_decision({"confidence": 0.5, "action": "a"})
        result = ie.analyze()
        assert result["biases_detected"] == []
        assert result["recommendation"] == "maintain"

    def test_log_trim(self) -> None:
        ie = IntrospectionEngine({"max_log": 3})
        for i in range(5):
            ie.log_decision({"id": i})
        assert len(ie.decision_log) == 3

    def test_get_state(self) -> None:
        ie = IntrospectionEngine({})
        s = ie.get_state()
        assert s["decision_log_size"] == 0


class TestMetaCognition:
    """MetaCognition 单元测试"""

    def test_init_normal(self) -> None:
        mc = MetaCognition({"strategy": "aggressive"})
        assert mc.strategy == "aggressive"

    def test_evaluate_conservative(self) -> None:
        mc = MetaCognition({})
        sm = SelfModel({})
        for i in range(20):
            sm.record_performance(0.5 - float(i) * 0.03)
        ce = ConfidenceEstimator({})
        result = mc.evaluate_and_adjust(sm, ce)
        assert result["new_strategy"] == "conservative"
        assert result["changed"] is True

    def test_evaluate_aggressive(self) -> None:
        mc = MetaCognition({})
        sm = SelfModel({"capabilities": {"prediction": 0.9}})
        for i in range(20):
            sm.record_performance(0.5 + float(i) * 0.03)
        ce = ConfidenceEstimator({})
        result = mc.evaluate_and_adjust(sm, ce)
        assert result["new_strategy"] == "aggressive"

    def test_evaluate_balanced(self) -> None:
        mc = MetaCognition({})
        sm = SelfModel({})
        for i in range(20):
            sm.record_performance(0.5)
        ce = ConfidenceEstimator({})
        result = mc.evaluate_and_adjust(sm, ce)
        assert result["new_strategy"] == "balanced"

    def test_adjustment_history_trim(self) -> None:
        mc = MetaCognition({"max_history": 2})
        sm = SelfModel({})
        ce = ConfidenceEstimator({})
        for _ in range(5):
            mc.evaluate_and_adjust(sm, ce)
        assert len(mc.adjustment_history) == 2

    def test_get_state(self) -> None:
        mc = MetaCognition({})
        s = mc.get_state()
        assert s["current_strategy"] == "balanced"
        assert "aggressive" in s["available_strategies"]


class TestSelfAwarenessModule:
    """SelfAwarenessModule 集成测试"""

    def test_init_normal(self) -> None:
        mod = SelfAwarenessModule({})
        assert mod.self_model is not None
        assert mod.confidence is not None
        assert mod.introspection is not None
        assert mod.meta is not None

    def test_observe_outcome(self) -> None:
        mod = SelfAwarenessModule({})
        result = mod.observe_outcome("t1", 1.0, 1.0, 0.8)
        assert result["task_id"] == "t1"
        assert result["confidence"] > 0.9
        assert result["is_confident"] is True

    def test_observe_outcome_poor(self) -> None:
        mod = SelfAwarenessModule({"confidence": {"confidence_threshold": 0.9}})
        for _ in range(5):
            mod.observe_outcome("t1", 0.0, 1.0, 0.2)
        result = mod.observe_outcome("t1", 0.0, 1.0, 0.2)
        assert result["is_confident"] is False

    def test_reflect(self) -> None:
        mod = SelfAwarenessModule({})
        for i in range(10):
            mod.reflect({"confidence": 0.95, "action": f"a{i}"})
        result = mod.reflect({"confidence": 0.95, "action": "last"})
        assert "introspection" in result
        assert "adjustment" in result
        assert "overconfidence" in result["introspection"]["biases_detected"]

    def test_update_capability(self) -> None:
        mod = SelfAwarenessModule({})
        mod.update_capability("prediction", 0.9)
        assert mod.self_model.capabilities["prediction"] == 0.9

    def test_update_resource(self) -> None:
        mod = SelfAwarenessModule({})
        mod.update_resource("cpu_usage", 50.0)
        assert mod.self_model.resources["cpu_usage"] == 50.0

    def test_get_state(self) -> None:
        mod = SelfAwarenessModule({})
        s = mod.get_state()
        assert "self_model" in s
        assert "confidence" in s
        assert "introspection" in s
        assert "meta" in s

    def test_boundary_single_record(self) -> None:
        mod = SelfAwarenessModule({})
        result = mod.observe_outcome("t1", 1.0, 1.0, 0.5)
        assert result["confidence"] == 1.0

    def test_boundary_empty_decision(self) -> None:
        mod = SelfAwarenessModule({})
        result = mod.reflect({})
        assert "introspection" in result
