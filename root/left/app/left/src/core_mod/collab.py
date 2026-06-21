"""多Agent协作模块"""
import copy
import threading
import time
import uuid
from typing import Any, Dict, Final, List, Optional, Set

from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class Message:
    """消息实体"""

    def __init__(
        self,
        msg_type: str,
        sender_id: str,
        payload: Dict[str, Any],
        ttl: int = 3
    ) -> None:
        Validator.require_type(msg_type, str, "msg_type")
        Validator.require_type(sender_id, str, "sender_id")
        Validator.require_type(payload, dict, "payload")
        self.msg_id: str = str(uuid.uuid4())
        self.msg_type: str = msg_type
        self.sender_id: str = sender_id
        self.payload: Dict[str, Any] = copy.deepcopy(payload)
        self.ttl: int = int(ttl)
        self.timestamp: float = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "msg_id": self.msg_id,
            "msg_type": self.msg_type,
            "sender_id": self.sender_id,
            "payload": self.payload,
            "ttl": self.ttl,
            "timestamp": self.timestamp,
        }


class MessageBus:
    """内存消息总线（模拟网络层）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[MessageBus.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.max_queue: int = int(config.get("max_queue", 1000))
        self.inbox: List[Message] = []
        self.outbox: List[Message] = []
        self._lock = threading.Lock()
        self._seen: Set[str] = set()
        logger.info(f"MessageBus initialized max_queue={self.max_queue}", "collab")

    def broadcast(self, msg: Message) -> bool:
        logger.debug(f"[MessageBus.broadcast] msg_id={msg.msg_id} type={msg.msg_type}")
        with self._lock:
            if msg.msg_id in self._seen:
                logger.debug(f"[MessageBus.broadcast] duplicate msg_id={msg.msg_id}")
                return False
            self._seen.add(msg.msg_id)
            if len(self.outbox) >= self.max_queue:
                removed = self.outbox.pop(0)
                logger.debug(f"[MessageBus.broadcast] outbox full, dropped oldest msg_id={removed.msg_id}")
            self.outbox.append(msg)
            logger.debug(f"[MessageBus.broadcast] msg queued msg_id={msg.msg_id}")
            return True

    def deliver(self, msg: Message) -> bool:
        logger.debug(f"[MessageBus.deliver] msg_id={msg.msg_id} from={msg.sender_id}")
        with self._lock:
            if msg.msg_id in self._seen:
                logger.debug(f"[MessageBus.deliver] duplicate msg_id={msg.msg_id}")
                return False
            self._seen.add(msg.msg_id)
            if len(self.inbox) >= self.max_queue:
                removed = self.inbox.pop(0)
                logger.debug(f"[MessageBus.deliver] inbox full, dropped oldest msg_id={removed.msg_id}")
            self.inbox.append(msg)
            logger.debug(f"[MessageBus.deliver] msg delivered msg_id={msg.msg_id}")
            return True

    def poll(self, count: int = 10) -> List[Message]:
        logger.debug(f"[MessageBus.poll] count={count}")
        with self._lock:
            result = self.inbox[:count]
            self.inbox = self.inbox[count:]
            logger.debug(f"[MessageBus.poll] returned={len(result)} remaining={len(self.inbox)}")
            return result

    def get_outbox(self, count: int = 10) -> List[Message]:
        logger.debug(f"[MessageBus.get_outbox] count={count}")
        with self._lock:
            result = self.outbox[:count]
            self.outbox = self.outbox[count:]
            logger.debug(f"[MessageBus.get_outbox] returned={len(result)} remaining={len(self.outbox)}")
            return result

    def clear_seen(self) -> None:
        logger.debug("[MessageBus.clear_seen] start")
        with self._lock:
            self._seen.clear()
            logger.debug("[MessageBus.clear_seen] done")


class StateSyncEngine:
    """状态同步引擎"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[StateSyncEngine.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.sync_interval: float = float(config.get("sync_interval", 5.0))
        self.last_sync: float = 0.0
        self.peer_states: Dict[str, Dict[str, Any]] = {}
        logger.info(f"StateSyncEngine initialized interval={self.sync_interval}", "collab")

    def should_sync(self) -> bool:
        result = time.time() - self.last_sync >= self.sync_interval
        logger.debug(f"[StateSyncEngine.should_sync] result={result}")
        return result

    def create_sync_message(
        self, agent_id: str, state: Dict[str, Any]
    ) -> Message:
        logger.debug(f"[StateSyncEngine.create_sync_message] agent_id={agent_id}")
        payload = {
            "agent_id": agent_id,
            "state_snapshot": copy.deepcopy(state),
            "timestamp": time.time(),
        }
        msg = Message("state_sync", agent_id, payload)
        self.last_sync = time.time()
        logger.debug(f"[StateSyncEngine.create_sync_message] msg_id={msg.msg_id}")
        return msg

    def apply_sync(self, msg: Message) -> bool:
        logger.debug(f"[StateSyncEngine.apply_sync] msg_id={msg.msg_id}")
        payload = msg.payload
        peer_id = payload.get("agent_id")
        if not peer_id:
            logger.warning("[StateSyncEngine.apply_sync] missing agent_id")
            return False
        self.peer_states[peer_id] = payload.get("state_snapshot", {})
        logger.info(f"[StateSyncEngine.apply_sync] synced peer={peer_id}", "collab")
        return True

    def get_peer_count(self) -> int:
        count = len(self.peer_states)
        logger.debug(f"[StateSyncEngine.get_peer_count] count={count}")
        return count


class TaskShardAllocator:
    """任务分片分配器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[TaskShardAllocator.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.agent_id: str = str(config.get("agent_id", uuid.uuid4()))
        self.shard_map: Dict[str, str] = {}
        logger.info(f"TaskShardAllocator initialized agent_id={self.agent_id}", "collab")

    def allocate(self, task_id: str, peer_ids: List[str]) -> str:
        logger.debug(f"[TaskShardAllocator.allocate] task_id={task_id} peers={len(peer_ids)}")
        if not peer_ids:
            logger.debug("[TaskShardAllocator.allocate] no peers -> self")
            return self.agent_id
        all_ids = peer_ids + [self.agent_id]
        idx = hash(task_id) % len(all_ids)
        assigned = all_ids[idx]
        self.shard_map[task_id] = assigned
        logger.debug(f"[TaskShardAllocator.allocate] task_id={task_id} -> agent={assigned}")
        return assigned

    def is_local(self, task_id: str) -> bool:
        result = self.shard_map.get(task_id, self.agent_id) == self.agent_id
        logger.debug(f"[TaskShardAllocator.is_local] task_id={task_id} result={result}")
        return result

    def create_alloc_message(
        self, task_id: str, peer_ids: List[str]
    ) -> Message:
        logger.debug(f"[TaskShardAllocator.create_alloc_message] task_id={task_id}")
        assigned = self.allocate(task_id, peer_ids)
        payload = {
            "task_id": task_id,
            "assigned_agent": assigned,
            "shard_map": copy.deepcopy(self.shard_map),
        }
        msg = Message("task_alloc", self.agent_id, payload)
        logger.debug(f"[TaskShardAllocator.create_alloc_message] msg_id={msg.msg_id}")
        return msg


class GossipProtocol:
    """Gossip配置传播协议"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[GossipProtocol.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.gossip_interval: float = float(config.get("gossip_interval", 3.0))
        self.fanout: int = int(config.get("fanout", 2))
        self.version: int = 0
        self.config_store: Dict[str, Any] = {}
        logger.info(f"GossipProtocol initialized fanout={self.fanout}", "collab")

    def should_gossip(self) -> bool:
        result = time.time() - getattr(self, '_last_gossip', 0) >= self.gossip_interval
        logger.debug(f"[GossipProtocol.should_gossip] result={result}")
        return result

    def create_gossip_message(
        self, agent_id: str, current_config: Dict[str, Any]
    ) -> Message:
        logger.debug(f"[GossipProtocol.create_gossip_message] agent_id={agent_id}")
        self.version += 1
        payload = {
            "version": self.version,
            "config": copy.deepcopy(current_config),
            "agent_id": agent_id,
        }
        msg = Message("gossip", agent_id, payload, ttl=self.fanout)
        self._last_gossip = time.time()
        logger.debug(f"[GossipProtocol.create_gossip_message] version={self.version}")
        return msg

    def merge_config(self, msg: Message) -> bool:
        logger.debug(f"[GossipProtocol.merge_config] msg_id={msg.msg_id}")
        payload = msg.payload
        incoming_version = payload.get("version", 0)
        if incoming_version <= self.version:
            logger.debug(f"[GossipProtocol.merge_config] stale version={incoming_version} current={self.version}")
            return False
        self.version = incoming_version
        self.config_store = copy.deepcopy(payload.get("config", {}))
        logger.info(f"[GossipProtocol.merge_config] updated to version={self.version}", "collab")
        return True

    def get_merged_config(self) -> Optional[Dict[str, Any]]:
        logger.debug(f"[GossipProtocol.get_merged_config] version={self.version}")
        return copy.deepcopy(self.config_store) if self.config_store else None


class CollaborationModule:
    """协作模块主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[CollaborationModule.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.agent_id: str = str(config.get("agent_id", uuid.uuid4()))
        logger.debug(f"[CollaborationModule.__init__] agent_id={self.agent_id}")
        self.bus = MessageBus(config.get("bus", {}))
        logger.debug("[CollaborationModule.__init__] bus created")
        self.state_sync = StateSyncEngine(config.get("state_sync", {}))
        logger.debug("[CollaborationModule.__init__] state_sync created")
        shard_cfg = dict(config.get("shard_alloc", {}))
        shard_cfg["agent_id"] = self.agent_id
        self.shard_alloc = TaskShardAllocator(shard_cfg)
        logger.debug("[CollaborationModule.__init__] shard_alloc created")
        self.gossip = GossipProtocol(config.get("gossip", {}))
        logger.debug("[CollaborationModule.__init__] gossip created")
        self.peers: List[str] = []
        logger.debug(f"[CollaborationModule.__init__] peers initialized count={len(self.peers)}")
        logger.info(f"CollaborationModule initialized agent_id={self.agent_id}", "collab")

    def register_peer(self, peer_id: str) -> None:
        logger.debug(f"[CollaborationModule.register_peer] peer_id={peer_id}")
        if peer_id not in self.peers and peer_id != self.agent_id:
            self.peers.append(peer_id)
            logger.info(f"[CollaborationModule.register_peer] peer registered={peer_id} total={len(self.peers)}", "collab")

    def broadcast_state(self, state: Dict[str, Any]) -> bool:
        logger.debug("[CollaborationModule.broadcast_state] start")
        if not self.state_sync.should_sync():
            logger.debug("[CollaborationModule.broadcast_state] skip sync")
            return False
        msg = self.state_sync.create_sync_message(self.agent_id, state)
        result = self.bus.broadcast(msg)
        logger.debug(f"[CollaborationModule.broadcast_state] result={result}")
        return result

    def broadcast_gossip(self, current_config: Dict[str, Any]) -> bool:
        logger.debug("[CollaborationModule.broadcast_gossip] start")
        if not self.gossip.should_gossip():
            logger.debug("[CollaborationModule.broadcast_gossip] skip gossip")
            return False
        msg = self.gossip.create_gossip_message(self.agent_id, current_config)
        result = self.bus.broadcast(msg)
        logger.debug(f"[CollaborationModule.broadcast_gossip] result={result}")
        return result

    def receive_messages(self) -> List[Message]:
        logger.debug("[CollaborationModule.receive_messages] start")
        msgs = self.bus.poll(50)
        for msg in msgs:
            logger.debug(f"[CollaborationModule.receive_messages] processing msg_id={msg.msg_id} type={msg.msg_type}")
            if msg.msg_type == "state_sync":
                self.state_sync.apply_sync(msg)
            elif msg.msg_type == "gossip":
                self.gossip.merge_config(msg)
            elif msg.msg_type == "task_alloc":
                self._apply_task_alloc(msg)
            else:
                logger.warning(f"[CollaborationModule.receive_messages] unknown msg_type={msg.msg_type}")
        logger.debug(f"[CollaborationModule.receive_messages] processed={len(msgs)}")
        return msgs

    def _apply_task_alloc(self, msg: Message) -> None:
        logger.debug(f"[CollaborationModule._apply_task_alloc] msg_id={msg.msg_id}")
        payload = msg.payload
        shard_map = payload.get("shard_map", {})
        self.shard_alloc.shard_map.update(shard_map)
        logger.debug("[CollaborationModule._apply_task_alloc] shard_map updated")

    def allocate_task(self, task_id: str) -> str:
        logger.debug(f"[CollaborationModule.allocate_task] task_id={task_id}")
        assigned = self.shard_alloc.allocate(task_id, self.peers)
        msg = self.shard_alloc.create_alloc_message(task_id, self.peers)
        self.bus.broadcast(msg)
        logger.debug(f"[CollaborationModule.allocate_task] assigned={assigned}")
        return assigned

    def is_local_task(self, task_id: str) -> bool:
        result = self.shard_alloc.is_local(task_id)
        logger.debug(f"[CollaborationModule.is_local_task] task_id={task_id} result={result}")
        return result

    def get_peer_count(self) -> int:
        count = self.state_sync.get_peer_count()
        logger.debug(f"[CollaborationModule.get_peer_count] count={count}")
        return count

    def get_merged_config(self) -> Optional[Dict[str, Any]]:
        result = self.gossip.get_merged_config()
        logger.debug(f"[CollaborationModule.get_merged_config] result={'present' if result else 'None'}")
        return result
