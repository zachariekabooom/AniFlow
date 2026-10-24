"""Interface de cache de réponses et implémentation en mémoire."""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Protocol


class ResponseCache(Protocol):
    def get(self, key: str) -> Any | None: ...

    def set(self, key: str, value: Any, ttl: float) -> None: ...


class MemoryCache:
    """Cache TTL borné, sûr entre threads. Les valeurs retournées ne doivent pas être modifiées."""

    def __init__(self, *, clock: Callable[[], float] = time.time, max_entries: int = 512) -> None:
        self._clock = clock
        self._max_entries = max_entries
        self._data: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at <= self._clock():
                del self._data[key]
                return None
            self._data.move_to_end(key)
            return value

    def set(self, key: str, value: Any, ttl: float) -> None:
        with self._lock:
            self._data[key] = (self._clock() + ttl, value)
            self._data.move_to_end(key)
            while len(self._data) > self._max_entries:
                self._data.popitem(last=False)
