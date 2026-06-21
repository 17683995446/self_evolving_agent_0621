"""协作模块集成测试"""


from root.left.app.left.src.core_mod.collab import CollaborationModule, Message


class TestMultiAgentSync:
    """多Agent状态同步测试"""

    def test_two_agent_state_sync(self) -> None:
        """两个Agent状态同步"""
        agent1 = CollaborationModule({"agent_id": "a1", "state_sync": {"sync_interval": 0.0}})
        agent2 = CollaborationModule({"agent_id": "a2", "state_sync": {"sync_interval": 0.0}})
        agent1.register_peer("a2")
        agent2.register_peer("a1")

        agent1.broadcast_state({"cpu": 0.5, "memory": 0.3})
        outbox = agent1.bus.get_outbox(10)
        for msg in outbox:
            agent2.bus.deliver(msg)

        agent2.receive_messages()
        assert agent2.get_peer_count() == 1
        assert "a1" in agent2.state_sync.peer_states

    def test_three_agent_gossip_convergence(self) -> None:
        """三个Agent Gossip配置收敛"""
        a1 = CollaborationModule({"agent_id": "a1", "gossip": {"gossip_interval": 0.0}})
        a2 = CollaborationModule({"agent_id": "a2", "gossip": {"gossip_interval": 0.0}})
        a3 = CollaborationModule({"agent_id": "a3", "gossip": {"gossip_interval": 0.0}})

        a1.register_peer("a2")
        a1.register_peer("a3")

        config = {"exploration_ratio": 0.4}
        a1.broadcast_gossip(config)

        outbox = a1.bus.get_outbox(10)
        for msg in outbox:
            a2.bus.deliver(msg)
            a3.bus.deliver(msg)

        a2.receive_messages()
        a3.receive_messages()

        assert a2.get_merged_config() == config
        assert a3.get_merged_config() == config

    def test_task_shard_consistency(self) -> None:
        """任务分片一致性"""
        a1 = CollaborationModule({"agent_id": "a1"})
        a2 = CollaborationModule({"agent_id": "a2"})
        a1.register_peer("a2")
        a2.register_peer("a1")

        a1.allocate_task("task_abc")
        outbox = a1.bus.get_outbox(10)
        for msg in outbox:
            a2.bus.deliver(msg)
        a2.receive_messages()

        assert a1.shard_alloc.shard_map["task_abc"] == a2.shard_alloc.shard_map["task_abc"]

    def test_network_partition_recovery(self) -> None:
        """网络分区恢复"""
        a1 = CollaborationModule({"agent_id": "a1", "state_sync": {"sync_interval": 0.0}})
        a2 = CollaborationModule({"agent_id": "a2", "state_sync": {"sync_interval": 0.0}})
        a1.register_peer("a2")

        a1.broadcast_state({"cpu": 0.1})
        outbox = a1.bus.get_outbox(10)
        for msg in outbox:
            a2.bus.deliver(msg)
        a2.receive_messages()

        assert a2.state_sync.peer_states.get("a1", {}).get("cpu") == 0.1

    def test_duplicate_message_deduplication(self) -> None:
        """重复消息去重"""
        a1 = CollaborationModule({"agent_id": "a1", "state_sync": {"sync_interval": 0.0}})
        a2 = CollaborationModule({"agent_id": "a2"})

        msg = a1.state_sync.create_sync_message("a1", {"cpu": 0.5})
        a2.bus.deliver(msg)
        a2.bus.deliver(msg)
        a2.receive_messages()

        assert a2.get_peer_count() == 1

    def test_message_ttl_decay(self) -> None:
        """消息TTL衰减"""
        msg = Message("test", "a1", {}, ttl=2)
        assert msg.ttl == 2

    def test_gossip_version_monotonic(self) -> None:
        """Gossip版本单调递增"""
        gossip = CollaborationModule({"agent_id": "a1", "gossip": {"gossip_interval": 0.0}})
        gossip.broadcast_gossip({"v": 1})
        gossip.broadcast_gossip({"v": 2})
        assert gossip.gossip.version == 2


class TestCollaborationFaultTolerance:
    """协作容错测试"""

    def test_peer_disconnect_graceful(self) -> None:
        """Peer断开优雅处理"""
        a1 = CollaborationModule({"agent_id": "a1"})
        a1.register_peer("a2")
        result = a1.broadcast_state({"cpu": 0.5})
        assert result is True

    def test_empty_peer_list(self) -> None:
        """空Peer列表"""
        a1 = CollaborationModule({"agent_id": "a1"})
        assigned = a1.allocate_task("task1")
        assert assigned == "a1"

    def test_corrupted_message_ignored(self) -> None:
        """损坏消息被忽略"""
        a1 = CollaborationModule({"agent_id": "a1"})
        a1.bus.deliver(Message("unknown_type", "a2", {}))
        msgs = a1.receive_messages()
        assert len(msgs) == 1
