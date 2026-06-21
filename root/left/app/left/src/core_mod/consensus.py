"""分布式共识与拜占庭容错模块"""
import copy
import time
from typing import Any, Dict, Final, List, Optional

import numpy as np

from root.left.app.left.src.utils_main.exceptions import ValidationError
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class RaftLikeConsensus:
    """类Raft共识（Leader选举、日志复制）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[RaftLikeConsensus.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.node_id: str = str(config.get("node_id", "node_0"))
        self.term: int = 0
        self.leader: Optional[str] = None
        self.log: List[Dict[str, Any]] = []
        self.voted_for: Optional[str] = None
        self.commit_index: int = -1
        self.nodes: List[str] = list(config.get("nodes", ["node_0"]))
        logger.info(f"RaftLikeConsensus initialized node={self.node_id}", "consensus")

    def request_vote(self, candidate_id: str, candidate_term: int) -> bool:
        logger.debug(f"[RaftLikeConsensus.request_vote] candidate={candidate_id} term={candidate_term}")
        if candidate_term > self.term:
            self.term = candidate_term
            self.voted_for = None
        if candidate_term == self.term and (self.voted_for is None or self.voted_for == candidate_id):
            self.voted_for = candidate_id
            logger.info(f"[RaftLikeConsensus.request_vote] voted for {candidate_id}", "consensus")
            return True
        return False

    def append_entries(self, leader_id: str, term: int, entries: List[Dict[str, Any]]) -> bool:
        logger.debug(f"[RaftLikeConsensus.append_entries] leader={leader_id} term={term}")
        if term < self.term:
            return False
        self.term = term
        self.leader = leader_id
        for entry in entries:
            self.log.append(copy.deepcopy(entry))
        self.commit_index = len(self.log) - 1
        logger.debug(f"[RaftLikeConsensus.append_entries] log_size={len(self.log)}")
        return True

    def become_candidate(self) -> None:
        logger.debug("[RaftLikeConsensus.become_candidate] start")
        self.term += 1
        self.voted_for = self.node_id
        logger.info(f"[RaftLikeConsensus.become_candidate] term={self.term}", "consensus")

    def get_state(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "term": self.term,
            "leader": self.leader,
            "log_size": len(self.log),
            "commit_index": self.commit_index,
        }


class ByzantineFaultTolerance:
    """拜占庭容错（多数投票、恶意节点检测）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[ByzantineFaultTolerance.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.fault_tolerance: int = int(config.get("fault_tolerance", 1))
        self.vote_history: Dict[str, List[Any]] = {}
        self.suspicion_scores: Dict[str, float] = {}
        self.max_history: int = int(config.get("max_history", 100))
        logger.info(f"ByzantineFaultTolerance initialized f={self.fault_tolerance}", "consensus")

    def vote(self, node_id: str, proposal: Any) -> Dict[str, Any]:
        logger.debug(f"[ByzantineFaultTolerance.vote] node={node_id}")
        if node_id not in self.vote_history:
            self.vote_history[node_id] = []
        self.vote_history[node_id].append(proposal)
        if len(self.vote_history[node_id]) > self.max_history:
            self.vote_history[node_id].pop(0)
        all_votes: List[Any] = []
        for votes in self.vote_history.values():
            if votes:
                all_votes.append(votes[-1])
        if not all_votes:
            return {"consensus": False, "value": None, "agreement_ratio": 0.0}
        values, counts = np.unique(all_votes, return_counts=True)
        max_idx = int(np.argmax(counts))
        winner = values[max_idx]
        agreement = float(counts[max_idx] / len(all_votes))
        consensus = bool(counts[max_idx] > len(all_votes) / 2)
        result = {
            "consensus": consensus,
            "value": winner,
            "agreement_ratio": agreement,
        }
        logger.debug(f"[ByzantineFaultTolerance.vote] consensus={consensus} agreement={agreement:.4f}")
        return result

    def suspect(self, node_id: str, deviation: float) -> None:
        logger.debug(f"[ByzantineFaultTolerance.suspect] node={node_id} dev={deviation:.4f}")
        current = self.suspicion_scores.get(node_id, 0.0)
        self.suspicion_scores[node_id] = min(1.0, current + deviation)
        if self.suspicion_scores[node_id] > 0.8:
            logger.warning(f"[ByzantineFaultTolerance.suspect] node {node_id} highly suspected", "consensus")

    def get_suspected_nodes(self) -> List[str]:
        return [n for n, s in self.suspicion_scores.items() if s > 0.8]

    def get_state(self) -> Dict[str, Any]:
        return {
            "fault_tolerance": self.fault_tolerance,
            "suspected_nodes": self.get_suspected_nodes(),
            "node_count": len(self.vote_history),
        }


class ConflictResolver:
    """冲突解析器（版本向量、最后写入胜出）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[ConflictResolver.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.strategy: str = str(config.get("strategy", "last_write_wins"))
        self.version_vectors: Dict[str, Dict[str, int]] = {}
        self.history: List[Dict[str, Any]] = []
        self.max_history: int = int(config.get("max_history", 200))
        logger.info(f"ConflictResolver initialized strategy={self.strategy}", "consensus")

    def resolve(self, key: str, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        logger.debug(f"[ConflictResolver.resolve] key={key} candidates={len(candidates)}")
        Validator.require_type(candidates, list, "candidates")
        if not candidates:
            raise ValidationError("candidates cannot be empty")
        if self.strategy == "last_write_wins":
            winner = max(candidates, key=lambda x: x.get("timestamp", 0.0))
        elif self.strategy == "version_vector":
            winner = self._version_vector_resolve(key, candidates)
        else:
            winner = candidates[0]
        self._add_history({"key": key, "winner": winner})
        logger.debug(f"[ConflictResolver.resolve] strategy={self.strategy}")
        return winner

    def _version_vector_resolve(self, key: str, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        vv = self.version_vectors.get(key, {})
        best = candidates[0]
        best_score = 0
        for c in candidates:
            node = str(c.get("node_id", "unknown"))
            ts = int(c.get("timestamp", 0))
            score = vv.get(node, 0) * 1000 + ts
            if score > best_score:
                best_score = score
                best = c
            vv[node] = vv.get(node, 0) + 1
        self.version_vectors[key] = vv
        return best

    def _add_history(self, record: Dict[str, Any]) -> None:
        self.history.append(record)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        logger.debug(f"[ConflictResolver._add_history] size={len(self.history)}")

    def get_state(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "history_size": len(self.history),
            "tracked_keys": list(self.version_vectors.keys()),
        }


class DistributedStateModule:
    """分布式共识与拜占庭容错主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[DistributedStateModule.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.raft = RaftLikeConsensus(config.get("raft", {}))
        logger.debug("[DistributedStateModule.__init__] raft created")
        self.bft = ByzantineFaultTolerance(config.get("bft", {}))
        logger.debug("[DistributedStateModule.__init__] bft created")
        self.conflict = ConflictResolver(config.get("conflict", {}))
        logger.debug("[DistributedStateModule.__init__] conflict created")
        logger.info("DistributedStateModule initialized", "consensus")

    def propose(self, value: Any) -> Dict[str, Any]:
        logger.debug("[DistributedStateModule.propose] start")
        entry = {"term": self.raft.term, "value": value, "timestamp": time.time()}
        self.raft.log.append(entry)
        vote_result = self.bft.vote(self.raft.node_id, value)
        return {
            "accepted": vote_result["consensus"],
            "term": self.raft.term,
            "vote": vote_result,
        }

    def replicate(self, leader_id: str, entries: List[Dict[str, Any]], term: Optional[int] = None) -> bool:
        logger.debug("[DistributedStateModule.replicate] start")
        use_term = self.raft.term if term is None else term
        return self.raft.append_entries(leader_id, use_term, entries)

    def resolve_conflict(self, key: str, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        logger.debug(f"[DistributedStateModule.resolve_conflict] key={key}")
        return self.conflict.resolve(key, candidates)

    def report_deviation(self, node_id: str, deviation: float) -> None:
        logger.debug(f"[DistributedStateModule.report_deviation] node={node_id}")
        self.bft.suspect(node_id, deviation)

    def get_state(self) -> Dict[str, Any]:
        return {
            "raft": self.raft.get_state(),
            "bft": self.bft.get_state(),
            "conflict": self.conflict.get_state(),
        }
