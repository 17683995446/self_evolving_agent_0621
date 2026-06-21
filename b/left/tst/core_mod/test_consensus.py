"""分布式共识与拜占庭容错模块测试"""
import pytest

from root.left.app.left.src.core_mod.consensus import (
    ByzantineFaultTolerance,
    ConflictResolver,
    DistributedStateModule,
    RaftLikeConsensus,
)
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestRaftLikeConsensus:
    """RaftLikeConsensus 单元测试"""

    def test_init_normal(self) -> None:
        raft = RaftLikeConsensus({"node_id": "n1", "nodes": ["n1", "n2"]})
        assert raft.node_id == "n1"
        assert raft.term == 0

    def test_request_vote_new_term(self) -> None:
        raft = RaftLikeConsensus({})
        result = raft.request_vote("n2", 1)
        assert result is True
        assert raft.term == 1
        assert raft.voted_for == "n2"

    def test_request_vote_same_term_twice(self) -> None:
        raft = RaftLikeConsensus({})
        raft.request_vote("n2", 1)
        result = raft.request_vote("n3", 1)
        assert result is False

    def test_append_entries(self) -> None:
        raft = RaftLikeConsensus({})
        result = raft.append_entries("leader", 1, [{"v": 1}])
        assert result is True
        assert raft.leader == "leader"
        assert len(raft.log) == 1

    def test_append_entries_old_term(self) -> None:
        raft = RaftLikeConsensus({})
        raft.term = 2
        result = raft.append_entries("leader", 1, [{"v": 1}])
        assert result is False

    def test_become_candidate(self) -> None:
        raft = RaftLikeConsensus({})
        raft.become_candidate()
        assert raft.term == 1
        assert raft.voted_for == "node_0"

    def test_get_state(self) -> None:
        raft = RaftLikeConsensus({"node_id": "n1"})
        s = raft.get_state()
        assert s["node_id"] == "n1"


class TestByzantineFaultTolerance:
    """ByzantineFaultTolerance 单元测试"""

    def test_init_normal(self) -> None:
        bft = ByzantineFaultTolerance({"fault_tolerance": 2})
        assert bft.fault_tolerance == 2

    def test_vote_consensus(self) -> None:
        bft = ByzantineFaultTolerance({})
        bft.vote("n1", "A")
        bft.vote("n2", "A")
        bft.vote("n3", "B")
        result = bft.vote("n1", "A")
        assert result["consensus"] is True
        assert result["value"] == "A"
        assert result["agreement_ratio"] > 0.5

    def test_vote_no_consensus(self) -> None:
        bft = ByzantineFaultTolerance({})
        bft.vote("n1", "A")
        bft.vote("n2", "B")
        result = bft.vote("n3", "C")
        assert result["consensus"] is False

    def test_vote_empty(self) -> None:
        bft = ByzantineFaultTolerance({})
        result = bft.vote("n1", "A")
        # Single node: agreement=1.0, consensus=True (majority of 1 is 1)
        assert result["consensus"] is True
        assert result["agreement_ratio"] == 1.0

    def test_suspect(self) -> None:
        bft = ByzantineFaultTolerance({})
        bft.suspect("n1", 0.5)
        assert bft.suspicion_scores["n1"] == 0.5

    def test_suspect_high(self) -> None:
        bft = ByzantineFaultTolerance({})
        bft.suspect("n1", 0.5)
        bft.suspect("n1", 0.5)
        assert "n1" in bft.get_suspected_nodes()

    def test_history_trim(self) -> None:
        bft = ByzantineFaultTolerance({"max_history": 2})
        for i in range(5):
            bft.vote("n1", f"v{i}")
        assert len(bft.vote_history["n1"]) == 2

    def test_get_state(self) -> None:
        bft = ByzantineFaultTolerance({})
        s = bft.get_state()
        assert s["fault_tolerance"] == 1


class TestConflictResolver:
    """ConflictResolver 单元测试"""

    def test_init_normal(self) -> None:
        cr = ConflictResolver({"strategy": "version_vector"})
        assert cr.strategy == "version_vector"

    def test_resolve_last_write_wins(self) -> None:
        cr = ConflictResolver({})
        candidates = [
            {"timestamp": 1.0, "value": "old"},
            {"timestamp": 3.0, "value": "new"},
            {"timestamp": 2.0, "value": "mid"},
        ]
        winner = cr.resolve("k1", candidates)
        assert winner["value"] == "new"

    def test_resolve_version_vector(self) -> None:
        cr = ConflictResolver({"strategy": "version_vector"})
        candidates = [
            {"node_id": "n1", "timestamp": 1, "value": "a"},
            {"node_id": "n2", "timestamp": 2, "value": "b"},
        ]
        winner = cr.resolve("k1", candidates)
        assert "value" in winner

    def test_resolve_empty_raises(self) -> None:
        cr = ConflictResolver({})
        with pytest.raises(ValidationError):
            cr.resolve("k1", [])

    def test_history_trim(self) -> None:
        cr = ConflictResolver({"max_history": 2})
        for i in range(5):
            cr.resolve("k1", [{"timestamp": float(i)}])
        assert len(cr.history) == 2

    def test_get_state(self) -> None:
        cr = ConflictResolver({})
        s = cr.get_state()
        assert s["strategy"] == "last_write_wins"


class TestDistributedStateModule:
    """DistributedStateModule 集成测试"""

    def test_init_normal(self) -> None:
        mod = DistributedStateModule({})
        assert mod.raft is not None
        assert mod.bft is not None
        assert mod.conflict is not None

    def test_propose(self) -> None:
        mod = DistributedStateModule({})
        result = mod.propose("value_A")
        assert "accepted" in result
        assert "term" in result
        assert "vote" in result
        assert len(mod.raft.log) >= 1

    def test_replicate(self) -> None:
        mod = DistributedStateModule({})
        result = mod.replicate("leader1", [{"v": 1}, {"v": 2}])
        assert result is True
        assert mod.raft.leader == "leader1"
        assert len(mod.raft.log) == 2

    def test_replicate_old_term(self) -> None:
        mod = DistributedStateModule({})
        mod.raft.term = 5
        result = mod.replicate("leader", [{"v": 1}], term=1)
        assert result is False

    def test_resolve_conflict(self) -> None:
        mod = DistributedStateModule({})
        candidates = [
            {"timestamp": 1.0, "value": "a"},
            {"timestamp": 2.0, "value": "b"},
        ]
        winner = mod.resolve_conflict("k1", candidates)
        assert winner["value"] == "b"

    def test_report_deviation(self) -> None:
        mod = DistributedStateModule({})
        mod.report_deviation("n1", 0.9)
        assert "n1" in mod.bft.get_suspected_nodes()

    def test_get_state(self) -> None:
        mod = DistributedStateModule({})
        s = mod.get_state()
        assert "raft" in s
        assert "bft" in s
        assert "conflict" in s

    def test_boundary_single_candidate(self) -> None:
        mod = DistributedStateModule({})
        winner = mod.resolve_conflict("k1", [{"timestamp": 1.0, "value": "only"}])
        assert winner["value"] == "only"

    def test_boundary_single_node_vote(self) -> None:
        mod = DistributedStateModule({})
        result = mod.propose("X")
        assert result["vote"]["agreement_ratio"] == 1.0
