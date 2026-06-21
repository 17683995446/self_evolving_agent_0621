"""神经符号混合推理模块"""
from typing import Any, Dict, Final, List

import numpy as np

from root.left.app.left.src.utils_main.exceptions import ValidationError
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class LogicParser:
    """逻辑解析器（解析简单命题逻辑表达式）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[LogicParser.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.parsed_cache: Dict[str, Any] = {}
        self.max_cache: int = int(config.get("max_cache", 200))
        logger.info("LogicParser initialized", "hybrid")

    def parse(self, expression: str) -> Dict[str, Any]:
        logger.debug(f"[LogicParser.parse] expr={expression}")
        Validator.require_type(expression, str, "expression")
        if expression in self.parsed_cache:
            return self.parsed_cache[expression]
        tokens = self._tokenize(expression)
        tree = self._build_tree(tokens)
        result = {"expression": expression, "tokens": tokens, "tree": tree}
        self._add_cache(expression, result)
        logger.debug(f"[LogicParser.parse] tokens={len(tokens)}")
        return result

    def _tokenize(self, expression: str) -> List[str]:
        cleaned = expression.replace("(", " ( ").replace(")", " ) ")
        return [t for t in cleaned.split() if t]

    def _build_tree(self, tokens: List[str]) -> Dict[str, Any]:
        if not tokens:
            return {"type": "empty"}
        # Strip outer parentheses
        while len(tokens) >= 2 and tokens[0] == "(" and tokens[-1] == ")":
            tokens = tokens[1:-1]
            if not tokens:
                return {"type": "empty"}
        if len(tokens) == 1:
            return {"type": "atom", "value": tokens[0]}
        op_idx = self._find_main_op(tokens)
        if op_idx == -1:
            return {"type": "atom", "value": " ".join(tokens)}
        op = tokens[op_idx]
        left = self._build_tree(tokens[:op_idx])
        right = self._build_tree(tokens[op_idx + 1:])
        return {"type": "op", "op": op, "left": left, "right": right}

    def _find_main_op(self, tokens: List[str]) -> int:
        depth = 0
        for i, t in enumerate(tokens):
            if t == "(":
                depth += 1
            elif t == ")":
                depth -= 1
            elif depth == 0 and t in {"AND", "OR", "IMPLIES", "NOT"}:
                return i
        return -1

    def _add_cache(self, key: str, value: Any) -> None:
        if len(self.parsed_cache) >= self.max_cache:
            oldest = next(iter(self.parsed_cache))
            del self.parsed_cache[oldest]
        self.parsed_cache[key] = value
        logger.debug(f"[LogicParser._add_cache] size={len(self.parsed_cache)}")

    def get_state(self) -> Dict[str, Any]:
        return {"cache_size": len(self.parsed_cache), "max_cache": self.max_cache}


class SymbolicReasoner:
    """符号推理器（前向链式推理）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[SymbolicReasoner.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.facts: set = set(config.get("initial_facts", []))
        self.rules: List[Dict[str, Any]] = list(config.get("rules", []))
        self.max_iterations: int = int(config.get("max_iterations", 100))
        logger.info(f"SymbolicReasoner initialized facts={len(self.facts)} rules={len(self.rules)}", "hybrid")

    def add_fact(self, fact: str) -> None:
        logger.debug(f"[SymbolicReasoner.add_fact] {fact}")
        self.facts.add(fact)

    def add_rule(self, rule: Dict[str, Any]) -> None:
        logger.debug(f"[SymbolicReasoner.add_rule] {rule.get('id')}")
        if "if" not in rule or "then" not in rule:
            raise ValidationError("rule must contain 'if' and 'then'")
        self.rules.append(rule)

    def infer(self) -> List[str]:
        logger.debug("[SymbolicReasoner.infer] start")
        new_facts: List[str] = []
        for _ in range(self.max_iterations):
            added = False
            for rule in self.rules:
                conditions = rule["if"]
                if all(c in self.facts for c in conditions):
                    conclusion = rule["then"]
                    if conclusion not in self.facts:
                        self.facts.add(conclusion)
                        new_facts.append(conclusion)
                        added = True
                        logger.debug(f"[SymbolicReasoner.infer] inferred {conclusion}")
            if not added:
                break
        logger.debug(f"[SymbolicReasoner.infer] new={len(new_facts)}")
        return new_facts

    def query(self, fact: str) -> bool:
        result = fact in self.facts
        logger.debug(f"[SymbolicReasoner.query] {fact}={result}")
        return result

    def get_state(self) -> Dict[str, Any]:
        return {
            "fact_count": len(self.facts),
            "rule_count": len(self.rules),
            "facts": list(self.facts)[:10],
        }


class NeuralSymbolicBridge:
    """神经符号桥接（向量↔符号互转）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[NeuralSymbolicBridge.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.vector_dim: int = int(config.get("vector_dim", 8))
        self.symbol_table: Dict[str, np.ndarray] = {}
        self.max_symbols: int = int(config.get("max_symbols", 500))
        logger.info(f"NeuralSymbolicBridge initialized dim={self.vector_dim}", "hybrid")

    def symbol_to_vector(self, symbol: str) -> List[float]:
        logger.debug(f"[NeuralSymbolicBridge.symbol_to_vector] {symbol}")
        if symbol not in self.symbol_table:
            vec = np.random.randn(self.vector_dim) * 0.1
            self.symbol_table[symbol] = vec
            if len(self.symbol_table) > self.max_symbols:
                oldest = next(iter(self.symbol_table))
                del self.symbol_table[oldest]
        return [float(v) for v in self.symbol_table[symbol]]

    def vector_to_symbol(self, vector: List[float], candidates: List[str]) -> str:
        logger.debug(f"[NeuralSymbolicBridge.vector_to_symbol] candidates={len(candidates)}")
        if not candidates:
            return "unknown"
        vec = np.array(vector, dtype=np.float64)
        best = candidates[0]
        best_sim = -1.0
        for c in candidates:
            c_vec = np.array(self.symbol_to_vector(c), dtype=np.float64)
            min_len = min(len(vec), len(c_vec))
            if min_len == 0:
                continue
            sim = float(np.dot(vec[:min_len], c_vec[:min_len]) /
                        (np.linalg.norm(vec[:min_len]) * np.linalg.norm(c_vec[:min_len]) + 1e-8))
            if sim > best_sim:
                best_sim = sim
                best = c
        logger.debug(f"[NeuralSymbolicBridge.vector_to_symbol] best={best} sim={best_sim:.4f}")
        return best

    def get_state(self) -> Dict[str, Any]:
        return {"symbol_count": len(self.symbol_table), "vector_dim": self.vector_dim}


class RuleInductor:
    """规则归纳器（从数据中提取IF-THEN规则）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[RuleInductor.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.min_support: int = int(config.get("min_support", 3))
        self.confidence_threshold: float = float(config.get("confidence_threshold", 0.7))
        self.rules: List[Dict[str, Any]] = []
        self.max_rules: int = int(config.get("max_rules", 100))
        logger.info(f"RuleInductor initialized min_support={self.min_support}", "hybrid")

    def induce(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logger.debug(f"[RuleInductor.induce] data={len(data)}")
        Validator.require_type(data, list, "data")
        if not data:
            return []
        patterns: Dict[str, Dict[str, int]] = {}
        for record in data:
            conditions = tuple(sorted(record.get("conditions", [])))
            outcome = str(record.get("outcome", ""))
            if conditions not in patterns:
                patterns[conditions] = {}
            patterns[conditions][outcome] = patterns[conditions].get(outcome, 0) + 1
        new_rules: List[Dict[str, Any]] = []
        for conditions, outcomes in patterns.items():
            total = sum(outcomes.values())
            if total < self.min_support:
                continue
            best_outcome = max(outcomes, key=lambda k: outcomes[k])
            confidence = outcomes[best_outcome] / total
            if confidence >= self.confidence_threshold:
                rule = {
                    "id": f"rule_{len(self.rules) + len(new_rules)}",
                    "if": list(conditions),
                    "then": best_outcome,
                    "confidence": confidence,
                    "support": total,
                }
                new_rules.append(rule)
        self.rules.extend(new_rules)
        if len(self.rules) > self.max_rules:
            self.rules = self.rules[-self.max_rules:]
        logger.debug(f"[RuleInductor.induce] new_rules={len(new_rules)}")
        return new_rules

    def get_state(self) -> Dict[str, Any]:
        return {"rule_count": len(self.rules), "min_support": self.min_support}


class HybridInferenceModule:
    """神经符号混合推理主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[HybridInferenceModule.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.parser = LogicParser(config.get("parser", {}))
        logger.debug("[HybridInferenceModule.__init__] parser created")
        self.reasoner = SymbolicReasoner(config.get("reasoner", {}))
        logger.debug("[HybridInferenceModule.__init__] reasoner created")
        self.bridge = NeuralSymbolicBridge(config.get("bridge", {}))
        logger.debug("[HybridInferenceModule.__init__] bridge created")
        self.inductor = RuleInductor(config.get("inductor", {}))
        logger.debug("[HybridInferenceModule.__init__] inductor created")
        logger.info("HybridInferenceModule initialized", "hybrid")

    def parse_and_infer(self, expression: str) -> Dict[str, Any]:
        logger.debug("[HybridInferenceModule.parse_and_infer] start")
        parsed = self.parser.parse(expression)
        inferred = self.reasoner.infer()
        return {"parsed": parsed, "inferred": inferred}

    def neural_to_symbolic(self, vector: List[float], candidates: List[str]) -> str:
        logger.debug("[HybridInferenceModule.neural_to_symbolic] start")
        return self.bridge.vector_to_symbol(vector, candidates)

    def symbolic_to_neural(self, symbol: str) -> List[float]:
        logger.debug("[HybridInferenceModule.symbolic_to_neural] start")
        return self.bridge.symbol_to_vector(symbol)

    def learn_rules(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logger.debug("[HybridInferenceModule.learn_rules] start")
        return self.inductor.induce(data)

    def add_fact(self, fact: str) -> None:
        logger.debug(f"[HybridInferenceModule.add_fact] {fact}")
        self.reasoner.add_fact(fact)

    def query(self, fact: str) -> bool:
        logger.debug(f"[HybridInferenceModule.query] {fact}")
        return self.reasoner.query(fact)

    def get_state(self) -> Dict[str, Any]:
        return {
            "parser": self.parser.get_state(),
            "reasoner": self.reasoner.get_state(),
            "bridge": self.bridge.get_state(),
            "inductor": self.inductor.get_state(),
        }
