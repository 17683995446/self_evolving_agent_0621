"""因果推理模块单元测试"""
import pytest

from root.left.app.left.src.core_mod.causal import (
    CausalGraph, InterventionSimulator, CounterfactualAnalyzer,
    CausalEffectEstimator, CausalDiscovery, CausalModule,
)
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestCausalGraph:
    """测试因果图"""

    def test_normal_add_edge(self) -> None:
        g = CausalGraph({})
        g.add_edge("A", "B", 0.5)
        assert "A" in g.nodes
        assert "B" in g.nodes
        assert "B" in g.edges["A"]

    def test_get_parents(self) -> None:
        g = CausalGraph({})
        g.add_edge("A", "C")
        g.add_edge("B", "C")
        assert sorted(g.get_parents("C")) == ["A", "B"]

    def test_get_children(self) -> None:
        g = CausalGraph({})
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        assert sorted(g.get_children("A")) == ["B", "C"]

    def test_no_cycle(self) -> None:
        g = CausalGraph({})
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        assert g.has_cycle() is False

    def test_cycle_detected(self) -> None:
        g = CausalGraph({})
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("C", "A")
        assert g.has_cycle() is True

    def test_to_dict(self) -> None:
        g = CausalGraph({})
        g.add_edge("A", "B", 0.5)
        d = g.to_dict()
        assert "nodes" in d
        assert "edges" in d

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            CausalGraph(None)


class TestInterventionSimulator:
    """测试干预模拟器"""

    def test_normal_intervention(self) -> None:
        g = CausalGraph({})
        g.add_edge("cpu", "performance", 0.5)
        sim = InterventionSimulator({})
        state = {"cpu": 0.3, "performance": 0.5}
        result = sim.do_intervention(g, state, {"cpu": 0.8})
        assert result["cpu"] == 0.8
        assert result["performance"] > 0.5

    def test_no_intervention(self) -> None:
        g = CausalGraph({})
        sim = InterventionSimulator({})
        state = {"cpu": 0.3}
        result = sim.do_intervention(g, state, {})
        assert result == state


class TestCounterfactualAnalyzer:
    """测试反事实分析器"""

    def test_what_if(self) -> None:
        g = CausalGraph({})
        g.add_edge("exploration", "performance", 0.3)
        cf = CounterfactualAnalyzer({})
        state = {"exploration": 0.3, "performance": 0.5}
        result = cf.analyze(g, state, {"exploration": 0.6}, "performance")
        assert "effect" in result
        assert result["factual"] == 0.5

    def test_negative_effect(self) -> None:
        g = CausalGraph({})
        g.add_edge("load", "performance", -0.5)
        cf = CounterfactualAnalyzer({})
        state = {"load": 0.2, "performance": 0.8}
        result = cf.analyze(g, state, {"load": 0.8}, "performance")
        assert result["effect"] < 0


class TestCausalEffectEstimator:
    """测试因果效应估计器"""

    def test_normal_ate(self) -> None:
        est = CausalEffectEstimator({"min_samples": 10})
        data = []
        for i in range(50):
            data.append({"treatment": 1.0, "outcome": 0.8 + (i % 5) * 0.01})
        for i in range(50):
            data.append({"treatment": 0.0, "outcome": 0.5 + (i % 5) * 0.01})
        ate = est.estimate_ate(data, "treatment", "outcome")
        assert ate is not None
        assert ate > 0

    def test_insufficient_data(self) -> None:
        est = CausalEffectEstimator({"min_samples": 100})
        data = [{"treatment": 1.0, "outcome": 1.0}]
        ate = est.estimate_ate(data, "treatment", "outcome")
        assert ate is None

    def test_no_control_group(self) -> None:
        est = CausalEffectEstimator({"min_samples": 1})
        data = [{"treatment": 1.0, "outcome": 1.0}]
        ate = est.estimate_ate(data, "treatment", "outcome")
        assert ate is None


class TestCausalDiscovery:
    """测试因果发现"""

    def test_discover_correlation(self) -> None:
        cd = CausalDiscovery({"correlation_threshold": 0.5})
        data = []
        for i in range(100):
            x = float(i) / 100.0
            data.append({"A": x, "B": x * 0.9 + 0.01})
        g = cd.discover_from_data(data, ["A", "B"])
        assert len(g.edge_weights) > 0

    def test_no_correlation(self) -> None:
        cd = CausalDiscovery({"correlation_threshold": 0.9})
        import random
        data = [{"A": random.random(), "B": random.random()} for _ in range(100)]
        g = cd.discover_from_data(data, ["A", "B"])
        assert len(g.edge_weights) == 0

    def test_insufficient_data(self) -> None:
        cd = CausalDiscovery({})
        g = cd.discover_from_data([{"A": 1.0}], ["A", "B"])
        assert len(g.nodes) == 0


class TestCausalModule:
    """测试因果模块主控"""

    def test_normal_init(self) -> None:
        mod = CausalModule({})
        assert mod.graph is not None

    def test_build_graph(self) -> None:
        mod = CausalModule({"discovery": {"correlation_threshold": 0.5}})
        data = [{"A": float(i) / 100, "B": float(i) / 100} for i in range(100)]
        g = mod.build_graph(data, ["A", "B"])
        assert isinstance(g, CausalGraph)

    def test_simulate_intervention(self) -> None:
        mod = CausalModule({})
        mod.graph.add_edge("X", "Y", 0.5)
        result = mod.simulate_intervention({"X": 0.2, "Y": 0.3}, {"X": 0.8})
        assert result["X"] == 0.8

    def test_what_if(self) -> None:
        mod = CausalModule({})
        mod.graph.add_edge("X", "Y", 0.5)
        result = mod.what_if({"X": 0.2, "Y": 0.3}, {"X": 0.8}, "Y")
        assert "effect" in result

    def test_estimate_effect(self) -> None:
        mod = CausalModule({"effect": {"min_samples": 10}})
        data = [{"T": 1.0, "O": 1.0} for _ in range(20)] + [{"T": 0.0, "O": 0.5} for _ in range(20)]
        ate = mod.estimate_effect(data, "T", "O")
        assert ate is not None

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            CausalModule(None)
