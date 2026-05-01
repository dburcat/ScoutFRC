"""
performance.py
==============
REST endpoints for Phase 2 Tier 3 — Robot Performance Analytics.

GET  /matches/{match_id}/performance
    Returns PhaseStat rows for every team in a match, grouped by team.

GET  /teams/{team_id}/performance
    Returns PhaseStat rows for a team across all matches, optionally
    filtered by event_id.

POST /matches/{match_id}/performance/compute
    Manually trigger the analytics Celery task for a match (admin / scout).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.phase_stat import PhaseStat
from app.models.movement_track import MovementTrack
from app.routers.deps import get_current_user

performance_router = APIRouter(tags=["performance"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class PhaseStatRead(BaseModel):
    id: int
    match_id: int
    team_id: int
    phase: str
    distance_traveled_ft: float
    avg_velocity_fps: float
    max_velocity_fps: float
    time_in_scoring_zone_s: float
    estimated_score: float
    actions_detected: list[str] | None
    track_count: int
    data_confidence: str

    model_config = {"from_attributes": True}


class TeamPerformanceSummary(BaseModel):
    team_id: int
    phases: list[PhaseStatRead]


class MatchPerformanceResponse(BaseModel):
    match_id: int
    teams: list[TeamPerformanceSummary]


class ComputeResponse(BaseModel):
    task_id: str
    match_id: int
    status: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _group_by_team(rows: list[PhaseStat]) -> list[TeamPerformanceSummary]:
    """Group PhaseStat rows by team_id."""
    by_team: dict[int, list[PhaseStatRead]] = {}
    for row in rows:
        by_team.setdefault(row.team_id, []).append(PhaseStatRead.model_validate(row))
    return [
        TeamPerformanceSummary(team_id=tid, phases=phases)
        for tid, phases in sorted(by_team.items())
    ]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@performance_router.get(
    "/matches/{match_id}/performance",
    response_model=MatchPerformanceResponse,
    summary="Get performance stats for all teams in a match",
)
def get_match_performance(
    match_id: int,
    db: Session = Depends(get_db),
):
    """
    Returns PhaseStat records for every team in the match, grouped by team.
    Returns 404 if no analytics have been computed yet.
    """
    rows: list[PhaseStat] = (
        db.query(PhaseStat)
        .filter(PhaseStat.match_id == match_id)
        .order_by(PhaseStat.team_id, PhaseStat.phase)
        .all()
    )

    if not rows:
        # Check whether the match exists vs. analytics simply not run yet
        track_exists = (
            db.query(MovementTrack.id)
            .filter(MovementTrack.match_id == match_id)
            .first()
        )
        detail = (
            "Analytics not yet computed for this match. "
            "Use POST /matches/{match_id}/performance/compute to trigger."
            if track_exists
            else "No movement data found for this match."
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    return MatchPerformanceResponse(
        match_id=match_id,
        teams=_group_by_team(rows),
    )


@performance_router.get(
    "/teams/{team_id}/performance",
    response_model=list[PhaseStatRead],
    summary="Get performance stats for a team across matches",
)
def get_team_performance(
    team_id: int,
    event_id: int | None = Query(None, description="Filter by event ID"),
    phase: str | None = Query(None, description="Filter by phase: auto | teleop | endgame"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Returns all PhaseStat records for a team, optionally filtered by
    event or game phase.  Results are ordered by match_id, phase.
    """
    from app.models.match import Match

    q = db.query(PhaseStat).filter(PhaseStat.team_id == team_id)

    if event_id is not None:
        q = q.join(Match, Match.match_id == PhaseStat.match_id).filter(
            Match.event_id == event_id
        )

    if phase is not None:
        valid_phases = {"auto", "teleop", "endgame"}
        if phase not in valid_phases:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"phase must be one of {sorted(valid_phases)}",
            )
        q = q.filter(PhaseStat.phase == phase)

    rows = (
        q.order_by(PhaseStat.match_id, PhaseStat.phase)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [PhaseStatRead.model_validate(r) for r in rows]


@performance_router.post(
    "/matches/{match_id}/performance/compute",
    response_model=ComputeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Manually trigger analytics computation for a match",
)
def trigger_compute(
    match_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Dispatch `compute_robot_performance` Celery task for a specific match.
    Requires authentication.  Returns the Celery task_id for polling.
    """
    from app.tasks.analytics_tasks import compute_robot_performance

    # Verify movement data exists before dispatching
    track_exists = (
        db.query(MovementTrack.id)
        .filter(MovementTrack.match_id == match_id)
        .first()
    )
    if not track_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No movement tracks found for this match. Upload and process a video first.",
        )

    result = compute_robot_performance.apply_async(
        kwargs={"match_id": match_id},
        queue="analytics",
    )

    return ComputeResponse(
        task_id=result.id,
        match_id=match_id,
        status="queued",
    )