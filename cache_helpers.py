"""ctx.cache wrapper for SE Ranking's panel reads.

The sidebar (project list) and workspace (rankings + opportunities) panels
call the shared se-ranking-control backend live on every single render/
pagination click. Rank tracking data only refreshes once a day server-side
(SE Ranking itself re-crawls positions daily), so caching it for a few
minutes here costs zero real freshness while making repeat panel opens
near-instant instead of 1-2 sequential live HTTP round-trips to the backend.

ctx.cache TTL is platform-capped to [5, 300]s (I-CACHE-TTL-CAP-300S).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, Field


class CachedSerPayload(BaseModel):
    """Generic ctx.cache envelope — one JSON-serialisable payload per call."""
    data: Any = Field(default_factory=dict)


PROJECTS_CACHE_TTL = 120       # project list rarely changes
RANKINGS_CACHE_TTL = 240       # positions re-crawl ~daily server-side
OPPORTUNITIES_CACHE_TTL = 240  # derived from the same daily-refreshed data


def _cache_key(scope: str, api_key: str, extra: dict | None = None) -> str:
    # Hash the api_key itself rather than storing it in the clear key — it's
    # a live credential, keep it out of any cache-key logs/telemetry.
    parts = {"scope": scope, "key": hashlib.sha256(api_key.encode()).hexdigest()[:16], "extra": extra or {}}
    digest = hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:32]
    return f"ser:{digest}"


async def cached_call(ctx, scope: str, api_key: str, extra: dict | None,
                       ttl_seconds: int, fetcher: Callable[[], Awaitable[Any]]) -> Any:
    """Cache one JSON-serialisable payload behind ctx.cache.get_or_fetch().

    Falls back to calling the fetcher directly if ctx.cache is unavailable
    (e.g. a minimal test/mock Context) so callers never have to special-case it.
    """
    key = _cache_key(scope, api_key or "none", extra)

    async def _fetch() -> CachedSerPayload:
        return CachedSerPayload(data=await fetcher())

    try:
        cache = ctx.cache
    except Exception:
        return await fetcher()

    payload = await cache.get_or_fetch(key, CachedSerPayload, _fetch, ttl_seconds=ttl_seconds)
    return payload.data
