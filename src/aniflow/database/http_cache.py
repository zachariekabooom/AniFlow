"""Cache de réponses HTTP persistant (SQLite), compatible avec l'interface ResponseCache."""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Any, Callable


class SqliteResponseCache:
    def __init__(self, conn: sqlite3.Connection, *, clock: Callable[[], float] = time.time) -> None:
        self._conn = conn
        self._clock = clock

    def get(self, key: str) -> Any | None:
        row = self._conn.execute("SELECT value, expires_at FROM http_cache WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        if row["expires_at"] <= self._clock():
            self._conn.execute("DELETE FROM http_cache WHERE key = ?", (key,))
            return None
        return json.loads(row["value"])

    def set(self, key: str, value: Any, ttl: float) -> None:
        self._conn.execute(
            "INSERT INTO http_cache(key, value, expires_at) VALUES(?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, expires_at = excluded.expires_at",
            (key, json.dumps(value, ensure_ascii=False, separators=(",", ":")), self._clock() + ttl),
        )

    def purge_expired(self) -> int:
        return self._conn.execute("DELETE FROM http_cache WHERE expires_at <= ?", (self._clock(),)).rowcount
