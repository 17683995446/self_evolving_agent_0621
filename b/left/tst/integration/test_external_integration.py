"""外部系统集成测试"""
import threading
import time

import pytest

from root.left.app.left.src.core_mod.external import ExternalIntegrationModule


class TestHttpResilience:
    """HTTP弹性测试"""

    def test_retry_mechanism(self) -> None:
        mod = ExternalIntegrationModule({"http": {"max_retries": 3, "retry_delay": 0.01}})
        result = mod.call_external_api("/test")
        assert result["status"] == 200

    def test_circuit_breaker_opens(self) -> None:
        mod = ExternalIntegrationModule({"http": {"failure_threshold": 1, "max_retries": 1, "retry_delay": 0.01}})
        mod.http.circuit_open = True
        mod.http._circuit_opened_at = time.time()
        with pytest.raises(Exception):
            mod.call_external_api("/test")


class TestMqIntegration:
    """MQ集成测试"""

    def test_pub_sub_flow(self) -> None:
        mod = ExternalIntegrationModule({})
        mod.publish_event("orders", {"id": 1})
        mod.publish_event("orders", {"id": 2})
        msgs = mod.consume_events("orders", 10)
        assert len(msgs) == 2
        assert msgs[0]["payload"]["id"] == 1

    def test_multiple_topics_isolated(self) -> None:
        mod = ExternalIntegrationModule({})
        mod.publish_event("topic_a", {"v": 1})
        mod.publish_event("topic_b", {"v": 2})
        assert len(mod.consume_events("topic_a")) == 1
        assert len(mod.consume_events("topic_b")) == 1


class TestFsIntegration:
    """文件系统集成测试"""

    def test_state_persistence_roundtrip(self) -> None:
        mod = ExternalIntegrationModule({"fs": {"base_path": "/tmp/test_agent_integ"}})
        state = {"loop": 100, "performance": 0.95}
        mod.persist_state("checkpoint.json", state)
        loaded = mod.load_state("checkpoint.json")
        assert loaded == state


class TestIdempotencyIntegration:
    """幂等性集成测试"""

    def test_duplicate_api_call_prevented(self) -> None:
        mod = ExternalIntegrationModule({})
        key = "payment_123"
        assert mod.is_idempotent(key) is True
        assert mod.is_idempotent(key) is False

    def test_concurrent_idempotency(self) -> None:
        mod = ExternalIntegrationModule({})
        results = []

        def check() -> None:
            results.append(mod.is_idempotent("concurrent_key"))

        threads = [threading.Thread(target=check) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert results.count(True) == 1
        assert results.count(False) == 9
