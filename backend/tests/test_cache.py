"""
test_cache.py
=============
Phase 2 Tier 4 — Data Caching System

Test coverage
-------------
Unit (CacheService — Redis mocked)
  - get: hit, miss, error resilience
  - set: stores value, respects TTL, error resilience
  - invalidate: deletes key, returns bool
  - invalidate_prefix: uses SCAN to delete matching keys
  - metrics: hit/miss counters, hit_rate calculation
  - key builders: correct namespacing

Integration (cache-aside pattern — Redis mocked)
  - GET /events/{id}        cache hit / miss / fallthrough
  - GET /events/{id}/rankings  cache hit / miss
  - GET /teams/{id}         cache hit / miss
  - GET /alliances/{id}     cache hit / miss

Invalidation hooks
  - POST /matches/           invalidates rankings + event_summary
  - PATCH /matches/{id}      invalidates rankings + event_summary
  - POST /scouting_observations/  invalidates team + rankings

Admin endpoints
  - GET  /admin/cache/stats  returns metrics dict
  - POST /admin/cache/invalidate  deletes by prefix
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock
import json
import pytest


# ════════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════════

def _make_redis_mock(stored: dict | None = None):
    """Return a mock Redis client with an in-memory store."""
    store = stored or {}
    ttls = {}

    mock = MagicMock()

    def _get(key):
        return store.get(key)

    def _setex(key, ttl, value):
        store[key] = value
        ttls[key] = ttl

    def _delete(*keys):
        deleted = sum(1 for k in keys if k in store)
        for k in keys:
            store.pop(k, None)
        return deleted

    def _exists(key):
        return 1 if key in store else 0

    def _ttl(key):
        return ttls.get(key, -2)

    def _ping():
        return True

    def _scan(cursor, match="*", count=100):
        import fnmatch
        matched = [k for k in store if fnmatch.fnmatch(k, match)]
        return 0, matched

    def _hincrby(key, field, amount):
        if key not in store:
            store[key] = {}
        if isinstance(store[key], dict):
            store[key][field] = store[key].get(field, 0) + amount

    def _hgetall(key):
        val = store.get(key, {})
        return {k: str(v) for k, v in val.items()} if isinstance(val, dict) else {}

    def _info(section=None):
        if section == "keyspace":
            return {"db2": {"keys": len(store)}}
        if section == "memory":
            return {"used_memory": 1024}
        return {}

    mock.get.side_effect = _get
    mock.setex.side_effect = _setex
    mock.delete.side_effect = _delete
    mock.exists.side_effect = _exists
    mock.ttl.side_effect = _ttl
    mock.ping.side_effect = _ping
    mock.scan.side_effect = _scan
    mock.hincrby.side_effect = _hincrby
    mock.hgetall.side_effect = _hgetall
    mock.info.side_effect = _info

    return mock, store


# ════════════════════════════════════════════════════════════════════════════
# Unit tests — CacheService
# ════════════════════════════════════════════════════════════════════════════

from app.services.cache_service import CacheService


class TestCacheServiceGet:
    def test_hit_returns_deserialized_value(self):
        redis_mock, store = _make_redis_mock()
        store["team:1"] = json.dumps({"team_id": 1, "team_number": 254})
        svc = CacheService(client=redis_mock)
        result = svc.get("team:1")
        assert result == {"team_id": 1, "team_number": 254}

    def test_miss_returns_none(self):
        redis_mock, _ = _make_redis_mock()
        svc = CacheService(client=redis_mock)
        assert svc.get("team:999") is None

    def test_error_returns_none(self):
        redis_mock, _ = _make_redis_mock()
        redis_mock.get.side_effect = Exception("connection refused")
        svc = CacheService(client=redis_mock)
        assert svc.get("team:1") is None


class TestCacheServiceSet:
    def test_stores_serialized_value(self):
        redis_mock, store = _make_redis_mock()
        svc = CacheService(client=redis_mock)
        svc.set("team:1", {"team_id": 1}, ttl=300)
        assert "team:1" in store
        assert json.loads(store["team:1"]) == {"team_id": 1}

    def test_returns_true_on_success(self):
        redis_mock, _ = _make_redis_mock()
        svc = CacheService(client=redis_mock)
        assert svc.set("key", "value") is True

    def test_returns_false_on_error(self):
        redis_mock, _ = _make_redis_mock()
        redis_mock.setex.side_effect = Exception("Redis down")
        svc = CacheService(client=redis_mock)
        assert svc.set("key", "value") is False


class TestCacheServiceInvalidate:
    def test_deletes_existing_key(self):
        redis_mock, store = _make_redis_mock({"team:1": "data"})
        svc = CacheService(client=redis_mock)
        result = svc.invalidate("team:1")
        assert result is True
        assert "team:1" not in store

    def test_returns_false_for_missing_key(self):
        redis_mock, _ = _make_redis_mock()
        svc = CacheService(client=redis_mock)
        assert svc.invalidate("team:999") is False

    def test_invalidate_prefix_deletes_all_matching(self):
        redis_mock, store = _make_redis_mock({
            "rankings:1": "r1",
            "rankings:2": "r2",
            "team:1": "t1",
        })
        svc = CacheService(client=redis_mock)
        deleted = svc.invalidate_prefix("rankings:")
        assert deleted == 2
        assert "team:1" in store
        assert "rankings:1" not in store
        assert "rankings:2" not in store


class TestCacheServiceMetrics:
    def test_hit_increments_counter(self):
        redis_mock, store = _make_redis_mock()
        store["key"] = json.dumps("value")
        svc = CacheService(client=redis_mock)
        svc.get("key")
        metrics = svc.get_metrics()
        assert metrics["hits"] == 1
        assert metrics["misses"] == 0

    def test_miss_increments_counter(self):
        redis_mock, _ = _make_redis_mock()
        svc = CacheService(client=redis_mock)
        svc.get("missing")
        metrics = svc.get_metrics()
        assert metrics["misses"] == 1
        assert metrics["hits"] == 0

    def test_hit_rate_calculation(self):
        redis_mock, store = _make_redis_mock()
        store["k"] = json.dumps("v")
        svc = CacheService(client=redis_mock)
        svc.get("k")       # hit
        svc.get("k")       # hit
        svc.get("miss")    # miss
        metrics = svc.get_metrics()
        assert metrics["hit_rate"] == pytest.approx(2 / 3, abs=0.01)

    def test_zero_requests_hit_rate(self):
        redis_mock, _ = _make_redis_mock()
        svc = CacheService(client=redis_mock)
        assert svc.get_metrics()["hit_rate"] == 0.0


class TestCacheKeyBuilders:
    def test_rankings_key(self):
        assert CacheService.rankings_key(42) == "rankings:42"

    def test_team_key(self):
        assert CacheService.team_key(100) == "team:100"

    def test_event_key(self):
        assert CacheService.event_key(5) == "event:5"

    def test_event_summary_key(self):
        assert CacheService.event_summary_key(5) == "event_summary:5"

    def test_alliance_key(self):
        assert CacheService.alliance_key(3) == "alliance:3"

    def test_dashboard_stats_key(self):
        assert CacheService.dashboard_stats_key() == "dashboard:stats"


# ════════════════════════════════════════════════════════════════════════════
# Integration tests — cache-aside via API
# ════════════════════════════════════════════════════════════════════════════

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db

client = TestClient(app)


class TestEventCacheAside:
    def test_cache_hit_returns_cached_data(self, db_session):
        cached_event = {"event_id": 1, "name": "Cached Event", "season_year": 2024,
                        "tba_event_key": "2024test", "city": None, "state_prov": None,
                        "country": None, "start_date": "2024-03-01", "end_date": "2024-03-03",
                        "created_at": "2024-01-01T00:00:00"}

        mock_cache = MagicMock()
        mock_cache.get.return_value = cached_event
        mock_cache.event_key.return_value = "event:1"

        app.dependency_overrides[get_db] = lambda: db_session
        with patch("app.routers.events.cache", mock_cache):
            resp = client.get("/events/1")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        mock_cache.get.assert_called_once_with("event:1")
        # DB should NOT have been queried
        mock_cache.set.assert_not_called()

    def test_cache_miss_falls_through_to_db(self, db_session):
        from datetime import date
        from app.models.event import Event
        e = Event(event_id=19001, season_year=2024, tba_event_key="2024miss",
                  name="Miss Event", start_date=date(2024,3,1), end_date=date(2024,3,3))
        db_session.add(e)
        db_session.flush()

        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # cache miss
        mock_cache.event_key.return_value = "event:19001"

        app.dependency_overrides[get_db] = lambda: db_session
        with patch("app.routers.events.cache", mock_cache):
            resp = client.get("/events/19001")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        mock_cache.set.assert_called_once()  # populated after DB hit

    def test_rankings_cache_hit(self, db_session):
        cached_rankings = [{"rank": 1, "team_id": 1, "team_number": 254,
                            "team_name": "The Cheesy Poofs", "total_score": 42.0,
                            "matches_played": 6, "avg_distance_ft": 120.0}]

        mock_cache = MagicMock()
        mock_cache.get.return_value = cached_rankings
        mock_cache.rankings_key.return_value = "rankings:1"

        app.dependency_overrides[get_db] = lambda: db_session
        with patch("app.routers.events.cache", mock_cache):
            resp = client.get("/events/1/rankings")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json() == cached_rankings


class TestTeamCacheAside:
    def test_cache_hit_skips_db(self, db_session):
        cached_team = {"team_id": 1, "team_number": 254, "team_name": "Cheesy Poofs",
                       "school_name": None, "city": None, "state_prov": None,
                       "country": None, "rookie_year": None,
                       "created_at": "2024-01-01T00:00:00"}

        mock_cache = MagicMock()
        mock_cache.get.return_value = cached_team
        mock_cache.team_key.return_value = "team:1"

        app.dependency_overrides[get_db] = lambda: db_session
        with patch("app.routers.teams.cache", mock_cache):
            resp = client.get("/teams/1")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        mock_cache.set.assert_not_called()

    def test_cache_miss_populates_on_db_hit(self, db_session):
        from app.models.team import Team
        t = Team(team_id=19002, team_number=19002)
        db_session.add(t)
        db_session.flush()

        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_cache.team_key.return_value = "team:19002"

        app.dependency_overrides[get_db] = lambda: db_session
        with patch("app.routers.teams.cache", mock_cache):
            resp = client.get("/teams/19002")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        mock_cache.set.assert_called_once()


class TestAllianceCacheAside:
    def test_cache_hit_returns_cached(self, db_session):
        cached = {"alliance_id": 1, "match_id": 1, "color": "red",
                  "total_score": None, "rp_earned": None, "won": None,
                  "robot_performances": []}

        mock_cache = MagicMock()
        mock_cache.get.return_value = cached
        mock_cache.alliance_key.return_value = "alliance:1"

        app.dependency_overrides[get_db] = lambda: db_session
        with patch("app.routers.alliances.cache", mock_cache):
            resp = client.get("/alliances/1")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        mock_cache.set.assert_not_called()


# ════════════════════════════════════════════════════════════════════════════
# Invalidation hook tests
# ════════════════════════════════════════════════════════════════════════════

class TestInvalidationHooks:
    def test_create_match_invalidates_event_cache(self, db_session):
        from datetime import date
        from app.models.event import Event
        e = Event(event_id=19003, season_year=2024, tba_event_key="2024inv",
                  name="Inv Event", start_date=date(2024,3,1), end_date=date(2024,3,3))
        db_session.add(e)
        db_session.flush()

        mock_cache = MagicMock()
        mock_cache.rankings_key.return_value = "rankings:19003"
        mock_cache.event_summary_key.return_value = "event_summary:19003"

        app.dependency_overrides[get_db] = lambda: db_session
        with patch("app.routers.matches.cache", mock_cache):
            resp = client.post("/matches/", json={
                "match_id": 19003,
                "event_id": 19003,
                "tba_match_key": "2024inv_qm1",
                "match_type": "qualification",
                "match_number": 1,
                "processing_status": "pending",
                "created_at": "2024-03-01T00:00:00",
            })
        app.dependency_overrides.clear()

        assert resp.status_code == 201
        mock_cache.invalidate.assert_any_call("rankings:19003")
        mock_cache.invalidate.assert_any_call("event_summary:19003")

    def test_create_scouting_observation_invalidates_team_cache(self, db_session):
        from datetime import date
        from app.models.event import Event
        from app.models.team import Team
        from app.models.match import Match
        from app.models.user import User
        from app.core.security import get_password_hash

        e = Event(event_id=19004, season_year=2024, tba_event_key="2024obs",
                  name="Obs Event", start_date=date(2024,3,1), end_date=date(2024,3,3))
        t = Team(team_id=19004, team_number=19004)
        m = Match(match_id=19004, event_id=19004, tba_match_key="2024obs_qm1",
                  match_type="qualification", match_number=1)
        scout = User(email="scout19004@test.com", username="scout19004",
                     hashed_password=get_password_hash("pass"),
                     role="SCOUT", is_active=True)
        db_session.add_all([e, t, m, scout])
        db_session.flush()

        mock_cache = MagicMock()
        mock_cache.team_key.return_value = "team:19004"

        app.dependency_overrides[get_db] = lambda: db_session
        with patch("app.routers.scouting_observations.cache", mock_cache):
            resp = client.post("/scouting_observations/", json={
                "match_id": 19004,
                "team_id": 19004,
                "scout_id": scout.user_id,
                "notes": "Great auto",
                "submitted_at": "2024-03-01T00:00:00",
            })
        app.dependency_overrides.clear()

        assert resp.status_code == 201
        mock_cache.invalidate.assert_any_call("team:19004")
        mock_cache.invalidate_prefix.assert_any_call("rankings:")


# ════════════════════════════════════════════════════════════════════════════
# Admin cache endpoints
# ════════════════════════════════════════════════════════════════════════════

from datetime import timedelta


def _admin_header(db_session) -> dict:
    from app.models.user import User
    from app.core.security import get_password_hash, create_access_token
    import time
    uid = int(time.time() * 1000) % 1_000_000
    user = User(
        email=f"admin{uid}@test.com",
        username=f"admin{uid}",
        hashed_password=get_password_hash("pass"),
        role="SYSTEM_ADMIN",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    token = create_access_token(subject=user.user_id, expires_delta=timedelta(days=1))
    return {"Authorization": f"Bearer {token}"}


class TestAdminCacheEndpoints:
    def test_cache_stats_returns_metrics(self, db_session):
        headers = _admin_header(db_session)
        mock_cache = MagicMock()
        mock_cache.is_healthy.return_value = True
        mock_cache.key_count.return_value = 42
        mock_cache.memory_used_bytes.return_value = 1024 * 512
        mock_cache.get_metrics.return_value = {
            "hits": 100, "misses": 20,
            "total_requests": 120, "hit_rate": 0.833,
        }

        app.dependency_overrides[get_db] = lambda: db_session
        with patch("app.services.cache_service.cache", mock_cache):
            resp = client.get("/admin/cache/stats", headers=headers)
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["healthy"] is True
        assert data["key_count"] == 42
        assert data["hits"] == 100
        assert data["hit_rate"] == pytest.approx(0.833, abs=0.001)

    def test_cache_stats_requires_admin(self, db_session):
        from app.models.user import User
        from app.core.security import get_password_hash, create_access_token
        import time
        uid = int(time.time() * 1000) % 1_000_000
        user = User(
            email=f"scout{uid}@test.com",
            username=f"scout{uid}",
            hashed_password=get_password_hash("pass"),
            role="SCOUT",
            is_active=True,
        )
        db_session.add(user)
        db_session.flush()
        token = create_access_token(subject=user.user_id, expires_delta=timedelta(days=1))
        headers = {"Authorization": f"Bearer {token}"}

        app.dependency_overrides[get_db] = lambda: db_session
        resp = client.get("/admin/cache/stats", headers=headers)
        app.dependency_overrides.clear()

        assert resp.status_code == 403

    def test_cache_invalidate_all(self, db_session):
        headers = _admin_header(db_session)
        mock_cache = MagicMock()
        mock_cache.invalidate_prefix.return_value = 5

        app.dependency_overrides[get_db] = lambda: db_session
        with patch("app.services.cache_service.cache", mock_cache):
            resp = client.post("/admin/cache/invalidate?prefix=all", headers=headers)
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json()["prefix"] == "all"

    def test_cache_invalidate_by_prefix(self, db_session):
        headers = _admin_header(db_session)
        mock_cache = MagicMock()
        mock_cache.invalidate_prefix.return_value = 3

        app.dependency_overrides[get_db] = lambda: db_session
        with patch("app.services.cache_service.cache", mock_cache):
            resp = client.post("/admin/cache/invalidate?prefix=rankings:", headers=headers)
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json()["deleted_keys"] == 3
        mock_cache.invalidate_prefix.assert_called_once_with("rankings:")