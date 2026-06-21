"""分层抽象与概念形成模块"""
import copy
import hashlib
from typing import Any, Dict, Final, List, Optional, Set

import numpy as np

from root.left.app.left.src.utils_main.exceptions import ValidationError
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class ConceptNode:
    """概念节点（树形层级结构）"""

    def __init__(self, name: str, level: int, features: List[float]) -> None:
        logger.debug(f"[ConceptNode.__init__] name={name} level={level}")
        Validator.require_type(name, str, "name")
        Validator.require_type(level, int, "level")
        Validator.require_type(features, list, "features")
        self.name: str = name
        self.level: int = level
        self.features: np.ndarray = np.array(features, dtype=np.float64)
        self.children: List[str] = []
        self.parent: Optional[str] = None
        self.stability: float = 0.0
        self.occurrence_count: int = 1
        logger.debug("[ConceptNode.__init__] done")

    def add_child(self, child_name: str) -> None:
        logger.debug(f"[ConceptNode.add_child] child={child_name}")
        if child_name not in self.children:
            self.children.append(child_name)
        logger.debug(f"[ConceptNode.add_child] children={len(self.children)}")

    def remove_child(self, child_name: str) -> None:
        logger.debug(f"[ConceptNode.remove_child] child={child_name}")
        if child_name in self.children:
            self.children.remove(child_name)
        logger.debug(f"[ConceptNode.remove_child] children={len(self.children)}")

    def update_stability(self, new_sample: List[float]) -> None:
        logger.debug(f"[ConceptNode.update_stability] name={self.name}")
        arr = np.array(new_sample, dtype=np.float64)
        if len(arr) != len(self.features):
            arr = self._pad_or_trim(arr)
        self.occurrence_count += 1
        alpha = 1.0 / self.occurrence_count
        old = self.features.copy()
        self.features = (1 - alpha) * old + alpha * arr
        dist = float(np.linalg.norm(self.features - old))
        self.stability = 1.0 / (1.0 + dist)
        logger.debug(f"[ConceptNode.update_stability] stability={self.stability:.4f}")

    def _pad_or_trim(self, arr: np.ndarray) -> np.ndarray:
        logger.debug(f"[ConceptNode._pad_or_trim] len={len(arr)} target={len(self.features)}")
        target = len(self.features)
        if len(arr) < target:
            return np.pad(arr, (0, target - len(arr)))
        return arr[:target]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "level": self.level,
            "features": self.features.tolist(),
            "children": self.children.copy(),
            "parent": self.parent,
            "stability": float(self.stability),
            "occurrence_count": self.occurrence_count,
        }


class PatternCluster:
    """模式聚类器（基于余弦相似度自动归类）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[PatternCluster.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.similarity_threshold: float = float(config.get("similarity_threshold", 0.85))
        self.max_clusters: int = int(config.get("max_clusters", 100))
        self.clusters: Dict[str, np.ndarray] = {}
        self.cluster_counts: Dict[str, int] = {}
        logger.info(f"PatternCluster initialized threshold={self.similarity_threshold}", "abstract")

    def _hash(self, features: List[float]) -> str:
        logger.debug("[PatternCluster._hash] start")
        arr = np.array(features, dtype=np.float64)
        rounded = np.round(arr, 4)
        raw = rounded.tobytes()
        h = hashlib.md5(raw).hexdigest()[:12]
        logger.debug(f"[PatternCluster._hash] hash={h}")
        return h

    def _cosine_sim(self, a: np.ndarray, b: np.ndarray) -> float:
        logger.debug("[PatternCluster._cosine_sim] start")
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        sim = float(np.dot(a, b) / (norm_a * norm_b))
        logger.debug(f"[PatternCluster._cosine_sim] sim={sim:.4f}")
        return sim

    def assign(self, features: List[float]) -> str:
        logger.debug("[PatternCluster.assign] start")
        arr = np.array(features, dtype=np.float64)
        best_id: Optional[str] = None
        best_sim: float = -1.0
        for cid, centroid in self.clusters.items():
            sim = self._cosine_sim(arr, centroid)
            if sim > best_sim:
                best_sim = sim
                best_id = cid
        if best_id is not None and best_sim >= self.similarity_threshold:
            self._update_centroid(best_id, arr)
            logger.debug(f"[PatternCluster.assign] matched={best_id} sim={best_sim:.4f}")
            return best_id
        new_id = self._hash(features)
        if len(self.clusters) >= self.max_clusters:
            self._evict_oldest()
        self.clusters[new_id] = arr.copy()
        self.cluster_counts[new_id] = 1
        logger.debug(f"[PatternCluster.assign] new_cluster={new_id}")
        return new_id

    def _update_centroid(self, cid: str, arr: np.ndarray) -> None:
        logger.debug(f"[PatternCluster._update_centroid] cid={cid}")
        count = self.cluster_counts.get(cid, 1)
        old = self.clusters[cid]
        self.clusters[cid] = (old * count + arr) / (count + 1)
        self.cluster_counts[cid] = count + 1
        logger.debug(f"[PatternCluster._update_centroid] new_count={count + 1}")

    def _evict_oldest(self) -> None:
        logger.debug("[PatternCluster._evict_oldest] start")
        if not self.cluster_counts:
            return
        oldest = min(self.cluster_counts, key=lambda k: self.cluster_counts[k])
        del self.clusters[oldest]
        del self.cluster_counts[oldest]
        logger.debug(f"[PatternCluster._evict_oldest] evicted={oldest}")

    def get_cluster_count(self) -> int:
        return len(self.clusters)

    def get_state(self) -> Dict[str, Any]:
        return {
            "cluster_count": len(self.clusters),
            "threshold": self.similarity_threshold,
            "max_clusters": self.max_clusters,
        }


class HierarchicalAbstraction:
    """分层抽象引擎（从原始数据逐层提炼概念）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[HierarchicalAbstraction.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.max_levels: int = int(config.get("max_levels", 4))
        self.merge_threshold: float = float(config.get("merge_threshold", 0.9))
        self.concepts: Dict[str, ConceptNode] = {}
        self.level_index: Dict[int, List[str]] = {i: [] for i in range(self.max_levels)}
        self.cluster = PatternCluster(config.get("cluster", {}))
        logger.info(f"HierarchicalAbstraction initialized max_levels={self.max_levels}", "abstract")

    def ingest(self, raw_id: str, features: List[float]) -> str:
        logger.debug(f"[HierarchicalAbstraction.ingest] raw_id={raw_id}")
        cid = self.cluster.assign(features)
        name = f"L0_{cid}"
        if name in self.concepts:
            self.concepts[name].update_stability(features)
        else:
            node = ConceptNode(name, 0, features)
            self.concepts[name] = node
            self.level_index[0].append(name)
            logger.debug(f"[HierarchicalAbstraction.ingest] created L0 concept={name}")
        self._try_abstract_up(name)
        logger.debug("[HierarchicalAbstraction.ingest] done")
        return name

    def _try_abstract_up(self, concept_name: str) -> None:
        logger.debug(f"[HierarchicalAbstraction._try_abstract_up] name={concept_name}")
        node = self.concepts.get(concept_name)
        if node is None:
            return
        if node.level >= self.max_levels - 1:
            return
        parent_name = self._find_or_create_parent(node)
        if parent_name is None:
            return
        parent = self.concepts[parent_name]
        if concept_name not in parent.children:
            parent.add_child(concept_name)
            node.parent = parent_name
            logger.debug(f"[HierarchicalAbstraction._try_abstract_up] linked {concept_name} -> {parent_name}")
        self._try_merge_siblings(parent_name)

    def _find_or_create_parent(self, node: ConceptNode) -> Optional[str]:
        logger.debug(f"[HierarchicalAbstraction._find_or_create_parent] name={node.name}")
        parent_level = node.level + 1
        candidates = self.level_index.get(parent_level, [])
        best: Optional[str] = None
        best_sim: float = -1.0
        arr = node.features
        for cand in candidates:
            cand_node = self.concepts[cand]
            sim = self._cosine_sim(arr, cand_node.features)
            if sim > best_sim:
                best_sim = sim
                best = cand
        if best is not None and best_sim >= self.merge_threshold:
            self.concepts[best].update_stability(node.features.tolist())
            logger.debug(f"[HierarchicalAbstraction._find_or_create_parent] matched={best} sim={best_sim:.4f}")
            return best
        new_name = f"L{parent_level}_{node.name}"
        new_node = ConceptNode(new_name, parent_level, node.features.tolist())
        self.concepts[new_name] = new_node
        self.level_index[parent_level].append(new_name)
        logger.debug(f"[HierarchicalAbstraction._find_or_create_parent] created={new_name}")
        return new_name

    def _cosine_sim(self, a: np.ndarray, b: np.ndarray) -> float:
        logger.debug("[HierarchicalAbstraction._cosine_sim] start")
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def _try_merge_siblings(self, parent_name: str) -> None:
        logger.debug(f"[HierarchicalAbstraction._try_merge_siblings] parent={parent_name}")
        parent = self.concepts.get(parent_name)
        if parent is None or len(parent.children) < 2:
            return
        children = parent.children.copy()
        merged_any = False
        for i in range(len(children)):
            for j in range(i + 1, len(children)):
                c1 = self.concepts.get(children[i])
                c2 = self.concepts.get(children[j])
                if c1 is None or c2 is None:
                    continue
                sim = self._cosine_sim(c1.features, c2.features)
                if sim >= self.merge_threshold:
                    self._merge_concepts(c1.name, c2.name)
                    merged_any = True
                    break
            if merged_any:
                break
        logger.debug(f"[HierarchicalAbstraction._try_merge_siblings] merged={merged_any}")

    def _merge_concepts(self, keep_name: str, drop_name: str) -> None:
        logger.debug(f"[HierarchicalAbstraction._merge_concepts] keep={keep_name} drop={drop_name}")
        keep = self.concepts.get(keep_name)
        drop = self.concepts.get(drop_name)
        if keep is None or drop is None:
            return
        keep.update_stability(drop.features.tolist())
        for child in drop.children:
            keep.add_child(child)
            child_node = self.concepts.get(child)
            if child_node is not None:
                child_node.parent = keep_name
        parent_name = drop.parent
        if parent_name is not None:
            parent = self.concepts.get(parent_name)
            if parent is not None:
                parent.remove_child(drop_name)
        level = drop.level
        if drop_name in self.level_index.get(level, []):
            self.level_index[level].remove(drop_name)
        del self.concepts[drop_name]
        logger.debug("[HierarchicalAbstraction._merge_concepts] done")

    def query_path(self, concept_name: str) -> List[str]:
        logger.debug(f"[HierarchicalAbstraction.query_path] name={concept_name}")
        path: List[str] = []
        current = concept_name
        visited: Set[str] = set()
        while current is not None and current not in visited:
            visited.add(current)
            path.append(current)
            node = self.concepts.get(current)
            if node is None:
                break
            current = node.parent
        logger.debug(f"[HierarchicalAbstraction.query_path] path_len={len(path)}")
        return path

    def get_level_concepts(self, level: int) -> List[Dict[str, Any]]:
        logger.debug(f"[HierarchicalAbstraction.get_level_concepts] level={level}")
        names = self.level_index.get(level, [])
        result = []
        for name in names:
            node = self.concepts.get(name)
            if node is not None:
                result.append(node.to_dict())
        logger.debug(f"[HierarchicalAbstraction.get_level_concepts] count={len(result)}")
        return result

    def get_state(self) -> Dict[str, Any]:
        return {
            "total_concepts": len(self.concepts),
            "level_distribution": {k: len(v) for k, v in self.level_index.items()},
            "cluster_state": self.cluster.get_state(),
        }


class ConceptFormation:
    """概念形成器（从经验序列中提取稳定概念）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[ConceptFormation.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.stability_threshold: float = float(config.get("stability_threshold", 0.7))
        self.min_occurrences: int = int(config.get("min_occurrences", 3))
        self.max_concepts: int = int(config.get("max_concepts", 200))
        self.formed_concepts: Dict[str, Dict[str, Any]] = {}
        logger.info(f"ConceptFormation initialized threshold={self.stability_threshold}", "abstract")

    def observe(self, experience: Dict[str, Any]) -> Optional[str]:
        logger.debug("[ConceptFormation.observe] start")
        Validator.require_type(experience, dict, "experience")
        features = experience.get("features")
        if features is None:
            logger.warning("[ConceptFormation.observe] missing features")
            return None
        label = experience.get("label")
        if label is None:
            label = self._auto_label(features)
        key = str(label)
        if key in self.formed_concepts:
            self._update_concept(key, features)
        else:
            if len(self.formed_concepts) >= self.max_concepts:
                self._evict_weakest()
            self._create_concept(key, features)
        concept = self.formed_concepts[key]
        if concept["stability"] >= self.stability_threshold and concept["occurrences"] >= self.min_occurrences:
            logger.info(f"[ConceptFormation.observe] stable_concept={key}", "abstract")
            return key
        logger.debug(f"[ConceptFormation.observe] unstable key={key}")
        return None

    def _auto_label(self, features: List[float]) -> str:
        logger.debug("[ConceptFormation._auto_label] start")
        arr = np.array(features, dtype=np.float64)
        h = hashlib.md5(arr.tobytes()).hexdigest()[:8]
        logger.debug(f"[ConceptFormation._auto_label] hash={h}")
        return h

    def _create_concept(self, key: str, features: List[float]) -> None:
        logger.debug(f"[ConceptFormation._create_concept] key={key}")
        arr = np.array(features, dtype=np.float64)
        self.formed_concepts[key] = {
            "features": arr.copy(),
            "stability": 0.0,
            "occurrences": 1,
            "created_at": 0,
        }
        logger.debug("[ConceptFormation._create_concept] done")

    def _update_concept(self, key: str, features: List[float]) -> None:
        logger.debug(f"[ConceptFormation._update_concept] key={key}")
        concept = self.formed_concepts[key]
        arr = np.array(features, dtype=np.float64)
        if len(arr) != len(concept["features"]):
            target = len(concept["features"])
            if len(arr) < target:
                arr = np.pad(arr, (0, target - len(arr)))
            else:
                arr = arr[:target]
        concept["occurrences"] += 1
        alpha = 1.0 / concept["occurrences"]
        old = concept["features"].copy()
        concept["features"] = (1 - alpha) * old + alpha * arr
        dist = float(np.linalg.norm(concept["features"] - old))
        concept["stability"] = 1.0 / (1.0 + dist)
        logger.debug(f"[ConceptFormation._update_concept] stability={concept['stability']:.4f}")

    def _evict_weakest(self) -> None:
        logger.debug("[ConceptFormation._evict_weakest] start")
        if not self.formed_concepts:
            return
        weakest = min(
            self.formed_concepts,
            key=lambda k: self.formed_concepts[k]["stability"]
        )
        del self.formed_concepts[weakest]
        logger.debug(f"[ConceptFormation._evict_weakest] evicted={weakest}")

    def get_stable_concepts(self) -> List[Dict[str, Any]]:
        logger.debug("[ConceptFormation.get_stable_concepts] start")
        result = []
        for key, concept in self.formed_concepts.items():
            if concept["stability"] >= self.stability_threshold and concept["occurrences"] >= self.min_occurrences:
                entry = copy.deepcopy(concept)
                entry["key"] = key
                entry["features"] = entry["features"].tolist()
                result.append(entry)
        logger.debug(f"[ConceptFormation.get_stable_concepts] count={len(result)}")
        return result

    def get_state(self) -> Dict[str, Any]:
        return {
            "formed_count": len(self.formed_concepts),
            "stable_count": len(self.get_stable_concepts()),
            "threshold": self.stability_threshold,
            "min_occurrences": self.min_occurrences,
        }


class AbstractionModule:
    """分层抽象与概念形成主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[AbstractionModule.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.hierarchy = HierarchicalAbstraction(config.get("hierarchy", {}))
        logger.debug("[AbstractionModule.__init__] hierarchy created")
        self.formation = ConceptFormation(config.get("formation", {}))
        logger.debug("[AbstractionModule.__init__] formation created")
        logger.info("AbstractionModule initialized", "abstract")

    def process_experience(self, experience: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[AbstractionModule.process_experience] start")
        Validator.require_type(experience, dict, "experience")
        features = experience.get("features")
        if features is None:
            raise ValidationError("experience must contain 'features'", "features")
        raw_id = experience.get("id", "unknown")
        concept_name = self.hierarchy.ingest(raw_id, features)
        stable = self.formation.observe(experience)
        result = {
            "hierarchy_concept": concept_name,
            "stable_concept": stable,
            "hierarchy_state": self.hierarchy.get_state(),
            "formation_state": self.formation.get_state(),
        }
        logger.debug(f"[AbstractionModule.process_experience] hierarchy={concept_name} stable={stable}")
        return result

    def query_concept_path(self, concept_name: str) -> List[str]:
        logger.debug(f"[AbstractionModule.query_concept_path] name={concept_name}")
        return self.hierarchy.query_path(concept_name)

    def get_stable_concepts(self) -> List[Dict[str, Any]]:
        logger.debug("[AbstractionModule.get_stable_concepts] start")
        return self.formation.get_stable_concepts()

    def get_state(self) -> Dict[str, Any]:
        return {
            "hierarchy": self.hierarchy.get_state(),
            "formation": self.formation.get_state(),
        }
