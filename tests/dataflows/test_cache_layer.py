import importlib
import sqlite3
import time
from pathlib import Path


def load_cache_module():
    return importlib.import_module("tradingagents.dataflows.cache")


def test_response_cache_set_and_get(tmp_path):
    cache_module = load_cache_module()
    db_path = tmp_path / "cache.db"
    cache = cache_module.ResponseCache(str(db_path))

    key = cache_module.ResponseCache.make_key("method", ("AAPL",), {"date": "2024-01-01"})
    cache.set("method", key, "payload", vendor="alpha_vantage")

    assert cache.get("method", key, ttl_seconds=60) == "payload"


def test_response_cache_respects_ttl(tmp_path):
    cache_module = load_cache_module()
    db_path = tmp_path / "cache.db"
    cache = cache_module.ResponseCache(str(db_path))

    key = cache_module.ResponseCache.make_key("method", tuple(), {})
    cache.set("method", key, "payload")

    # Simulate expiry by manually updating timestamp
    conn = sqlite3.connect(str(db_path))
    conn.execute("UPDATE cache SET created_at=?", (time.time() - 10,))
    conn.commit()
    conn.close()

    assert cache.get("method", key, ttl_seconds=5) is None
    assert cache.get("method", key, ttl_seconds=0) == "payload"
