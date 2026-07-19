"""cache_helpers.cached_call — unit tests, no network."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest

from cache_helpers import cached_call


class _FakeCacheClient:
    def __init__(self):
        self.store: dict[str, object] = {}
        self.fetch_calls = 0

    async def get_or_fetch(self, key, model, fetcher, ttl_seconds=60):
        if key in self.store:
            return self.store[key]
        self.fetch_calls += 1
        value = await fetcher()
        self.store[key] = value
        return value


def _ctx_with_cache():
    ctx = SimpleNamespace()
    ctx.cache = _FakeCacheClient()
    return ctx


class _NoCacheContext:
    @property
    def cache(self):
        raise RuntimeError("no cache available")


@pytest.mark.asyncio
async def test_cached_call_fetches_once_then_serves_from_cache():
    ctx = _ctx_with_cache()
    calls = []

    async def fetcher():
        calls.append(1)
        return {"data": [{"id": 1, "title": "Site A"}]}

    first = await cached_call(ctx, "projects", "key-abc", None, 60, fetcher)
    second = await cached_call(ctx, "projects", "key-abc", None, 60, fetcher)

    assert first == {"data": [{"id": 1, "title": "Site A"}]}
    assert second == first
    assert len(calls) == 1
    assert ctx.cache.fetch_calls == 1


@pytest.mark.asyncio
async def test_cached_call_keys_differ_per_api_key_and_extra():
    ctx = _ctx_with_cache()

    async def fetcher_a():
        return {"keywords": ["a"]}

    async def fetcher_b():
        return {"keywords": ["b"]}

    r1 = await cached_call(ctx, "rankings", "key-1", {"project_id": "123"}, 60, fetcher_a)
    r2 = await cached_call(ctx, "rankings", "key-2", {"project_id": "123"}, 60, fetcher_b)
    r3 = await cached_call(ctx, "rankings", "key-1", {"project_id": "456"}, 60, fetcher_b)

    assert r1 == {"keywords": ["a"]}
    assert r2 == {"keywords": ["b"]}
    assert r3 == {"keywords": ["b"]}
    assert ctx.cache.fetch_calls == 3


@pytest.mark.asyncio
async def test_cached_call_falls_back_when_cache_unavailable():
    ctx = _NoCacheContext()
    calls = []

    async def fetcher():
        calls.append(1)
        return {"opportunities": []}

    result = await cached_call(ctx, "opportunities", "key-x", {"project_id": "1"}, 60, fetcher)

    assert result == {"opportunities": []}
    assert len(calls) == 1
