"""外部集成模块单元测试"""
import time

import pytest

from root.left.app.left.src.core_mod.external import (
    HttpClient, IdempotencyStore, MessageQueue,
    FileSystemAdapter, ExternalIntegrationModule,
)
from root.left.app.left.src.utils_main.exceptions import ValidationError, ExternalIntegrationException


class TestHttpClient:
    """测试HttpClient"""

    def test_normal_get(self) -> None:
        client = HttpClient({})
        result = client.get("/test")
        assert result["status"] == 200
        assert result["method"] == "GET"

    def test_normal_post(self) -> None:
        client = HttpClient({})
        result = client.post("/test", {"a": 1})
        assert result["status"] == 200
        assert result["method"] == "POST"

    def test_circuit_breaker(self) -> None:
        client = HttpClient({"failure_threshold": 1, "max_retries": 1, "retry_delay": 0.01})
        client.circuit_open = True
        client._circuit_opened_at = time.time()
        with pytest.raises(ExternalIntegrationException):
            client.get("/test")

    def test_boundary_invalid_config(self) -> None:
        with pytest.raises(ValidationError):
            HttpClient(None)


class TestIdempotencyStore:
    """测试IdempotencyStore"""

    def test_normal_first_call(self) -> None:
        store = IdempotencyStore({})
        assert store.check_or_record("key1") is True

    def test_duplicate_rejected(self) -> None:
        store = IdempotencyStore({})
        store.check_or_record("key1")
        assert store.check_or_record("key1") is False

    def test_boundary_ttl_expired(self) -> None:
        store = IdempotencyStore({"ttl": 0.01})
        store.check_or_record("key1")
        time.sleep(0.02)
        assert store.check_or_record("key1") is True


class TestMessageQueue:
    """测试MessageQueue"""

    def test_normal_publish_consume(self) -> None:
        mq = MessageQueue({})
        mq.publish("topic1", {"a": 1})
        msgs = mq.consume("topic1", 10)
        assert len(msgs) == 1
        assert msgs[0]["payload"]["a"] == 1

    def test_boundary_full_queue(self) -> None:
        mq = MessageQueue({"max_size": 2})
        mq.publish("topic1", {"a": 1})
        mq.publish("topic1", {"a": 2})
        mq.publish("topic1", {"a": 3})
        assert mq.get_queue_depth("topic1") == 2

    def test_invalid_format_none_topic(self) -> None:
        mq = MessageQueue({})
        with pytest.raises(ValidationError):
            mq.publish(None, {})


class TestFileSystemAdapter:
    """测试FileSystemAdapter"""

    def test_normal_write_read(self) -> None:
        fs = FileSystemAdapter({"base_path": "/tmp/test_agent_fs"})
        fs.write_json("test.json", {"a": 1})
        data = fs.read_json("test.json")
        assert data["a"] == 1
        fs.delete("test.json")

    def test_boundary_delete_nonexistent(self) -> None:
        fs = FileSystemAdapter({"base_path": "/tmp/test_agent_fs"})
        assert fs.delete("nonexistent.json") is False


class TestExternalIntegrationModule:
    """测试ExternalIntegrationModule"""

    def test_normal_init(self) -> None:
        mod = ExternalIntegrationModule({})
        assert mod.http is not None

    def test_publish_event(self) -> None:
        mod = ExternalIntegrationModule({})
        assert mod.publish_event("events", {"type": "test"}) is True

    def test_call_external_api(self) -> None:
        mod = ExternalIntegrationModule({})
        result = mod.call_external_api("/api/test")
        assert result["status"] == 200

    def test_persist_and_load(self) -> None:
        mod = ExternalIntegrationModule({"fs": {"base_path": "/tmp/test_agent_mod"}})
        mod.persist_state("state.json", {"v": 42})
        data = mod.load_state("state.json")
        assert data["v"] == 42

    def test_idempotency(self) -> None:
        mod = ExternalIntegrationModule({})
        assert mod.is_idempotent("op1") is True
        assert mod.is_idempotent("op1") is False

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            ExternalIntegrationModule(None)
