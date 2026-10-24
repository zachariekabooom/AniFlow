"""Limiteur de débit à fenêtre glissante, partagé entre threads."""

from __future__ import annotations

import collections
import threading
import time
from typing import Callable


class RateLimitWouldBlock(Exception):
    """L'attente nécessaire dépasse le maximum toléré par l'appelant."""

    def __init__(self, wait: float) -> None:
        super().__init__(f"attente requise : {wait:.1f} s")
        self.wait = wait


class SlidingWindowRateLimiter:
    def __init__(
        self,
        max_calls: int = 30,
        period: float = 60.0,
        min_interval: float = 0.5,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_calls < 1 or period <= 0 or min_interval < 0:
            raise ValueError("paramètres de limiteur invalides")
        self._max_calls = max_calls
        self._period = period
        self._min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._calls: collections.deque[float] = collections.deque()
        self._blocked_until = 0.0
        self._lock = threading.Lock()

    def penalize(self, seconds: float) -> None:
        """Bloque tous les appels pendant `seconds` (après un 429, par exemple)."""
        with self._lock:
            self._blocked_until = max(self._blocked_until, self._clock() + max(0.0, seconds))

    def required_wait(self) -> float:
        with self._lock:
            return self._required_wait_locked(self._clock())

    def _required_wait_locked(self, now: float) -> float:
        while self._calls and now - self._calls[0] >= self._period:
            self._calls.popleft()
        wait = max(0.0, self._blocked_until - now)
        if self._calls and self._min_interval:
            wait = max(wait, self._calls[-1] + self._min_interval - now)
        if len(self._calls) >= self._max_calls:
            wait = max(wait, self._calls[0] + self._period - now)
        return wait

    def acquire(self, max_wait: float | None = None) -> float:
        """Réserve un créneau. Retourne le temps attendu ; lève RateLimitWouldBlock si > max_wait."""
        waited = 0.0
        while True:
            with self._lock:
                now = self._clock()
                wait = self._required_wait_locked(now)
                if wait <= 0:
                    self._calls.append(now)
                    return waited
                if max_wait is not None and waited + wait > max_wait:
                    raise RateLimitWouldBlock(waited + wait)
            self._sleep(wait)
            waited += wait
