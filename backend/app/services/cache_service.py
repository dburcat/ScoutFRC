"""
cache_service.py
================
Phase 2 Tier 4 — Data Caching System

Provides a typed Redis wrapper (CacheService) used by:
  - Hot-read API endpoints (cache-aside pattern)
  - Celery Beat refresh task
  - Write-path invalidation hooks
  - Startup warm-up task

TTL Policies (configurable via env)
------------------------------------
  CACHE_TTL_RANKINGS   = 600   s  (10 min)
  CACHE_TTL_TEAM       = 1800  s  (30 min)
  CACHE_TTL_EVENT      = 600   s  (10 min)
  CACHE_TTL_STATS      = 300   s  (5 min)
  CACHE_TTL_ALLIANCE   = 600   s  (10 min)

Key Namespacing
---------------
  rankings:{event_id}
  team:{team_id}
  event:{event_id}
  event_summary:{event_id}
  alliance:{alliance_id}
  dashboard:stats        (global aggregate)
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import redis

logger = logging.getLogger(__name__)

# ── Redis connection (DB 2 — separate from broker/result) ─────────────────────
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_REDIS_DB: int = int(os.getenv("CACHE_REDIS_DB", "2"))

# ── TTL policies (seconds) ────────────────────────────────────────────────────
TTL_RANKINGS: int = int(os.getenv("CACHE_TTL_RANKINGS", "600"))
TTL_TEAM: int = int(os.getenv("CACHE_TTL_TEAM", "1800"))
TTL_EVENT: int = int(os.getenv("CACHE_TTL_EVENT", "600"))
TTL_STATS: int = int(os.getenv("CACHE_TTL_STATS", "300"))
TTL_ALLIANCE: int = int(os.getenv("CACHE_TTL_ALLIANCE", "600"))

# ── Internal metrics key ──────────────────────────────────────────────────────
_METRICS_KEY = "cache:metrics"


def _build_redis_client() -> redis.Redis:
    """Parse REDIS_URL and override DB to CACHE_REDIS_DB."""
    client = redis.from_url(
        REDIS_URL,
        db=CACHE_REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    return client


class CacheService:
    """
    Typed cache service backed by Redis.

    Usage
    -----
    cache = CacheService()

    # Store
    cache.set("rankings:42", data, ttl=TTL_RANKINGS)

    # Retrieve (returns None on miss)
    data = cache.get("rankings:42")

    # Invalidate
    cache.invalidate("rankings:42")

    # Invalidate by prefix
    cache.invalidate_prefix("rankings:")
    """

    def __init__(self, client: redis.Redis | None = None) -> None:
        self._client: redis.Redis = client or _build_redis_client()

    # ── Core helpers ──────────────────────────────────────────────────────────

    def _ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except Exception:
            return False

    def get(self, key: str) -> Any | None:
        """Return deserialized value or None on miss/error."""
        try:
            raw = self._client.get(key)
            if raw is None:
                self._record_miss()
                return None
            self._record_hit()
            return json.loads(raw)  # type: ignore[arg-type]
        except Exception as exc:
            logger.warning("Cache GET error for key %r: %s", key, exc)
            return None

    def set(self, key: str, value: Any, ttl: int = TTL_STATS) -> bool:
        """Serialize and store value. Returns True on success."""
        try:
            serialized = json.dumps(value, default=str)
            self._client.setex(key, ttl, serialized)
            return True
        except Exception as exc:
            logger.warning("Cache SET error for key %r: %s", key, exc)
            return False

    def invalidate(self, key: str) -> bool:
        """Delete a single key. Returns True if key existed."""
        try:
            return bool(self._client.delete(key))
        except Exception as exc:
            logger.warning("Cache DELETE error for key %r: %s", key, exc)
            return False

    def invalidate_prefix(self, prefix: str) -> int:
        """
        Delete all keys matching prefix*.
        Uses SCAN to avoid blocking Redis on large key spaces.
        Returns count of deleted keys.
        """
        deleted = 0
        try:
            cursor = 0
            while True:
                cursor, keys = self._client.scan(cursor, match=f"{prefix}*", count=100)  # type: ignore[misc]
                if keys:
                    deleted += self._client.delete(*keys)  # type: ignore[assignment,arg-type]
                if cursor == 0:
                    break
        except Exception as exc:
            logger.warning("Cache invalidate_prefix error for %r: %s", prefix, exc)
        return deleted

    def ttl(self, key: str) -> int:
        """Return remaining TTL in seconds, or -2 if key doesn't exist."""
        try:
            return self._client.ttl(key)  # type: ignore[return-value]
        except Exception:
            return -2

    def exists(self, key: str) -> bool:
        try:
            return bool(self._client.exists(key))
        except Exception:
            return False

    # ── Hit-rate metrics ──────────────────────────────────────────────────────

    def _record_hit(self) -> None:
        try:
            self._client.hincrby(_METRICS_KEY, "hits", 1)
        except Exception:
            pass

    def _record_miss(self) -> None:
        try:
            self._client.hincrby(_METRICS_KEY, "misses", 1)
        except Exception:
            pass

    def get_metrics(self) -> dict:
        """Return hit/miss counts and derived hit-rate."""
        try:
            raw: dict = self._client.hgetall(_METRICS_KEY)  # type: ignore[assignment]
            hits = int(raw.get("hits", 0))
            misses = int(raw.get("misses", 0))
            total = hits + misses
            return {
                "hits": hits,
                "misses": misses,
                "total_requests": total,
                "hit_rate": round(hits / total, 4) if total else 0.0,
            }
        except Exception as exc:
            logger.warning("Cache metrics error: %s", exc)
            return {"hits": 0, "misses": 0, "total_requests": 0, "hit_rate": 0.0}

    def reset_metrics(self) -> None:
        try:
            self._client.delete(_METRICS_KEY)
        except Exception:
            pass

    # ── Introspection ─────────────────────────────────────────────────────────

    def key_count(self) -> int:
        """Approximate number of keys in the cache DB."""
        try:
            ks_info: dict = self._client.info("keyspace")  # type: ignore[assignment]
            db_key = f"db{CACHE_REDIS_DB}"
            if db_key in ks_info:
                return ks_info[db_key].get("keys", 0)
            return 0
        except Exception:
            return 0

    def memory_used_bytes(self) -> int:
        """Used memory reported by Redis (whole instance, bytes)."""
        try:
            mem_info: dict = self._client.info("memory")  # type: ignore[assignment]
            return mem_info.get("used_memory", 0)
        except Exception:
            return 0

    def is_healthy(self) -> bool:
        return self._ping()

    # ── Named-key builders ────────────────────────────────────────────────────

    @staticmethod
    def rankings_key(event_id: int) -> str:
        return f"rankings:{event_id}"

    @staticmethod
    def team_key(team_id: int) -> str:
        return f"team:{team_id}"

    @staticmethod
    def event_key(event_id: int) -> str:
        return f"event:{event_id}"

    @staticmethod
    def event_summary_key(event_id: int) -> str:
        return f"event_summary:{event_id}"

    @staticmethod
    def alliance_key(alliance_id: int) -> str:
        return f"alliance:{alliance_id}"

    @staticmethod
    def dashboard_stats_key() -> str:
        return "dashboard:stats"


# ── Module-level singleton ────────────────────────────────────────────────────
# Routers and tasks import this directly.
cache = CacheService()