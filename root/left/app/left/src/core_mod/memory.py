"""记忆模块"""
import json
import sqlite3
import threading
import time
from typing import Any, Dict, Final, List

from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator

_STATES_SQL = """
    CREATE TABLE IF NOT EXISTS states (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loop_id INTEGER,
        timestamp REAL,
        state_json TEXT,
        drive_json TEXT,
        performance REAL
    )
"""

_ERRORS_SQL = """
    CREATE TABLE IF NOT EXISTS errors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loop_id INTEGER,
        timestamp REAL,
        error_type TEXT,
        error_message TEXT
    )
"""


class SQLiteStore:
    """SQLite持久化存储，线程安全连接池"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.db_path: str = str(config.get("db_path", "agent_memory.db"))
        self.max_records: int = int(config.get("max_records", 5000))
        self._local = threading.local()
        self._lock = threading.Lock()
        self._conn_lock = threading.Lock()
        self._connections: List[sqlite3.Connection] = []
        self._closed = False
        self._init_db()
        logger.info(f"SQLiteStore initialized db={self.db_path} max_records={self.max_records}", "memory")

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn = conn
            with self._conn_lock:
                if not self._closed:
                    self._connections.append(conn)
        return self._local.conn

    def close(self) -> None:
        """关闭所有 SQLite 连接，释放资源"""
        with self._conn_lock:
            self._closed = True
            connections = self._connections
            self._connections = []
        for conn in connections:
            try:
                conn.close()
            except Exception:
                pass
        local = getattr(self, "_local", None)
        if local is not None:
            local.conn = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def _init_db(self) -> None:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(_STATES_SQL)
            cursor.execute(_ERRORS_SQL)
            conn.commit()
            conn.close()

    def save_state(
        self, loop_id: int, state_json: str,
        drive_json: str, performance: float
    ) -> None:
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO states (loop_id, timestamp, state_json, drive_json, performance) VALUES (?, ?, ?, ?, ?)",
                (loop_id, time.time(), state_json, drive_json, performance)
            )
            self._trim_table(cursor, "states")
            conn.commit()
        logger.debug(f"State saved loop_id={loop_id}", "memory")

    def save_error(
        self, loop_id: int, error_type: str, error_message: str
    ) -> None:
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO errors (loop_id, timestamp, error_type, error_message) VALUES (?, ?, ?, ?)",
                (loop_id, time.time(), error_type, error_message)
            )
            self._trim_table(cursor, "errors")
            conn.commit()
        logger.debug(f"Error saved loop_id={loop_id} type={error_type}", "memory")

    def _trim_table(self, cursor: Any, table: str) -> None:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        if count > self.max_records:
            to_delete = count - self.max_records
            cursor.execute(f"DELETE FROM {table} WHERE id IN (SELECT id FROM {table} ORDER BY id ASC LIMIT ?)", (to_delete,))
            logger.info(f"Trimmed {to_delete} old records from {table}", "memory")

    def query_recent_states(self, limit: int) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            sql = "SELECT loop_id, timestamp, state_json, drive_json, performance FROM states ORDER BY id DESC LIMIT ?"
            cursor.execute(sql, (limit,))
            rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row: tuple) -> Dict[str, Any]:
        return {
            "loop_id": row[0],
            "timestamp": row[1],
            "state_json": row[2],
            "drive_json": row[3],
            "performance": row[4],
        }

    def query_error_count(self, error_type: str) -> int:
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            sql = "SELECT COUNT(*) FROM errors WHERE error_type = ?"
            cursor.execute(sql, (error_type,))
            count = cursor.fetchone()[0]
        return count


class StateCache:
    """状态缓存"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.max_size: int = int(config.get("max_cache_size", 1000))
        self.cache: List[Dict[str, Any]] = []

    def add(self, record: Dict[str, Any]) -> None:
        self.cache.append(record)
        if len(self.cache) > self.max_size:
            self.cache.pop(0)

    def get_recent(self, count: int) -> List[Dict[str, Any]]:
        return self.cache[-count:] if self.cache else []

    def get_all(self) -> List[Dict[str, Any]]:
        return self.cache.copy()


class MemoryModule:
    """记忆模块主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.cache = StateCache(config.get("cache", {}))
        self.store = SQLiteStore(config.get("store", {}))
        logger.info("MemoryModule initialized", "memory")

    def record_state(
        self, loop_id: int, state: Dict[str, Any],
        drive: Dict[str, Any], performance: float
    ) -> None:
        Validator.require_type(loop_id, int, "loop_id")
        Validator.require_type(state, dict, "state")
        Validator.require_type(drive, dict, "drive")
        Validator.require_type(performance, (int, float), "performance")
        record = self._build_record(loop_id, state, drive, performance)
        self.cache.add(record)
        self._persist_state(loop_id, state, drive, performance)
        logger.debug(f"State recorded loop_id={loop_id} perf={performance:.4f}", "memory")

    def _build_record(
        self, loop_id: int, state: Dict[str, Any],
        drive: Dict[str, Any], performance: float
    ) -> Dict[str, Any]:
        return {
            "loop_id": loop_id,
            "timestamp": time.time(),
            "state": state,
            "drive": drive,
            "performance": performance,
        }

    def _persist_state(
        self, loop_id: int, state: Dict[str, Any],
        drive: Dict[str, Any], performance: float
    ) -> None:
        state_json = json.dumps(self._convert(state))
        drive_json = json.dumps(self._convert(drive))
        self.store.save_state(loop_id, state_json, drive_json, performance)

    def _convert(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {self._convert_key(k): self._convert(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._convert(v) for v in obj]
        if hasattr(obj, "value"):
            return obj.value
        return obj

    def _convert_key(self, key: Any) -> str:
        if hasattr(key, "value"):
            return str(key.value)
        return str(key)

    def record_error(
        self, loop_id: int, error_type: str, error_message: str
    ) -> None:
        self.store.save_error(loop_id, error_type, error_message)
        logger.error(f"Error recorded loop_id={loop_id} type={error_type}", "memory")

    def get_recent_states(self, count: int) -> List[Dict[str, Any]]:
        return self.cache.get_recent(count)

    def get_performance_trend(self, window: int) -> float:
        recent = self.cache.get_recent(window)
        if len(recent) < 2:
            return 0.0
        performances = [r["performance"] for r in recent]
        trend = (performances[-1] - performances[0]) / len(performances)
        logger.debug(f"Performance trend={trend:.4f} window={window}", "memory")
        return trend

    def get_error_count(self, error_type: str) -> int:
        return self.store.query_error_count(error_type)

    def get_state(self) -> Dict[str, Any]:
        """获取记忆模块状态"""
        return {
            "cache_size": len(self.cache.cache),
            "cache_max_size": self.cache.max_size,
            "has_store": hasattr(self.store, "save_state"),
        }

    def reset(self) -> None:
        """重置记忆模块"""
        logger.debug("[MemoryModule.reset] called", "memory")
        self.cache = StateCache(self.config.get("cache", {}))
        self.store.close()
        self.store = SQLiteStore(self.config.get("store", {}))

    def close(self) -> None:
        """关闭记忆模块，释放底层存储资源"""
        store = getattr(self, "store", None)
        if store is not None and hasattr(store, "close"):
            store.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def health_check(self) -> bool:
        """健康检查"""
        logger.debug("[MemoryModule.health_check] called", "memory")
        return True
