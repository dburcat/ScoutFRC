"""
predictions.py
==============
Phase 2 Tier 9 — Prediction & Ranking REST endpoints.

Routes
------
GET  /predictions/matches/{match_id}
    Returns cached prediction for a specific match.  Falls back to live
    computation if cache is cold.

GET  /predictions/events/{event_id}
    Returns all cached match predictions for an event.

GET  /predictions/teams/{team_id}/strength
    Returns cached strength score for a team. Falls back to live computation.

GET  /predictions/events/{event_id}/rankings
    Returns teams sorted by strength score for an event.

GET  /predictions/events/{event_id}/alliance-recommendations/{team_id}
    Returns top pick recommendations for an alliance captain.

POST /predictions/events/{event_id}/compute
    Trigger batch prediction Celery task for an event (auth required).

POST /predictions/train
    Trigger model training Celery task (SYSTEM_ADMIN only).

GET  /predictions/model/status
    Returns model availability and training metadata.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.routers.deps import get_current_user
from app.services.cache_service import cache
from app.services.predictor import (
    TeamStats,
    predict_match_outcome,
    compute_team_strength,
    generate_alliance_recommendations,
    load_model,
    MODEL_PATH,
)

logger = logging.getLogger(__name__)

predictions_router = APIRouter(prefix="/predictions", tags=["predictions"])

# ── Cache key helpers (mirror prediction_tasks.py) ───────────────────────────

def _prediction_key(match_id: int) -> str:
    return f"prediction:match:{match_id}"

def _strength_key(team_id: int) -> str:
    return f"prediction:strength:{team_id}"

def _event_predictions_key(event_id: int) -> str:
    return f"prediction:event:{event_id}"


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class MatchPrediction(BaseModel):
    match_id: int
    tba_match_key: str | None = None
    match_type: str | None = None
    match_number: int | None = None
    red_win_probability: float
    blue_win_probability: float
    predicted_red_score: float
    predicted_blue_score: float
    red_score_low: float
    red_score_high: float
    blue_score_low: float
    blue_score_high: float
    confidence: str          # "high" | "medium" | "low"
    model_available: bool


class TeamStrength(BaseModel):
    team_id: int
    team_number: int | None = None
    team_name: str | None = None
    strength_score: float
    auto_contribution: float
    teleop_contribution: float
    endgame_contribution: float
    win_rate_contribution: float
    matches_played: int
    confidence: str


class AllianceRecommendationOut(BaseModel):
    rank: int
    team_id: int
    team_number: int | None = None
    team_name: str | None = None
    strength_score: float
    projected_alliance_score: float
    coverage_notes: list[str]


class ComputeResponse(BaseModel):
    task_id: str
    event_id: int | None = None
    status: str


class TrainResponse(BaseModel):
    task_id: str
    status: str


class ModelStatus(BaseModel):
    model_available: bool
    model_path: str
    model_size_bytes: int | None = None


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_team_stats_live(db: Session, team_id: int, event_id: int | None = None) -> TeamStats:
    """Build TeamStats from DB (used when cache is cold)."""
    from sqlalchemy import func
    from app.models.phase_stat import PhaseStat
    from app.models.match import Match
    from app.models.alliance import Alliance
    from app.models.robot_performance import RobotPerformance
    import numpy as np

    q = db.query(PhaseStat).filter(PhaseStat.team_id == team_id)
    if event_id is not None:
        q = q.join(Match, Match.match_id == PhaseStat.match_id).filter(
            Match.event_id == event_id
        )
    rows = q.all()

    def _phase_mean(phase: str, field: str) -> float:
        vals = [getattr(r, field) for r in rows if r.phase == phase]
        return float(np.mean(vals)) if vals else 0.0

    rp_q = (
        db.query(Alliance.won)
        .join(RobotPerformance, RobotPerformance.alliance_id == Alliance.alliance_id)
        .filter(RobotPerformance.team_id == team_id, Alliance.won.isnot(None))
    )
    if event_id is not None:
        rp_q = rp_q.join(Match, Match.match_id == Alliance.match_id).filter(
            Match.event_id == event_id
        )
    outcomes = [r.won for r in rp_q.all()]
    win_rate = float(np.mean([1.0 if w else 0.0 for w in outcomes])) if outcomes else 0.0

    return TeamStats(
        team_id=team_id,
        auto_score=_phase_mean("auto", "estimated_score"),
        teleop_score=_phase_mean("teleop", "estimated_score"),
        endgame_score=_phase_mean("endgame", "estimated_score"),
        auto_distance_ft=_phase_mean("auto", "distance_traveled_ft"),
        teleop_distance_ft=_phase_mean("teleop", "distance_traveled_ft"),
        endgame_distance_ft=_phase_mean("endgame", "distance_traveled_ft"),
        avg_velocity_fps=_phase_mean("teleop", "avg_velocity_fps"),
        max_velocity_fps=max(
            _phase_mean("auto", "max_velocity_fps"),
            _phase_mean("teleop", "max_velocity_fps"),
        ),
        time_in_scoring_zone_s=(
            _phase_mean("auto", "time_in_scoring_zone_s") +
            _phase_mean("teleop", "time_in_scoring_zone_s")
        ),
        win_rate=win_rate,
        matches_played=len(set(r.match_id for r in rows)),
    )


def _team_strength_payload(stats: TeamStats, team=None) -> dict:
    strength = compute_team_strength(stats)
    return {
        "team_id": strength.team_id,
        "team_number": team.team_number if team else None,
        "team_name": team.team_name if team else None,
        "strength_score": strength.strength_score,
        "auto_contribution": strength.auto_contribution,
        "teleop_contribution": strength.teleop_contribution,
        "endgame_contribution": strength.endgame_contribution,
        "win_rate_contribution": strength.win_rate_contribution,
        "matches_played": strength.matches_played,
        "confidence": strength.confidence,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@predictions_router.get(
    "/matches/{match_id}",
    response_model=MatchPrediction,
    summary="Get win probability and score prediction for a match",
)
def get_match_prediction(
    match_id: int,
    db: Session = Depends(get_db),
):
    """
    Returns match outcome prediction. Reads from Redis cache first.
    Falls back to live computation if cache is cold.
    """
    cached = cache.get(_prediction_key(match_id))
    if cached:
        return cached

    # Live fallback — find teams in this match
    from app.models.match import Match
    from app.models.alliance import Alliance
    from app.models.robot_performance import RobotPerformance

    match = db.query(Match).filter(Match.match_id == match_id).first()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    alliances = {a.color: a for a in match.alliances}
    if "red" not in alliances or "blue" not in alliances:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Match does not have both red and blue alliances configured",
        )

    red_ids = [
        rp.team_id for rp in
        db.query(RobotPerformance)
        .filter(RobotPerformance.alliance_id == alliances["red"].alliance_id).all()
    ]
    blue_ids = [
        rp.team_id for rp in
        db.query(RobotPerformance)
        .filter(RobotPerformance.alliance_id == alliances["blue"].alliance_id).all()
    ]

    if not red_ids or not blue_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insufficient team data to generate a prediction for this match.",
        )

    red_stats = [_get_team_stats_live(db, tid) for tid in red_ids]
    blue_stats = [_get_team_stats_live(db, tid) for tid in blue_ids]

    prediction = predict_match_outcome(red_stats, blue_stats)

    return MatchPrediction(
        match_id=match_id,
        tba_match_key=match.tba_match_key,
        match_type=match.match_type,
        match_number=match.match_number,
        red_win_probability=prediction.red_win_probability,
        blue_win_probability=prediction.blue_win_probability,
        predicted_red_score=prediction.predicted_red_score,
        predicted_blue_score=prediction.predicted_blue_score,
        red_score_low=prediction.red_score_low,
        red_score_high=prediction.red_score_high,
        blue_score_low=prediction.blue_score_low,
        blue_score_high=prediction.blue_score_high,
        confidence=prediction.confidence,
        model_available=prediction.model_available,
    )


@predictions_router.get(
    "/events/{event_id}",
    response_model=list[MatchPrediction],
    summary="Get predictions for all matches in an event",
)
def get_event_predictions(
    event_id: int,
    db: Session = Depends(get_db),
):
    """Returns cached batch predictions for an event. Empty list if not yet computed."""
    cached = cache.get(_event_predictions_key(event_id))
    if cached:
        return cached

    # No cache — check event exists
    from app.models.event import Event
    event = db.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    return []


@predictions_router.get(
    "/teams/{team_id}/strength",
    response_model=TeamStrength,
    summary="Get strength score for a team",
)
def get_team_strength(
    team_id: int,
    event_id: int | None = Query(None, description="Scope to a specific event"),
    db: Session = Depends(get_db),
):
    """
    Returns team strength score (0–100). Reads from cache, falls back to live computation.
    Optionally scoped to a specific event for event-relative strength.
    """
    cache_key = _strength_key(team_id) if event_id is None else f"prediction:strength:{team_id}:event:{event_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    from app.models.team import Team
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    stats = _get_team_stats_live(db, team_id, event_id)
    payload = _team_strength_payload(stats, team)
    cache.set(cache_key, payload, ttl=900)
    return payload


@predictions_router.get(
    "/events/{event_id}/rankings",
    response_model=list[TeamStrength],
    summary="Rank all teams in an event by predicted strength score",
)
def get_event_strength_rankings(
    event_id: int,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Returns all teams in an event sorted by strength score descending.
    Aggregates from phase stats and win/loss records.
    """
    from app.models.match import Match
    from app.models.alliance import Alliance
    from app.models.robot_performance import RobotPerformance
    from app.models.team import Team
    from app.models.event import Event

    event = db.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    # Collect all team IDs that participated in this event
    rp_rows = (
        db.query(RobotPerformance.team_id)
        .join(Alliance, Alliance.alliance_id == RobotPerformance.alliance_id)
        .join(Match, Match.match_id == Alliance.match_id)
        .filter(Match.event_id == event_id)
        .distinct()
        .all()
    )
    team_ids = [r.team_id for r in rp_rows]

    if not team_ids:
        return []

    rankings: list[dict] = []
    for team_id in team_ids:
        team = db.query(Team).filter(Team.team_id == team_id).first()
        stats = _get_team_stats_live(db, team_id, event_id)
        payload = _team_strength_payload(stats, team)
        rankings.append(payload)

    rankings.sort(key=lambda r: r["strength_score"], reverse=True)
    return rankings[:limit]


@predictions_router.get(
    "/events/{event_id}/alliance-recommendations/{team_id}",
    response_model=list[AllianceRecommendationOut],
    summary="Get top alliance pick recommendations for a team",
)
def get_alliance_recommendations(
    event_id: int,
    team_id: int,
    top_n: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    Ranks all other teams in the event as alliance picks for the given captain.
    Scores are based on projected 2-team alliance strength.
    """
    from app.models.match import Match
    from app.models.alliance import Alliance
    from app.models.robot_performance import RobotPerformance
    from app.models.team import Team

    # Verify captain exists
    captain_team = db.query(Team).filter(Team.team_id == team_id).first()
    if not captain_team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Captain team not found")

    # All teams in the event
    rp_rows = (
        db.query(RobotPerformance.team_id)
        .join(Alliance, Alliance.alliance_id == RobotPerformance.alliance_id)
        .join(Match, Match.match_id == Alliance.match_id)
        .filter(Match.event_id == event_id)
        .distinct()
        .all()
    )
    all_team_ids = [r.team_id for r in rp_rows]

    if team_id not in all_team_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Captain team has no data in this event.",
        )

    captain_stats = _get_team_stats_live(db, team_id, event_id)
    candidate_stats = [
        _get_team_stats_live(db, tid, event_id)
        for tid in all_team_ids
        if tid != team_id
    ]

    teams = {
        t.team_id: t
        for t in db.query(Team).filter(Team.team_id.in_(all_team_ids)).all()
    }
    team_numbers: dict[int, int | None] = {tid: teams[tid].team_number for tid in all_team_ids if tid in teams}
    team_names: dict[int, str | None] = {tid: teams[tid].team_name for tid in all_team_ids if tid in teams}

    recommendations = generate_alliance_recommendations(
        captain_stats=captain_stats,
        candidate_stats=candidate_stats,
        team_numbers=team_numbers,
        team_names=team_names,
        top_n=top_n,
    )

    return [
        AllianceRecommendationOut(
            rank=r.rank,
            team_id=r.team_id,
            team_number=r.team_number,
            team_name=r.team_name,
            strength_score=r.strength_score,
            projected_alliance_score=r.projected_alliance_score,
            coverage_notes=r.coverage_notes,
        )
        for r in recommendations
    ]


@predictions_router.post(
    "/events/{event_id}/compute",
    response_model=ComputeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger batch match predictions for an event",
)
def trigger_event_predictions(
    event_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Dispatches the ``run_batch_predictions`` Celery task for an event.
    Requires authentication.
    """
    from app.models.event import Event
    from app.tasks.prediction_tasks import run_batch_predictions

    event = db.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    result = run_batch_predictions.apply_async(
        kwargs={"event_id": event_id},
        queue="analytics",
    )

    return ComputeResponse(task_id=result.id, event_id=event_id, status="queued")


@predictions_router.post(
    "/train",
    response_model=TrainResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger ML model training (SYSTEM_ADMIN only)",
)
def trigger_training(
    current_user=Depends(get_current_user),
):
    """
    Dispatches model training. Requires SYSTEM_ADMIN role.
    """
    from app.tasks.prediction_tasks import train_prediction_model

    if current_user.role != "SYSTEM_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Model training requires SYSTEM_ADMIN role.",
        )

    result = train_prediction_model.apply_async(queue="analytics")
    return TrainResponse(task_id=result.id, status="queued")


@predictions_router.get(
    "/model/status",
    response_model=ModelStatus,
    summary="Check ML model availability and metadata",
)
def get_model_status():
    """Returns whether the trained model artifact exists and its file size."""
    model_available = MODEL_PATH.exists()
    size = MODEL_PATH.stat().st_size if model_available else None
    return ModelStatus(
        model_available=model_available,
        model_path=str(MODEL_PATH),
        model_size_bytes=size,
    )