"""Document 75 (SPEC-DATA-007) versioned cache -- READ-FR-002..007/024..027.

Phase 1 has no live Redis (same "mechanism present, infra feed deferred" shape as Document 66's
zero-trust functions / Document 70's replica routing): this is a genuine, testable in-process
versioned cache with TTL, per-key single-flight (stampede protection, READ-FR-006) and explicit
invalidation. It is process-local and disposable by construction -- exactly what READ-FR-001/003
require ("non-authoritative projection... no regulated state exists only in" the cache) -- and every
entry is scoped by `(cache_class, scope_key, entity_id, version)` so a stale/superseded version is a
cache *miss*, never a stale hit (READ-FR-004/005/025).

Swapping this module's body for a real Redis client changes no caller: the public functions
(`get_versioned_cache_entry`, `invalidate_entity_cache`) keep their signatures.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Awaitable, Callable

_DEFAULT_TTL_SECONDS = 300.0  # READ-FR-005: every cache class has a TTL; no infinite cache.


@dataclass
class _Entry:
    value: object
    expires_at: float


class VersionedCache:
    """One process-local cache instance. `app/modules/readmodels/cache.py`'s module-level `_cache`
    singleton is what request handlers use; tests may construct their own instance for isolation."""

    def __init__(self) -> None:
        self._store: dict[str, _Entry] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    @staticmethod
    def _key(cache_class: str, scope_key: str, entity_id: str, version: int) -> str:
        # READ-FR-004: tenant/site/user/entity/version in the key -- scope_key carries whatever
        # tenant/site/user scoping the caller needs; version makes a superseded entry unreachable
        # (a new version is simply a different key, not an overwrite -- no stale-hit risk).
        return f"{cache_class}:{scope_key}:{entity_id}:{version}"

    def _lock_for(self, key: str) -> asyncio.Lock:
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    async def get_versioned_cache_entry(
        self,
        *,
        cache_class: str,
        scope_key: str,
        entity_id: str | uuid.UUID,
        version: int,
        loader: Callable[[], Awaitable[object]] | None = None,
        ttl_seconds: float = _DEFAULT_TTL_SECONDS,
    ) -> object | None:
        """Returns the cached value, or `None` on a miss with no `loader`. With a `loader`, a miss
        triggers exactly one concurrent load per key (single-flight, READ-FR-006) and populates the
        cache; concurrent callers for the same key await the same in-flight load rather than each
        re-running the expensive query (cache-stampede protection)."""
        key = self._key(cache_class, scope_key, str(entity_id), version)
        now = time.monotonic()
        entry = self._store.get(key)
        if entry is not None and entry.expires_at > now:
            return entry.value
        if loader is None:
            return None
        async with self._lock_for(key):
            entry = self._store.get(key)
            if entry is not None and entry.expires_at > time.monotonic():
                return entry.value  # someone else populated it while we waited for the lock
            value = await loader()
            self._store[key] = _Entry(value=value, expires_at=time.monotonic() + ttl_seconds)
            return value

    def invalidate_entity_cache(self, *, cache_class: str, scope_key: str, entity_id: str | uuid.UUID) -> int:
        """READ-FR-007: removes every version of this entity's entries under `cache_class`/`scope_key`
        (a version bump makes the old key unreachable anyway; this also drops it eagerly). Returns the
        count removed."""
        prefix = f"{cache_class}:{scope_key}:{entity_id}:"
        to_drop = [k for k in self._store if k.startswith(prefix)]
        for k in to_drop:
            del self._store[k]
        return len(to_drop)

    def purge_expired(self) -> int:
        now = time.monotonic()
        expired = [k for k, e in self._store.items() if e.expires_at <= now]
        for k in expired:
            del self._store[k]
        return len(expired)

    def size(self) -> int:
        return len(self._store)


_cache = VersionedCache()


async def get_versioned_cache_entry(**kwargs) -> object | None:
    return await _cache.get_versioned_cache_entry(**kwargs)


async def invalidate_entity_cache(*, cache_class: str, scope_key: str, entity_id: str | uuid.UUID) -> int:
    """Sync cache mutation + best-effort `CacheInvalidated` signal (own committed transaction, never
    blocks or fails the invalidation itself -- same pattern as every other module's signals.py)."""
    from app.modules.readmodels.signals import emit_cache_invalidated  # local import: avoid cycle

    count = _cache.invalidate_entity_cache(cache_class=cache_class, scope_key=scope_key, entity_id=entity_id)
    if count:
        await emit_cache_invalidated({
            "cache_class": cache_class, "scope_key": scope_key, "entity_id": str(entity_id),
            "entries_removed": count,
        })
    return count
