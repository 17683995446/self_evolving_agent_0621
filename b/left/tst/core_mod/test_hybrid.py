"""神经符号混合推理模块测试"""
import pytest

from root.left.app.left.src.core_mod.hybrid import (
    HybridInferenceModule,
    LogicParser,
    NeuralSymbolicBridge,
    RuleInductor,
    SymbolicReasoner,
)
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestLogicParser:
    """LogicParser 单元测试"""

    def test_init_normal(self) -> None:
        lp = LogicParser({"max_cache": 50})
        assert lp.max_cache == 50

    def test_parse_atom(self) -> None:
        lp = LogicParser({})
        result = lp.parse("A")
        assert result["tokens"] == ["A"]
        assert result["tree"]["type"] == "atom"

    def test_parse_op(self) -> None:
        lp = LogicParser({})
        result = lp.parse("A AND B")
        assert "AND" in result["tokens"]
        assert result["tree"]["type"] == "op"
        assert result["tree"]["op"] == "AND"

    def test_parse_parens(self) -> None:
        lp = LogicParser({})
        result = lp.parse("( A AND B )")
        assert result["tree"]["type"] == "op"

    def test_cache(self) -> None:
        lp = LogicParser({})
        r1 = lp.parse("A AND B")
        r2 = lp.parse("A AND B")
        assert r1 is r2

    def test_cache_trim(self) -> None:
        lp = LogicParser({"max_cache": 2})
        lp.parse("A")
        lp.parse("B")
        lp.parse("C")
        assert len(lp.parsed_cache) == 2

    def test_get_state(self) -> None:
        lp = LogicParser({})
        s = lp.get_state()
        assert s["cache_size"] == 0


class TestSymbolicReasoner:
    """SymbolicReasoner 单元测试"""

    def test_init_normal(self) -> None:
        sr = SymbolicReasoner({"initial_facts": ["A"], "rules": [{"id": "r1", "if": ["A"], "then": "B"}]})
        assert "A" in sr.facts
        assert len(sr.rules) == 1

    def test_add_fact(self) -> None:
        sr = SymbolicReasoner({})
        sr.add_fact("X")
        assert "X" in sr.facts

    def test_add_rule_invalid(self) -> None:
        sr = SymbolicReasoner({})
        with pytest.raises(ValidationError):
            sr.add_rule({"id": "r1"})

    def test_infer_chain(self) -> None:
        sr = SymbolicReasoner({
            "initial_facts": ["A"],
            "rules": [
                {"id": "r1", "if": ["A"], "then": "B"},
                {"id": "r2", "if": ["B"], "then": "C"},
            ]
        })
        new = sr.infer()
        assert "B" in new
        assert "C" in new
        assert sr.query("C") is True

    def test_infer_no_new(self) -> None:
        sr = SymbolicReasoner({"initial_facts": ["A"]})
        new = sr.infer()
        assert new == []

    def test_query(self) -> None:
        sr = SymbolicReasoner({"initial_facts": ["A"]})
        assert sr.query("A") is True
        assert sr.query("Z") is False

    def test_get_state(self) -> None:
        sr = SymbolicReasoner({})
        s = sr.get_state()
        assert s["fact_count"] == 0


class TestNeuralSymbolicBridge:
    """NeuralSymbolicBridge 单元测试"""

    def test_init_normal(self) -> None:
        bridge = NeuralSymbolicBridge({"vector_dim": 4})
        assert bridge.vector_dim == 4

    def test_symbol_to_vector(self) -> None:
        bridge = NeuralSymbolicBridge({})
        vec = bridge.symbol_to_vector("cat")
        assert len(vec) == 8

    def test_symbol_consistent(self) -> None:
        bridge = NeuralSymbolicBridge({})
        v1 = bridge.symbol_to_vector("dog")
        v2 = bridge.symbol_to_vector("dog")
        assert v1 == v2

    def test_vector_to_symbol(self) -> None:
        bridge = NeuralSymbolicBridge({})
        vec = bridge.symbol_to_vector("cat")
        result = bridge.vector_to_symbol(vec, ["cat", "dog", "bird"])
        assert result == "cat"

    def test_vector_to_symbol_empty(self) -> None:
        bridge = NeuralSymbolicBridge({})
        assert bridge.vector_to_symbol([1.0, 2.0], []) == "unknown"

    def test_symbol_trim(self) -> None:
        bridge = NeuralSymbolicBridge({"max_symbols": 2})
        bridge.symbol_to_vector("a")
        bridge.symbol_to_vector("b")
        bridge.symbol_to_vector("c")
        assert len(bridge.symbol_table) == 2

    def test_get_state(self) -> None:
        bridge = NeuralSymbolicBridge({})
        s = bridge.get_state()
        assert s["vector_dim"] == 8


class TestRuleInductor:
    """RuleInductor 单元测试"""

    def test_init_normal(self) -> None:
        ri = RuleInductor({"min_support": 5, "confidence_threshold": 0.8})
        assert ri.min_support == 5
        assert ri.confidence_threshold == 0.8

    def test_induce_empty(self) -> None:
        ri = RuleInductor({})
        assert ri.induce([]) == []

    def test_induce_rule(self) -> None:
        ri = RuleInductor({"min_support": 3, "confidence_threshold": 0.6})
        data = [
            {"conditions": ["A", "B"], "outcome": "C"},
            {"conditions": ["A", "B"], "outcome": "C"},
            {"conditions": ["A", "B"], "outcome": "C"},
            {"conditions": ["A", "B"], "outcome": "D"},
        ]
        rules = ri.induce(data)
        assert len(rules) >= 1
        assert rules[0]["then"] == "C"
        assert rules[0]["confidence"] >= 0.6

    def test_induce_no_rule(self) -> None:
        ri = RuleInductor({"min_support": 10})
        data = [{"conditions": ["A"], "outcome": "B"}]
        assert ri.induce(data) == []

    def test_rule_trim(self) -> None:
        ri = RuleInductor({"max_rules": 2, "min_support": 1, "confidence_threshold": 0.5})
        for i in range(5):
            ri.induce([{"conditions": [f"A{i}"], "outcome": "B"}])
        assert len(ri.rules) == 2

    def test_get_state(self) -> None:
        ri = RuleInductor({})
        s = ri.get_state()
        assert s["rule_count"] == 0


class TestHybridInferenceModule:
    """HybridInferenceModule 集成测试"""

    def test_init_normal(self) -> None:
        mod = HybridInferenceModule({})
        assert mod.parser is not None
        assert mod.reasoner is not None
        assert mod.bridge is not None
        assert mod.inductor is not None

    def test_parse_and_infer(self) -> None:
        mod = HybridInferenceModule({
            "reasoner": {
                "initial_facts": ["A"],
                "rules": [{"id": "r1", "if": ["A"], "then": "B"}]
            }
        })
        result = mod.parse_and_infer("A AND B")
        assert "parsed" in result
        assert "B" in result["inferred"]

    def test_neural_to_symbolic(self) -> None:
        mod = HybridInferenceModule({})
        vec = mod.symbolic_to_neural("cat")
        result = mod.neural_to_symbolic(vec, ["cat", "dog"])
        assert result == "cat"

    def test_learn_rules(self) -> None:
        mod = HybridInferenceModule({})
        data = [
            {"conditions": ["A", "B"], "outcome": "C"},
            {"conditions": ["A", "B"], "outcome": "C"},
            {"conditions": ["A", "B"], "outcome": "C"},
        ]
        rules = mod.learn_rules(data)
        assert len(rules) >= 1

    def test_add_fact_and_query(self) -> None:
        mod = HybridInferenceModule({})
        mod.add_fact("X")
        assert mod.query("X") is True
        assert mod.query("Y") is False

    def test_get_state(self) -> None:
        mod = HybridInferenceModule({})
        s = mod.get_state()
        assert "parser" in s
        assert "reasoner" in s
        assert "bridge" in s
        assert "inductor" in s

    def test_boundary_empty_expression(self) -> None:
        mod = HybridInferenceModule({})
        result = mod.parse_and_infer("")
        assert result["parsed"]["tree"]["type"] == "empty"

    def test_boundary_single_condition_rule(self) -> None:
        mod = HybridInferenceModule({})
        data = [{"conditions": ["A"], "outcome": "B"}]
        rules = mod.learn_rules(data)
        assert rules == []
