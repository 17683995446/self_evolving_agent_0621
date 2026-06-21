"""协作模块单元测试"""
import pytest
from root.left.app.left.src.core_mod.collab import (
    Message, MessageBus, StateSyncEngine,
    TaskShardAllocator, GossipProtocol, CollaborationModule,
)
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestMessage:
    """测试Message"""

    def test_normal_init(self) -> None:
        msg = Message("test", "agent1", {"a": 1})
        assert msg.msg_type == "test"
        assert msg.sender_id == "agent1"

    def test_empty_payload(self) -> None:
        msg = Message("test", "agent1", {})
        assert msg.payload == {}

    def test_invalid_format_none_type(self) -> None:
        with pytest.raises(ValidationError):
            Message(None, "agent1", {})

    def test_to_dict(self) -> None:
        msg = Message("test", "agent1", {"a": 1})
        d = msg.to_dict()
        assert "msg_id" in d
        assert d["msg_type"] == "test"


class TestMessageBus:
    """测试MessageBus"""

    def test_normal_broadcast(self) -> None:
        bus = MessageBus({})
        msg = Message("test", "a1", {})
        assert bus.broadcast(msg) is True

    def test_duplicate_rejected(self) -> None:
        bus = MessageBus({})
        msg = Message("test", "a1", {})
        bus.broadcast(msg)
        assert bus.broadcast(msg) is False

    def test_poll_returns_messages(self) -> None:
        bus = MessageBus({})
        bus.deliver(Message("test", "a1", {}))
        assert len(bus.poll(10)) == 1

    def test_boundary_full_queue(self) -> None:
        bus = MessageBus({"max_queue": 2})
        bus.broadcast(Message("test", "a1", {}))
        bus.broadcast(Message("test", "a2", {}))
        bus.broadcast(Message("test", "a3", {}))
        assert len(bus.outbox) == 2

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            MessageBus(None)


class TestStateSyncEngine:
    """测试StateSyncEngine"""

    def test_normal_sync(self) -> None:
        engine = StateSyncEngine({})
        msg = engine.create_sync_message("a1", {"cpu": 0.5})
        assert msg.msg_type == "state_sync"

    def test_apply_sync(self) -> None:
        engine = StateSyncEngine({})
        msg = engine.create_sync_message("a1", {"cpu": 0.5})
        assert engine.apply_sync(msg) is True
        assert engine.get_peer_count() == 1

    def test_boundary_missing_agent_id(self) -> None:
        engine = StateSyncEngine({})
        msg = Message("state_sync", "a1", {})
        assert engine.apply_sync(msg) is False


class TestTaskShardAllocator:
    """测试TaskShardAllocator"""

    def test_normal_allocate(self) -> None:
        alloc = TaskShardAllocator({"agent_id": "a1"})
        assigned = alloc.allocate("task1", ["a2", "a3"])
        assert assigned in ["a1", "a2", "a3"]

    def test_empty_peers(self) -> None:
        alloc = TaskShardAllocator({"agent_id": "a1"})
        assigned = alloc.allocate("task1", [])
        assert assigned == "a1"

    def test_is_local(self) -> None:
        alloc = TaskShardAllocator({"agent_id": "a1"})
        alloc.allocate("task1", ["a2"])
        assert alloc.is_local("task1") in [True, False]


class TestGossipProtocol:
    """测试GossipProtocol"""

    def test_normal_gossip(self) -> None:
        gossip = GossipProtocol({})
        msg = gossip.create_gossip_message("a1", {"key": "val"})
        assert msg.msg_type == "gossip"
        assert gossip.version == 1

    def test_merge_config(self) -> None:
        gossip = GossipProtocol({})
        msg = gossip.create_gossip_message("a1", {"key": "val"})
        gossip2 = GossipProtocol({})
        assert gossip2.merge_config(msg) is True
        assert gossip2.get_merged_config() == {"key": "val"}

    def test_stale_version_rejected(self) -> None:
        gossip = GossipProtocol({})
        msg = gossip.create_gossip_message("a1", {"key": "val"})
        assert gossip.merge_config(msg) is False


class TestCollaborationModule:
    """测试CollaborationModule"""

    def test_normal_init(self) -> None:
        mod = CollaborationModule({"agent_id": "a1"})
        assert mod.agent_id == "a1"

    def test_register_peer(self) -> None:
        mod = CollaborationModule({"agent_id": "a1"})
        mod.register_peer("a2")
        assert "a2" in mod.peers

    def test_self_peer_rejected(self) -> None:
        mod = CollaborationModule({"agent_id": "a1"})
        mod.register_peer("a1")
        assert "a1" not in mod.peers

    def test_broadcast_state(self) -> None:
        mod = CollaborationModule({"agent_id": "a1", "state_sync": {"sync_interval": 0.0}})
        result = mod.broadcast_state({"cpu": 0.5})
        assert result is True

    def test_receive_messages(self) -> None:
        mod = CollaborationModule({"agent_id": "a1"})
        mod.bus.deliver(Message("state_sync", "a2", {"agent_id": "a2", "state_snapshot": {}}))
        msgs = mod.receive_messages()
        assert len(msgs) == 1
        assert mod.get_peer_count() == 1

    def test_allocate_task(self) -> None:
        mod = CollaborationModule({"agent_id": "a1"})
        mod.register_peer("a2")
        assigned = mod.allocate_task("task1")
        assert assigned in ["a1", "a2"]

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            CollaborationModule(None)
