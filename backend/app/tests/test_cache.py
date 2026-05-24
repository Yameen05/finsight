"""Tests for the TTL cache."""

from __future__ import annotations

import asyncio
import time

from app.services.cache import TTLCache


async def test_cache_returns_cached_value():
    cache = TTLCache[int](ttl_seconds=60)
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        return 42

    a = await cache.get_or_set("k", factory)
    b = await cache.get_or_set("k", factory)
    assert a == b == 42
    assert calls["n"] == 1


async def test_cache_expires():
    cache = TTLCache[int](ttl_seconds=0.05)

    async def factory():
        return time.time_ns()

    a = await cache.get_or_set("k", factory)
    await asyncio.sleep(0.1)
    b = await cache.get_or_set("k", factory)
    assert a != b


async def test_cache_coalesces_concurrent_misses():
    """Multiple awaiters for the same key should produce only one factory call."""
    cache = TTLCache[int](ttl_seconds=60)
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        await asyncio.sleep(0.05)
        return 7

    results = await asyncio.gather(
        *[cache.get_or_set("k", factory) for _ in range(10)]
    )
    assert all(r == 7 for r in results)
    assert calls["n"] == 1


async def test_cache_invalidate():
    cache = TTLCache[int](ttl_seconds=60)
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        return calls["n"]

    assert await cache.get_or_set("k", factory) == 1
    cache.invalidate("k")
    assert await cache.get_or_set("k", factory) == 2
