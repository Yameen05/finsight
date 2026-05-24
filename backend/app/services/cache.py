"""Tiny async-safe TTL cache.

Used to dampen repeat calls to yfinance, NewsAPI, and SEC during burst traffic
without pulling in Redis. Keys are arbitrary hashables; values are anything.

  - Per-key expiration
  - Concurrent fetches for the same key coalesce on a single `asyncio.Lock` so
    we don't issue N parallel upstream calls for a hot key (thundering herd).
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: float):
        self.ttl = ttl_seconds
        self._data: dict[Any, tuple[float, T]] = {}
        self._locks: dict[Any, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    def _get_fresh(self, key: Any) -> T | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.time():
            self._data.pop(key, None)
            return None
        return value

    async def get_or_set(self, key: Any, factory: Callable[[], Awaitable[T]]) -> T:
        # Fast path: cached + fresh.
        hit = self._get_fresh(key)
        if hit is not None:
            return hit

        # Slow path: acquire per-key lock to coalesce concurrent misses.
        async with self._global_lock:
            lock = self._locks.setdefault(key, asyncio.Lock())

        async with lock:
            hit = self._get_fresh(key)
            if hit is not None:
                return hit
            value = await factory()
            self._data[key] = (time.time() + self.ttl, value)
            return value

    def invalidate(self, key: Any) -> None:
        self._data.pop(key, None)

    def clear(self) -> None:
        self._data.clear()
        self._locks.clear()
