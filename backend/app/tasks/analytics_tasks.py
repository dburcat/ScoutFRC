"""
analytics_tasks.py
==================
Celery task: compute_robot_performance

Queries MovementTrack rows for a completed match, runs the
performance_calculator, and upserts PhaseStat rows to the database.

This task is auto-chained after process_video_file via Celery `chain`,
but can also be triggered manually via the API.
"""

from __future__ import annotations

import logging
from typing import cast

from celery import Task
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.movement_track import MovementTrack
from app.models.phase_stat import PhaseStat
from app.services.performance_calculator import compute_phase_stats

logger = logging.getLogger(__name__)


# ── DB helpers ────────────────────────────────────────────────────────────────

def _fetch_tracks(db: Session, match_id: int) -> list[MovementTrack]:
    """Load all non-null-team_id MovementTrack rows for a match."""
    return (
        db.query(MovementTrack)
        .filter(
            MovementTrack.match_id == match_id,
            MovementTrack.team_id.isnot(None),
        )
        .order_by(MovementTrack.team_id, MovementTrack.timestamp_ms)
        .all()
    )


def _upsert_phase_stats(db: Session, stats: list) -> int:
    """
    Upsert PhaseStat rows using PostgreSQL ON CONFLICT DO UPDATE.
    Falls back to a delete-then-insert for non-Postgres backends (SQLite in tests).
    """
    if not stats:
        return 0

    dialect = db.bind.dialect.name if db.bind else "postgresql"

    if dialect == "postgresql":
        rows = [
            {
                "match_id": s.match_id,
                "team_id": s.team_id,
                "phase": s.phase,
                "distance_traveled_ft": s.distance_traveled_ft,
                "avg_velocity_fps": s.avg_velocity_fps,
                "max_velocity_fps": s.max_velocity_fps,
                "time_in_scoring_zone_s": s.time_in_scoring_zone_s,
                "estimated_score": s.estimated_score,
                "actions_detected": s.actions_detected,
                "track_count": s.track_count,
                "data_confidence": s.data_confidence,
            }
            for s in stats
        ]
        stmt = pg_insert(PhaseStat).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_phase_stat_match_team_phase",
            set_={
                "distance_traveled_ft": stmt.excluded.distance_traveled_ft,
                "avg_velocity_fps": stmt.excluded.avg_velocity_fps,
                "max_velocity_fps": stmt.excluded.max_velocity_fps,
                "time_in_scoring_zone_s": stmt.excluded.time_in_scoring_zone_s,
                "estimated_score": stmt.excluded.estimated_score,
                "actions_detected": stmt.excluded.actions_detected,
                "track_count": stmt.excluded.track_count,
                "data_confidence": stmt.excluded.data_confidence,
            },
        )
        db.execute(stmt)
        db.commit()
        return len(rows)

    else:
        # SQLite / test fallback: delete-then-insert
        keys = [(s.match_id, s.team_id, s.phase) for s in stats]
        for match_id, team_id, phase in keys:
            db.query(PhaseStat).filter(
                PhaseStat.match_id == match_id,
                PhaseStat.team_id == team_id,
                PhaseStat.phase == phase,
            ).delete()
        for s in stats:
            db.add(PhaseStat(
                match_id=s.match_id,
                team_id=s.team_id,
                phase=s.phase,
                distance_traveled_ft=s.distance_traveled_ft,
                avg_velocity_fps=s.avg_velocity_fps,
                max_velocity_fps=s.max_velocity_fps,
                time_in_scoring_zone_s=s.time_in_scoring_zone_s,
                estimated_score=s.estimated_score,
                actions_detected=s.actions_detected,
                track_count=s.track_count,
                data_confidence=s.data_confidence,
            ))
        db.commit()
        return len(stats)


# ── Task implementation ───────────────────────────────────────────────────────

def _run_analytics(match_id: int) -> dict:
    """Core logic (separated so tests can call directly without Celery)."""
    with SessionLocal() as db:
        tracks = _fetch_tracks(db, match_id)

    if not tracks:
        logger.warning("compute_robot_performance: no tracks found for match %d", match_id)
        return {
            "match_id": match_id,
            "phase_stats_saved": 0,
            "teams_processed": 0,
            "status": "no_data",
        }

    team_ids = {t.team_id for t in tracks if t.team_id is not None}
    logger.info(
        "compute_robot_performance: match=%d  tracks=%d  teams=%s",
        match_id, len(tracks), sorted(team_ids),
    )

    stats = compute_phase_stats(match_id=match_id, tracks=tracks)

    with SessionLocal() as db:
        saved = _upsert_phase_stats(db, stats)

    result = {
        "match_id": match_id,
        "phase_stats_saved": saved,
        "teams_processed": len(team_ids),
        "status": "complete",
    }
    logger.info("compute_robot_performance complete: %s", result)
    return result


@celery_app.task(
    bind=True,
    name="analytics_tasks.compute_robot_performance",
    queue="analytics",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
)
def _compute_robot_performance_celery(self: Task, match_id: int, **_kwargs) -> dict:
    """
    Celery entry-point.

    Accepts **_kwargs so that when chained after process_video_file the
    previous task's result dict is passed as keyword arguments without
    breaking this task's signature.
    """
    try:
        return _run_analytics(match_id)
    except Exception as exc:
        logger.error("compute_robot_performance failed for match %d: %s", match_id, exc)
        raise


compute_robot_performance: Task = cast(Task, _compute_robot_performance_celery)