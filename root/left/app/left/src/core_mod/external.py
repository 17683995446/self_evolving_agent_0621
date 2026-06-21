"""外部系统集成适配器模块"""
import copy
import json
import os
import threading
import time
import uuid
from typing import Any, Dict, Final, List, Optional

from root.left.app.left.src.utils_main.exceptions import ExternalIntegrationException
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class HttpClient:
    """HTTP客户端（模拟）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[HttpClient.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.base_url: str = str(config.get("base_url", "http://localhost:8080"))
        self.timeout: float = float(config.get("timeout", 5.0))
        self.max_retries: int = int(config.get("max_retries", 3))
        self.retry_delay: float = float(config.get("retry_delay", 1.0))
        self.circuit_open: bool = False
        self.failure_count: int = 0
        self.failure_threshold: int = int(config.get("failure_threshold", 5))
        self.circuit_timeout: float = float(config.get("circuit_timeout", 30.0))
        self._circuit_opened_at: float = 0.0
        self._lock = threading.Lock()
        logger.info(f"HttpClient initialized base_url={self.base_url}", "external")

    def _check_circuit(self) -> bool:
        logger.debug("[HttpClient._check_circuit] start")
        with self._lock:
            if self.circuit_open:
                if time.time() - self._circuit_opened_at >= self.circuit_timeout:
                    logger.info("[HttpClient._check_circuit] circuit half-open", "external")
                    self.circuit_open = False
                    self.failure_count = 0
                else:
                    logger.warning("[HttpClient._check_circuit] circuit open", "external")
                    return False
        logger.debug("[HttpClient._check_circuit] circuit closed")
        return True

    def _record_success(self) -> None:
        logger.debug("[HttpClient._record_success] start")
        with self._lock:
            self.failure_count = 0
            logger.debug("[HttpClient._record_success] failure_count reset")

    def _record_failure(self) -> None:
        logger.debug("[HttpClient._record_failure] start")
        with self._lock:
            self.failure_count += 1
            logger.debug(f"[HttpClient._record_failure] failure_count={self.failure_count}")
            if self.failure_count >= self.failure_threshold:
                self.circuit_open = True
                self._circuit_opened_at = time.time()
                logger.error("[HttpClient._record_failure] circuit opened", "external")

    def get(self, path: str) -> Dict[str, Any]:
        logger.debug(f"[HttpClient.get] path={path}")
        if not self._check_circuit():
            raise ExternalIntegrationException("Circuit breaker open", service="http")
        url = f"{self.base_url}{path}"
        for attempt in range(self.max_retries):
            logger.debug(f"[HttpClient.get] attempt={attempt + 1}/{self.max_retries}")
            try:
                result = self._simulate_request("GET", url)
                self._record_success()
                logger.debug("[HttpClient.get] success")
                return result
            except Exception as e:
                logger.warning(f"[HttpClient.get] attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        self._record_failure()
        raise ExternalIntegrationException("Max retries exceeded", service="http")

    def post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug(f"[HttpClient.post] path={path}")
        if not self._check_circuit():
            raise ExternalIntegrationException("Circuit breaker open", service="http")
        url = f"{self.base_url}{path}"
        for attempt in range(self.max_retries):
            logger.debug(f"[HttpClient.post] attempt={attempt + 1}/{self.max_retries}")
            try:
                result = self._simulate_request("POST", url, data)
                self._record_success()
                logger.debug("[HttpClient.post] success")
                return result
            except Exception as e:
                logger.warning(f"[HttpClient.post] attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        self._record_failure()
        raise ExternalIntegrationException("Max retries exceeded", service="http")

    def _simulate_request(
        self, method: str, url: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        logger.debug(f"[HttpClient._simulate_request] method={method} url={url}")
        import random
        if random.random() < 0.05:
            raise ConnectionError("Simulated network failure")
        return {
            "status": 200,
            "method": method,
            "url": url,
            "data": data,
            "timestamp": time.time(),
        }


class IdempotencyStore:
    """幂等性存储"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[IdempotencyStore.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.ttl: float = float(config.get("ttl", 3600.0))
        self._store: Dict[str, float] = {}
        self._lock = threading.Lock()
        logger.info(f"IdempotencyStore initialized ttl={self.ttl}", "external")

    def check_or_record(self, key: str) -> bool:
        logger.debug(f"[IdempotencyStore.check_or_record] key={key}")
        with self._lock:
            now = time.time()
            self._cleanup(now)
            if key in self._store:
                logger.debug(f"[IdempotencyStore.check_or_record] duplicate key={key}")
                return False
            self._store[key] = now
            logger.debug(f"[IdempotencyStore.check_or_record] recorded key={key}")
            return True

    def _cleanup(self, now: float) -> None:
        stale = [k for k, v in self._store.items() if now - v > self.ttl]
        for k in stale:
            del self._store[k]
        if stale:
            logger.debug(f"[IdempotencyStore._cleanup] cleared={len(stale)}")


class MessageQueue:
    """内存消息队列（模拟MQ）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[MessageQueue.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.max_size: int = int(config.get("max_size", 1000))
        self.queues: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = threading.Lock()
        logger.info(f"MessageQueue initialized max_size={self.max_size}", "external")

    def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        logger.debug(f"[MessageQueue.publish] topic={topic}")
        Validator.require_type(topic, str, "topic")
        Validator.require_type(message, dict, "message")
        with self._lock:
            if topic not in self.queues:
                self.queues[topic] = []
            if len(self.queues[topic]) >= self.max_size:
                self.queues[topic].pop(0)
                logger.debug(f"[MessageQueue.publish] topic={topic} full, dropped oldest")
            msg = {
                "id": str(uuid.uuid4()),
                "payload": copy.deepcopy(message),
                "timestamp": time.time(),
            }
            self.queues[topic].append(msg)
            logger.debug(f"[MessageQueue.publish] topic={topic} queued msg_id={msg['id']}")
            return True

    def consume(self, topic: str, count: int = 10) -> List[Dict[str, Any]]:
        logger.debug(f"[MessageQueue.consume] topic={topic} count={count}")
        with self._lock:
            q = self.queues.get(topic, [])
            result = q[:count]
            self.queues[topic] = q[count:]
            logger.debug(f"[MessageQueue.consume] topic={topic} returned={len(result)}")
            return result

    def get_queue_depth(self, topic: str) -> int:
        logger.debug(f"[MessageQueue.get_queue_depth] topic={topic}")
        with self._lock:
            depth = len(self.queues.get(topic, []))
            logger.debug(f"[MessageQueue.get_queue_depth] topic={topic} depth={depth}")
            return depth


class FileSystemAdapter:
    """文件系统适配器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[FileSystemAdapter.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.base_path: str = str(config.get("base_path", "/tmp/agent_data"))
        os.makedirs(self.base_path, exist_ok=True)
        logger.info(f"FileSystemAdapter initialized base_path={self.base_path}", "external")

    def write_json(self, filename: str, data: Dict[str, Any]) -> str:
        logger.debug(f"[FileSystemAdapter.write_json] filename={filename}")
        filepath = os.path.join(self.base_path, filename)
        with open(filepath, "w") as f:
            json.dump(data, f)
        logger.info(f"[FileSystemAdapter.write_json] written={filepath}", "external")
        return filepath

    def read_json(self, filename: str) -> Dict[str, Any]:
        logger.debug(f"[FileSystemAdapter.read_json] filename={filename}")
        filepath = os.path.join(self.base_path, filename)
        with open(filepath, "r") as f:
            data = json.load(f)
        logger.debug(f"[FileSystemAdapter.read_json] loaded={filepath}")
        return data

    def delete(self, filename: str) -> bool:
        logger.debug(f"[FileSystemAdapter.delete] filename={filename}")
        filepath = os.path.join(self.base_path, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.debug(f"[FileSystemAdapter.delete] removed={filepath}")
            return True
        logger.debug(f"[FileSystemAdapter.delete] not_found={filepath}")
        return False


class ExternalIntegrationModule:
    """外部集成模块主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[ExternalIntegrationModule.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.http = HttpClient(config.get("http", {}))
        logger.debug("[ExternalIntegrationModule.__init__] http created")
        self.idempotency = IdempotencyStore(config.get("idempotency", {}))
        logger.debug("[ExternalIntegrationModule.__init__] idempotency created")
        self.mq = MessageQueue(config.get("mq", {}))
        logger.debug("[ExternalIntegrationModule.__init__] mq created")
        self.fs = FileSystemAdapter(config.get("fs", {}))
        logger.debug("[ExternalIntegrationModule.__init__] fs created")
        logger.info("ExternalIntegrationModule initialized", "external")

    def publish_event(self, topic: str, event: Dict[str, Any]) -> bool:
        logger.debug(f"[ExternalIntegrationModule.publish_event] topic={topic}")
        return self.mq.publish(topic, event)

    def consume_events(self, topic: str, count: int = 10) -> List[Dict[str, Any]]:
        logger.debug(f"[ExternalIntegrationModule.consume_events] topic={topic}")
        return self.mq.consume(topic, count)

    def call_external_api(
        self, path: str, method: str = "GET", data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        logger.debug(f"[ExternalIntegrationModule.call_external_api] path={path} method={method}")
        if method.upper() == "GET":
            return self.http.get(path)
        return self.http.post(path, data or {})

    def persist_state(self, filename: str, state: Dict[str, Any]) -> str:
        logger.debug(f"[ExternalIntegrationModule.persist_state] filename={filename}")
        return self.fs.write_json(filename, state)

    def load_state(self, filename: str) -> Dict[str, Any]:
        logger.debug(f"[ExternalIntegrationModule.load_state] filename={filename}")
        return self.fs.read_json(filename)

    def is_idempotent(self, key: str) -> bool:
        logger.debug(f"[ExternalIntegrationModule.is_idempotent] key={key}")
        return self.idempotency.check_or_record(key)
