import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .config import get_config


class ResponseCache:
    def __init__(self, db_path: str):
        self.db_path = str(Path(db_path).expanduser())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    method TEXT NOT NULL,
                    cache_key TEXT NOT NULL,
                    vendor TEXT,
                    response TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (method, cache_key)
                )
                """
            )
        self._lock = threading.RLock()

    @staticmethod
    def make_key(method: str, args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> str:
        serialized = json.dumps(
            {"args": args, "kwargs": kwargs},
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get(self, method: str, cache_key: str, ttl_seconds: int) -> Optional[str]:
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT response, created_at FROM cache WHERE method=? AND cache_key=?",
                (method, cache_key),
            ).fetchone()
            if not row:
                return None
            if ttl_seconds > 0:
                age = time.time() - row["created_at"]
                if age > ttl_seconds:
                    return None
            return row["response"]

    def get_stale(self, method: str, cache_key: str) -> Optional[str]:
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT response FROM cache WHERE method=? AND cache_key=?",
                (method, cache_key),
            ).fetchone()
            return row["response"] if row else None

    def set(self, method: str, cache_key: str, response: str, vendor: Optional[str] = None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO cache(method, cache_key, vendor, response, created_at)
                VALUES(?,?,?,?,?)
                ON CONFLICT(method, cache_key)
                DO UPDATE SET vendor=excluded.vendor, response=excluded.response, created_at=excluded.created_at
                """,
                (method, cache_key, vendor, response, time.time()),
            )

    def clear(self) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM cache")


_cache_instance: Optional[ResponseCache] = None
_cache_lock = threading.Lock()


def get_cache() -> Optional[ResponseCache]:
    global _cache_instance
    config = get_config()
    db_path = config.get("cache_db_path")
    if not db_path:
        return None
    with _cache_lock:
        if _cache_instance and _cache_instance.db_path == str(Path(db_path).expanduser()):
            return _cache_instance
        _cache_instance = ResponseCache(db_path)
    return _cache_instance


def reset_cache_for_tests() -> None:
    global _cache_instance
    with _cache_lock:
        _cache_instance = None
