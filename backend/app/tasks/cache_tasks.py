"""
cache_tasks.py
==============
Phase 2 Tier 4 — Celery tasks for cache management.

Tasks
-----
refresh_dashboard_cache
    Celery Beat periodic task (default every 10 min).
    Pre-computes and caches:
      - Team rankings per event
      - Event summary statistics
      - Alliance projection data

warmup_cache
    One-shot task dispatched at application startup.
    Populates the cache before the first real request arrives.
"""

from __future__ import annotations

import logging

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.cache_service import (
    cache,
    TTL_RANKINGS,
    TTL_EVENT,
    TTL_ALLIANCE,
)

logger = logging.getLogger(__name__)


# ── Data builders (pure DB queries, no HTTP) ──────────────────────────────────

def _build_event_rankings(db, event_id: int) -> list[dict]:
    """
    Compute team rankings for an event based on phase stats.
    Returns list of {team_id, team_number, total_score, matches_played} sorted by score.
    """
    from sqlalchemy import func
    from app.models.phase_stat import PhaseStat
    from app.models.match import Match
    from app.models.team import Team

    rows = (
        db.query(
            PhaseStat.team_id,
            func.sum(PhaseStat.estimated_score).label("total_score"),
            func.count(PhaseStat.match_id.distinct()).label("matches_played"),
            func.avg(PhaseStat.distance_traveled_ft).label("avg_distance"),
        )
        .join(Match, Match.match_id == PhaseStat.match_id)
        .filter(Match.event_id == event_id)
        .group_by(PhaseStat.team_id)
        .order_by(func.sum(PhaseStat.estimated_score).desc())
        .all()
    )

    rankings = []
    for rank, row in enumerate(rows, start=1):
        team = db.query(Team).filter(Team.team_id == row.team_id).first()
        rankings.append({
            "rank": rank,
            "team_id": row.team_id,
            "team_number": team.team_number if team else None,
            "team_name": team.team_name if team else None,
            "total_score": round(float(row.total_score or 0), 2),
            "matches_played": row.matches_played,
            "avg_distance_ft": round(float(row.avg_distance or 0), 2),
        })
    return rankings


def _build_event_summary(db, event_id: int) -> dict:
    """Compute summary statistics for an event."""
    from app.models.match import Match
    from app.models.phase_stat import PhaseStat
    from sqlalchemy import func

    match_count = db.query(Match).filter(Match.event_id == event_id).count()

    stats = (
        db.query(
            func.count(PhaseStat.team_id.distinct()).label("team_count"),
            func.avg(PhaseStat.estimated_score).label("avg_score"),
            func.max(PhaseStat.estimated_score).label("max_score"),
            func.avg(PhaseStat.distance_traveled_ft).label("avg_distance"),
        )
        .join(Match, Match.match_id == PhaseStat.match_id)
        .filter(Match.event_id == event_id)
        .first()
    )

    return {
        "event_id": event_id,
        "match_count": match_count,
        "team_count": int(stats.team_count or 0),
        "avg_score": round(float(stats.avg_score or 0), 2),
        "max_score": round(float(stats.max_score or 0), 2),
        "avg_distance_ft": round(float(stats.avg_distance or 0), 2),
    }


def _build_alliance_projection(db, alliance_id: int) -> dict:
    """Compute projected performance metrics for a user-built alliance."""
    from app.models.user_alliance import UserAlliance
    from app.models.phase_stat import PhaseStat
    from sqlalchemy import func

    ua = db.query(UserAlliance).filter(UserAlliance.alliance_id == alliance_id).first()
    if not ua:
        return {}

    # UserAlliance stores comma-separated team IDs in red_teams / blue_teams
    def _parse_ids(s: str) -> list[int]:
        return [int(x) for x in s.split(",") if x.strip().isdigit()]

    team_ids = _parse_ids(ua.red_teams or "") + _parse_ids(ua.blue_teams or "")

    if not team_ids:
        return {"alliance_id": alliance_id, "team_count": 0, "projected_score": 0.0}

    stats = (
        db.query(
            func.avg(PhaseStat.estimated_score).label("avg_score"),
            func.avg(PhaseStat.distance_traveled_ft).label("avg_distance"),
        )
        .filter(PhaseStat.team_id.in_(team_ids))
        .first()
    )

    return {
        "alliance_id": alliance_id,
        "name": ua.name,
        "team_count": len(team_ids),
        "projected_score": round(float(stats.avg_score or 0) * len(team_ids), 2),
        "avg_team_distance_ft": round(float(stats.avg_distance or 0), 2),
    }


# ── Core refresh logic (separated so warmup can reuse) ───────────────────────

def _do_refresh(db) -> dict:
    """Run full cache refresh. Returns summary dict."""
    from app.models.event import Event
    from datetime import date

    refreshed = {"events": 0, "alliances": 0, "errors": 0}

    # Refresh rankings + summaries for all active/recent events
    events = (
        db.query(Event)
        .filter(Event.season_year >= date.today().year - 1)
        .all()
    )

    for event in events:
        try:
            rankings = _build_event_rankings(db, event.event_id)
            cache.set(
                cache.rankings_key(event.event_id),
                rankings,
                ttl=TTL_RANKINGS,
            )

            summary = _build_event_summary(db, event.event_id)
            cache.set(
                cache.event_summary_key(event.event_id),
                summary,
                ttl=TTL_EVENT,
            )
            refreshed["events"] += 1
        except Exception as exc:
            logger.warning("Cache refresh failed for event %d: %s", event.event_id, exc)
            refreshed["errors"] += 1

    # Refresh alliance projections — UserAlliance only (user-built alliance picks,
    # not the 2-per-match Alliance rows which would be 300k+ entries)
    from app.models.user_alliance import UserAlliance
    user_alliances = db.query(UserAlliance).all()
    for ua in user_alliances:
        try:
            projection = _build_alliance_projection(db, ua.alliance_id)
            cache.set(
                cache.alliance_key(ua.alliance_id),
                projection,
                ttl=TTL_ALLIANCE,
            )
            refreshed["alliances"] += 1
        except Exception as exc:
            logger.warning("Cache refresh failed for user_alliance %d: %s", ua.alliance_id, exc)
            refreshed["errors"] += 1

    return refreshed


# ── Celery Beat task ──────────────────────────────────────────────────────────

@celery_app.task(
    name="cache_tasks.refresh_dashboard_cache",
    queue="default",
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def refresh_dashboard_cache() -> dict:
    """
    Periodic task: pre-compute and cache expensive dashboard queries.
    Scheduled via Celery Beat (default every 10 minutes).
    """
    logger.info("refresh_dashboard_cache: starting")
    with SessionLocal() as db:
        result = _do_refresh(db)
    logger.info("refresh_dashboard_cache: complete %s", result)
    return result


# ── Startup warm-up task ──────────────────────────────────────────────────────

@celery_app.task(
    name="cache_tasks.warmup_cache",
    queue="default",
    max_retries=1,
)
def warmup_cache() -> dict:
    """
    One-shot task dispatched at application startup to pre-populate cache
    before the first real request arrives.
    """
    if not cache.is_healthy():
        logger.warning("warmup_cache: Redis not reachable, skipping")
        return {"status": "skipped", "reason": "redis_unavailable"}

    logger.info("warmup_cache: starting")
    with SessionLocal() as db:
        result = _do_refresh(db)
    logger.info("warmup_cache: complete %s", result)
    return {"status": "complete", **result}