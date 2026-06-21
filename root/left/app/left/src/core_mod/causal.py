"""因果推理与反事实分析模块"""
import copy
from typing import Any, Dict, Final, List, Optional, Set, Tuple

import numpy as np

from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class CausalGraph:
    """因果图（有向无环图）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[CausalGraph.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.nodes: Set[str] = set()
        self.edges: Dict[str, List[str]] = {}
        self.edge_weights: Dict[Tuple[str, str], float] = {}
        logger.info("CausalGraph initialized", "causal")

    def add_node(self, node: str) -> None:
        logger.debug(f"[CausalGraph.add_node] node={node}")
        self.nodes.add(node)
        if node not in self.edges:
            self.edges[node] = []

    def add_edge(self, from_node: str, to_node: str, weight: float = 1.0) -> None:
        logger.debug(f"[CausalGraph.add_edge] {from_node} -> {to_node} weight={weight}")
        self.add_node(from_node)
        self.add_node(to_node)
        if to_node not in self.edges[from_node]:
            self.edges[from_node].append(to_node)
        self.edge_weights[(from_node, to_node)] = weight

    def get_parents(self, node: str) -> List[str]:
        parents = [n for n, children in self.edges.items() if node in children]
        logger.debug(f"[CausalGraph.get_parents] node={node} parents={parents}")
        return parents

    def get_children(self, node: str) -> List[str]:
        children = self.edges.get(node, [])
        logger.debug(f"[CausalGraph.get_children] node={node} children={children}")
        return children

    def has_cycle(self) -> bool:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(n: str) -> bool:
            visited.add(n)
            rec_stack.add(n)
            for child in self.edges.get(n, []):
                if child not in visited:
                    if dfs(child):
                        return True
                elif child in rec_stack:
                    return True
            rec_stack.remove(n)
            return False

        for node in self.nodes:
            if node not in visited:
                if dfs(node):
                    logger.warning("[CausalGraph.has_cycle] cycle detected", "causal")
                    return True
        logger.debug("[CausalGraph.has_cycle] no cycle")
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": list(self.nodes),
            "edges": {k: list(v) for k, v in self.edges.items()},
            "weights": {f"{k[0]}->{k[1]}": v for k, v in self.edge_weights.items()},
        }


class InterventionSimulator:
    """干预模拟器（do-calculus）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[InterventionSimulator.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        logger.info("InterventionSimulator initialized", "causal")

    def do_intervention(
        self,
        graph: CausalGraph,
        state: Dict[str, float],
        intervention: Dict[str, float]
    ) -> Dict[str, float]:
        logger.debug(f"[InterventionSimulator.do_intervention] vars={list(intervention.keys())}")
        result = copy.deepcopy(state)
        for var, value in intervention.items():
            old_value = result.get(var, 0.0)
            result[var] = value
            self._propagate_effects(graph, result, var, old_value, value)
        logger.debug("[InterventionSimulator.do_intervention] done")
        return result

    def _propagate_effects(
        self,
        graph: CausalGraph,
        state: Dict[str, float],
        changed_var: str,
        old_value: float,
        new_value: float
    ) -> None:
        children = graph.get_children(changed_var)
        for child in children:
            weight = graph.edge_weights.get((changed_var, child), 1.0)
            old_val = state.get(child, 0.0)
            delta = (new_value - old_value) * weight
            state[child] = old_val + delta
            logger.debug(f"[InterventionSimulator._propagate] {changed_var} -> {child} delta={delta:.4f}")


class CounterfactualAnalyzer:
    """反事实分析器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[CounterfactualAnalyzer.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        logger.info("CounterfactualAnalyzer initialized", "causal")

    def analyze(
        self,
        graph: CausalGraph,
        observed_state: Dict[str, float],
        intervention: Dict[str, float],
        outcome_var: str
    ) -> Dict[str, Any]:
        logger.debug(f"[CounterfactualAnalyzer.analyze] outcome={outcome_var}")
        simulator = InterventionSimulator({})
        factual = simulator.do_intervention(graph, observed_state, {})
        counterfactual = simulator.do_intervention(graph, observed_state, intervention)
        factual_outcome = factual.get(outcome_var, 0.0)
        counterfactual_outcome = counterfactual.get(outcome_var, 0.0)
        effect = counterfactual_outcome - factual_outcome
        result = {
            "outcome_var": outcome_var,
            "factual": factual_outcome,
            "counterfactual": counterfactual_outcome,
            "effect": effect,
            "intervention": intervention,
        }
        logger.info(f"[CounterfactualAnalyzer.analyze] effect={effect:.4f}", "causal")
        return result


class CausalEffectEstimator:
    """因果效应估计器（ATE）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[CausalEffectEstimator.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.min_samples: int = int(config.get("min_samples", 30))
        logger.info(f"CausalEffectEstimator initialized min_samples={self.min_samples}", "causal")

    def estimate_ate(
        self,
        data: List[Dict[str, float]],
        treatment_var: str,
        outcome_var: str
    ) -> Optional[float]:
        logger.debug(f"[CausalEffectEstimator.estimate_ate] treatment={treatment_var} outcome={outcome_var}")
        if len(data) < self.min_samples:
            logger.warning(f"[CausalEffectEstimator.estimate_ate] insufficient data: {len(data)} < {self.min_samples}")
            return None
        treated = [d for d in data if d.get(treatment_var, 0.0) > 0.5]
        control = [d for d in data if d.get(treatment_var, 0.0) <= 0.5]
        if not treated or not control:
            logger.warning("[CausalEffectEstimator.estimate_ate] empty treated or control group")
            return None
        treated_mean = np.mean([d.get(outcome_var, 0.0) for d in treated])
        control_mean = np.mean([d.get(outcome_var, 0.0) for d in control])
        ate = float(treated_mean - control_mean)
        logger.info(f"[CausalEffectEstimator.estimate_ate] ATE={ate:.4f} treated={len(treated)} control={len(control)}", "causal")
        return ate


class CausalDiscovery:
    """因果发现（基于相关性和时间优先）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[CausalDiscovery.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.correlation_threshold: float = float(config.get("correlation_threshold", 0.3))
        logger.info(f"CausalDiscovery initialized threshold={self.correlation_threshold}", "causal")

    def discover_from_data(
        self,
        data: List[Dict[str, float]],
        var_order: List[str]
    ) -> CausalGraph:
        logger.debug(f"[CausalDiscovery.discover_from_data] vars={var_order}")
        graph = CausalGraph({})
        if len(data) < 3:
            logger.warning("[CausalDiscovery.discover_from_data] insufficient data")
            return graph
        for i, var_a in enumerate(var_order):
            for var_b in var_order[i + 1:]:
                corr = self._correlation(data, var_a, var_b)
                if abs(corr) > self.correlation_threshold:
                    graph.add_edge(var_a, var_b, weight=corr)
                    logger.debug(f"[CausalDiscovery.discover] {var_a} -> {var_b} corr={corr:.4f}")
        logger.info(f"[CausalDiscovery.discover_from_data] edges={len(graph.edge_weights)}", "causal")
        return graph

    def _correlation(self, data: List[Dict[str, float]], var_a: str, var_b: str) -> float:
        vals_a = [d.get(var_a, 0.0) for d in data]
        vals_b = [d.get(var_b, 0.0) for d in data]
        if len(vals_a) < 2:
            return 0.0
        return float(np.corrcoef(vals_a, vals_b)[0, 1])


class CausalModule:
    """因果推理模块主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[CausalModule.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.graph = CausalGraph(config.get("graph", {}))
        logger.debug("[CausalModule.__init__] graph created")
        self.intervention = InterventionSimulator(config.get("intervention", {}))
        logger.debug("[CausalModule.__init__] intervention created")
        self.counterfactual = CounterfactualAnalyzer(config.get("counterfactual", {}))
        logger.debug("[CausalModule.__init__] counterfactual created")
        self.effect_estimator = CausalEffectEstimator(config.get("effect", {}))
        logger.debug("[CausalModule.__init__] effect_estimator created")
        self.discovery = CausalDiscovery(config.get("discovery", {}))
        logger.debug("[CausalModule.__init__] discovery created")
        logger.info("CausalModule initialized", "causal")

    def build_graph(self, data: List[Dict[str, float]], var_order: List[str]) -> CausalGraph:
        logger.debug("[CausalModule.build_graph] start")
        return self.discovery.discover_from_data(data, var_order)

    def simulate_intervention(
        self,
        state: Dict[str, float],
        intervention: Dict[str, float]
    ) -> Dict[str, float]:
        logger.debug("[CausalModule.simulate_intervention] start")
        return self.intervention.do_intervention(self.graph, state, intervention)

    def what_if(
        self,
        observed_state: Dict[str, float],
        intervention: Dict[str, float],
        outcome_var: str
    ) -> Dict[str, Any]:
        logger.debug(f"[CausalModule.what_if] outcome={outcome_var}")
        return self.counterfactual.analyze(self.graph, observed_state, intervention, outcome_var)

    def estimate_effect(
        self,
        data: List[Dict[str, float]],
        treatment_var: str,
        outcome_var: str
    ) -> Optional[float]:
        logger.debug(f"[CausalModule.estimate_effect] treatment={treatment_var}")
        return self.effect_estimator.estimate_ate(data, treatment_var, outcome_var)

    def get_graph_state(self) -> Dict[str, Any]:
        return self.graph.to_dict()
