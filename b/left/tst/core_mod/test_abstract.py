"""分层抽象与概念形成模块测试"""
import numpy as np
import pytest

from root.left.app.left.src.core_mod.abstract import (
    AbstractionModule,
    ConceptFormation,
    ConceptNode,
    HierarchicalAbstraction,
    PatternCluster,
)
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestConceptNode:
    """ConceptNode 单元测试"""

    def test_init_normal(self) -> None:
        node = ConceptNode("test", 0, [1.0, 2.0, 3.0])
        assert node.name == "test"
        assert node.level == 0
        assert node.parent is None
        assert node.stability == 0.0
        assert node.occurrence_count == 1

    def test_init_empty_features(self) -> None:
        node = ConceptNode("empty", 1, [])
        assert len(node.features) == 0

    def test_add_child(self) -> None:
        node = ConceptNode("parent", 0, [1.0])
        node.add_child("c1")
        node.add_child("c1")
        assert node.children == ["c1"]

    def test_remove_child(self) -> None:
        node = ConceptNode("p", 0, [1.0])
        node.add_child("c1")
        node.remove_child("c1")
        assert node.children == []
        node.remove_child("missing")
        assert node.children == []

    def test_update_stability(self) -> None:
        node = ConceptNode("s", 0, [1.0, 2.0])
        node.update_stability([1.0, 2.0])
        assert node.occurrence_count == 2
        assert node.stability > 0.9

    def test_update_stability_pad(self) -> None:
        node = ConceptNode("s", 0, [1.0, 2.0, 3.0])
        node.update_stability([1.0])
        assert node.occurrence_count == 2

    def test_to_dict(self) -> None:
        node = ConceptNode("d", 1, [0.5])
        d = node.to_dict()
        assert d["name"] == "d"
        assert d["level"] == 1
        assert d["features"] == [0.5]


class TestPatternCluster:
    """PatternCluster 单元测试"""

    def test_init_normal(self) -> None:
        pc = PatternCluster({"similarity_threshold": 0.8, "max_clusters": 10})
        assert pc.similarity_threshold == 0.8
        assert pc.max_clusters == 10

    def test_init_defaults(self) -> None:
        pc = PatternCluster({})
        assert pc.similarity_threshold == 0.85
        assert pc.max_clusters == 100

    def test_assign_new_cluster(self) -> None:
        pc = PatternCluster({"similarity_threshold": 0.99})
        cid = pc.assign([1.0, 0.0])
        assert cid in pc.clusters
        assert pc.cluster_counts[cid] == 1

    def test_assign_merge_similar(self) -> None:
        pc = PatternCluster({"similarity_threshold": 0.9})
        cid1 = pc.assign([1.0, 0.0])
        cid2 = pc.assign([0.99, 0.01])
        assert cid1 == cid2
        assert pc.cluster_counts[cid1] == 2

    def test_assign_evict_when_full(self) -> None:
        pc = PatternCluster({"similarity_threshold": 0.99, "max_clusters": 2})
        pc.assign([1.0, 0.0])
        pc.assign([0.0, 1.0])
        pc.assign([1.0, 1.0])
        assert pc.get_cluster_count() <= 2

    def test_cosine_sim_zero_norm(self) -> None:
        pc = PatternCluster({})
        a = np.array([0.0, 0.0])
        b = np.array([1.0, 0.0])
        assert pc._cosine_sim(a, b) == 0.0

    def test_get_state(self) -> None:
        pc = PatternCluster({})
        s = pc.get_state()
        assert "cluster_count" in s


class TestHierarchicalAbstraction:
    """HierarchicalAbstraction 单元测试"""

    def test_init_normal(self) -> None:
        ha = HierarchicalAbstraction({"max_levels": 3, "merge_threshold": 0.95})
        assert ha.max_levels == 3
        assert ha.merge_threshold == 0.95
        assert len(ha.level_index) == 3

    def test_ingest_creates_l0(self) -> None:
        ha = HierarchicalAbstraction({"similarity_threshold": 0.99})
        name = ha.ingest("r1", [1.0, 0.0])
        assert name.startswith("L0_")
        assert name in ha.concepts

    def test_ingest_updates_existing(self) -> None:
        ha = HierarchicalAbstraction({"similarity_threshold": 0.99})
        name = ha.ingest("r1", [1.0, 0.0])
        n1 = ha.concepts[name].occurrence_count
        ha.ingest("r2", [1.0, 0.0])
        n2 = ha.concepts[name].occurrence_count
        assert n2 > n1

    def test_abstract_up_creates_parent(self) -> None:
        ha = HierarchicalAbstraction({"similarity_threshold": 0.99, "merge_threshold": 0.99})
        ha.ingest("r1", [1.0, 0.0])
        parent_level = ha.level_index[1]
        assert len(parent_level) >= 1

    def test_query_path(self) -> None:
        ha = HierarchicalAbstraction({"similarity_threshold": 0.99, "merge_threshold": 0.99})
        name = ha.ingest("r1", [1.0, 0.0])
        path = ha.query_path(name)
        assert len(path) >= 1
        assert path[0] == name

    def test_query_path_missing(self) -> None:
        ha = HierarchicalAbstraction({})
        path = ha.query_path("missing")
        assert path == ["missing"]

    def test_get_level_concepts(self) -> None:
        ha = HierarchicalAbstraction({})
        ha.ingest("r1", [1.0])
        result = ha.get_level_concepts(0)
        assert len(result) >= 1

    def test_merge_concepts(self) -> None:
        ha = HierarchicalAbstraction({"similarity_threshold": 0.99, "merge_threshold": 0.99})
        n1 = ha.ingest("r1", [1.0, 0.0])
        n2 = ha.ingest("r2", [1.0, 0.0])
        ha._merge_concepts(n1, n2)
        assert n2 not in ha.concepts

    def test_merge_concepts_missing(self) -> None:
        ha = HierarchicalAbstraction({})
        ha._merge_concepts("a", "b")

    def test_get_state(self) -> None:
        ha = HierarchicalAbstraction({})
        s = ha.get_state()
        assert "total_concepts" in s
        assert "level_distribution" in s


class TestConceptFormation:
    """ConceptFormation 单元测试"""

    def test_init_normal(self) -> None:
        cf = ConceptFormation({"stability_threshold": 0.8, "min_occurrences": 5})
        assert cf.stability_threshold == 0.8
        assert cf.min_occurrences == 5

    def test_observe_returns_none_initially(self) -> None:
        cf = ConceptFormation({"stability_threshold": 0.99, "min_occurrences": 10})
        result = cf.observe({"features": [1.0, 2.0]})
        assert result is None

    def test_observe_eventually_stable(self) -> None:
        cf = ConceptFormation({"stability_threshold": 0.5, "min_occurrences": 3})
        stable = None
        for _ in range(5):
            stable = cf.observe({"features": [1.0, 2.0], "label": "A"})
        assert stable == "A"

    def test_observe_missing_features(self) -> None:
        cf = ConceptFormation({})
        result = cf.observe({"label": "A"})
        assert result is None

    def test_evict_weakest(self) -> None:
        cf = ConceptFormation({"max_concepts": 2})
        cf.observe({"features": [1.0], "label": "A"})
        cf.observe({"features": [2.0], "label": "B"})
        cf.observe({"features": [3.0], "label": "C"})
        assert len(cf.formed_concepts) <= 2

    def test_get_stable_concepts(self) -> None:
        cf = ConceptFormation({"stability_threshold": 0.1, "min_occurrences": 1})
        for _ in range(5):
            cf.observe({"features": [1.0], "label": "A"})
        stable = cf.get_stable_concepts()
        assert len(stable) >= 1
        assert "key" in stable[0]

    def test_get_state(self) -> None:
        cf = ConceptFormation({})
        s = cf.get_state()
        assert "formed_count" in s


class TestAbstractionModule:
    """AbstractionModule 集成测试"""

    def test_init_normal(self) -> None:
        mod = AbstractionModule({})
        assert mod.hierarchy is not None
        assert mod.formation is not None

    def test_process_experience_normal(self) -> None:
        mod = AbstractionModule({})
        result = mod.process_experience({"id": "e1", "features": [1.0, 0.0]})
        assert "hierarchy_concept" in result
        assert "stable_concept" in result
        assert result["hierarchy_concept"].startswith("L0_")

    def test_process_experience_missing_features(self) -> None:
        mod = AbstractionModule({})
        with pytest.raises(ValidationError):
            mod.process_experience({"id": "e1"})

    def test_query_concept_path(self) -> None:
        mod = AbstractionModule({})
        result = mod.process_experience({"id": "e1", "features": [1.0]})
        name = result["hierarchy_concept"]
        path = mod.query_concept_path(name)
        assert len(path) >= 1

    def test_get_stable_concepts(self) -> None:
        mod = AbstractionModule({"formation": {"stability_threshold": 0.1, "min_occurrences": 1}})
        mod.process_experience({"id": "e1", "features": [1.0], "label": "A"})
        stable = mod.get_stable_concepts()
        assert isinstance(stable, list)

    def test_get_state(self) -> None:
        mod = AbstractionModule({})
        s = mod.get_state()
        assert "hierarchy" in s
        assert "formation" in s

    def test_long_sequence_stability(self) -> None:
        mod = AbstractionModule({
            "formation": {"stability_threshold": 0.6, "min_occurrences": 3},
            "hierarchy": {"similarity_threshold": 0.99, "merge_threshold": 0.99}
        })
        stable_keys = []
        for i in range(20):
            result = mod.process_experience({
                "id": f"e{i}",
                "features": [1.0, 0.0],
                "label": "fixed"
            })
            if result["stable_concept"] is not None:
                stable_keys.append(result["stable_concept"])
        assert len(stable_keys) >= 1

    def test_diverse_features_create_multiple_clusters(self) -> None:
        mod = AbstractionModule({
            "hierarchy": {"similarity_threshold": 0.99, "merge_threshold": 0.99}
        })
        for i in range(10):
            mod.process_experience({
                "id": f"e{i}",
                "features": [float(i), float(i * 2)]
            })
        state = mod.get_state()
        assert state["hierarchy"]["total_concepts"] >= 1

    def test_boundary_empty_features(self) -> None:
        mod = AbstractionModule({})
        result = mod.process_experience({"id": "e", "features": []})
        assert "hierarchy_concept" in result

    def test_boundary_single_feature(self) -> None:
        mod = AbstractionModule({})
        result = mod.process_experience({"id": "e", "features": [5.0]})
        assert result["hierarchy_concept"].startswith("L0_")

    def test_boundary_large_features(self) -> None:
        mod = AbstractionModule({})
        features = [float(i) for i in range(1000)]
        result = mod.process_experience({"id": "e", "features": features})
        assert result["hierarchy_concept"].startswith("L0_")

    def test_formation_max_concepts_eviction(self) -> None:
        mod = AbstractionModule({
            "formation": {"max_concepts": 3, "stability_threshold": 0.99, "min_occurrences": 100}
        })
        for i in range(10):
            mod.process_experience({
                "id": f"e{i}",
                "features": [float(i)],
                "label": f"L{i}"
            })
        state = mod.get_state()
        assert state["formation"]["formed_count"] <= 3
