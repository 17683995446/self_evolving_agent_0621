"""记忆模块单元测试"""
import pytest
import os
from root.left.app.left.src.core_mod.memory import StateCache, SQLiteStore, MemoryModule
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestStateCache:
    """测试StateCache"""

    def test_normal_add(self) -> None:
        cache = StateCache({"max_cache_size": 10})
        cache.add({"loop_id": 1})
        assert len(cache.cache) == 1

    def test_empty_get(self) -> None:
        cache = StateCache({})
        assert cache.get_recent(5) == []

    def test_boundary_overflow(self) -> None:
        cache = StateCache({"max_cache_size": 2})
        cache.add({"loop_id": 1})
        cache.add({"loop_id": 2})
        cache.add({"loop_id": 3})
        assert len(cache.cache) == 2

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            StateCache(None)

    def test_get_all(self) -> None:
        cache = StateCache({})
        cache.add({"loop_id": 1})
        assert len(cache.get_all()) == 1


class TestSQLiteStore:
    """测试SQLiteStore"""

    def test_normal_init(self) -> None:
        db_path = "/tmp/test_memory_1.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        store = SQLiteStore({"db_path": db_path})
        try:
            assert os.path.exists(db_path)
        finally:
            store.close()
            os.remove(db_path)

    def test_empty_config(self) -> None:
        db_path = "agent_memory_test.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        store = SQLiteStore({"db_path": db_path})
        try:
            assert store.db_path == db_path
        finally:
            store.close()
            os.remove(db_path)

    def test_boundary_save_and_query(self) -> None:
        db_path = "/tmp/test_memory_2.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        store = SQLiteStore({"db_path": db_path})
        try:
            store.save_state(1, "{}", "{}", 0.5)
            result = store.query_recent_states(1)
            assert len(result) == 1
        finally:
            store.close()
            os.remove(db_path)

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            SQLiteStore(None)

    def test_save_error(self) -> None:
        db_path = "/tmp/test_memory_3.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        store = SQLiteStore({"db_path": db_path})
        try:
            store.save_error(1, "test", "msg")
            assert store.query_error_count("test") == 1
        finally:
            store.close()
            os.remove(db_path)

    def test_close_closes_all_connections(self) -> None:
        import threading
        db_path = "/tmp/test_memory_close.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        store = SQLiteStore({"db_path": db_path})
        try:
            store.save_state(1, "{}", "{}", 0.5)

            def worker() -> None:
                store.save_state(2, "{}", "{}", 0.6)

            t = threading.Thread(target=worker)
            t.start()
            t.join()
            assert len(store._connections) == 2
            store.close()
            assert all(conn.closed for conn in store._connections)
        finally:
            store.close()
            os.remove(db_path)

    def test_close_is_idempotent(self) -> None:
        db_path = "/tmp/test_memory_idempotent.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        store = SQLiteStore({"db_path": db_path})
        try:
            store.save_state(1, "{}", "{}", 0.5)
            store.close()
            store.close()
        finally:
            store.close()
            os.remove(db_path)


class TestMemoryModule:
    """测试MemoryModule"""

    def test_normal_record(self) -> None:
        db_path = "/tmp/test_memory_4.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        mod = MemoryModule({"store": {"db_path": db_path}})
        try:
            mod.record_state(1, {}, {}, 0.5)
            assert len(mod.get_recent_states(1)) == 1
        finally:
            mod.close()
            os.remove(db_path)

    def test_empty_state(self) -> None:
        db_path = "/tmp/test_memory_5.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        mod = MemoryModule({"store": {"db_path": db_path}})
        try:
            mod.record_state(1, {}, {}, 0.0)
            assert len(mod.get_recent_states(1)) == 1
        finally:
            mod.close()
            os.remove(db_path)

    def test_boundary_trend(self) -> None:
        db_path = "/tmp/test_memory_6.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        mod = MemoryModule({"store": {"db_path": db_path}})
        try:
            mod.record_state(1, {}, {}, 0.1)
            mod.record_state(2, {}, {}, 0.2)
            trend = mod.get_performance_trend(2)
            assert trend > 0.0
        finally:
            mod.close()
            os.remove(db_path)

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            MemoryModule(None)

    def test_error_count(self) -> None:
        db_path = "/tmp/test_memory_7.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        mod = MemoryModule({"store": {"db_path": db_path}})
        try:
            mod.record_error(1, "test", "msg")
            assert mod.get_error_count("test") == 1
        finally:
            mod.close()
            os.remove(db_path)

    def test_close_closes_store(self) -> None:
        db_path = "/tmp/test_memory_mod_close.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        mod = MemoryModule({"store": {"db_path": db_path}})
        try:
            mod.record_state(1, {}, {}, 0.5)
            mod.close()
            assert len(mod.store._connections) == 0
        finally:
            mod.close()
            os.remove(db_path)

    def test_close_is_idempotent(self) -> None:
        db_path = "/tmp/test_memory_mod_idempotent.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        mod = MemoryModule({"store": {"db_path": db_path}})
        try:
            mod.close()
            mod.close()
        finally:
            mod.close()
            os.remove(db_path)
