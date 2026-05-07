"""
prediction_tasks.py
===================
Phase 2 Tier 9 — Celery tasks for ML model training and batch predictions.

Tasks
-----
train_prediction_model
    Pulls all historical PhaseStat + Alliance win/loss data, builds feature
    matrix, trains a GradientBoostingClassifier, and saves the artifact.
    Queued on the ``analytics`` queue. Should be triggered after every N
    new matches or manually via the API.

run_batch_predictions
    For all upcoming (unplayed) matches in an event, computes predictions
    and caches results in Redis for instant API reads.
"""

from __future__ import annotations

import logging
from typing import cast

import numpy as np
from celery import Task

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.cache_service import cache
from app.services.predictor import (
    TeamStats,
    build_match_feature_row,
    compute_team_strength,
    predict_match_outcome,
    save_model,
    load_model,
)

logger = logging.getLogger(__name__)

# ── Cache TTL for predictions (10 minutes) ────────────────────────────────────
_PREDICTION_TTL = 600
_STRENGTH_TTL = 900


# ── Cache key helpers ─────────────────────────────────────────────────────────

def _prediction_key(match_id: int) -> str:
    return f"prediction:match:{match_id}"


def _strength_key(team_id: int) -> str:
    return f"prediction:strength:{team_id}"


def _event_predictions_key(event_id: int) -> str:
    return f"prediction:event:{event_id}"


# ── DB helpers ────────────────────────────────────────────────────────────────

def _build_team_stats(db, team_id: int, event_id: int | None = None) -> TeamStats:
    """
    Aggregate PhaseStat rows for a team into a TeamStats object.
    Optionally scoped to a specific event.
    """
    from sqlalchemy import func
    from app.models.phase_stat import PhaseStat
    from app.models.match import Match
    from app.models.alliance import Alliance
    from app.models.robot_performance import RobotPerformance

    q = db.query(PhaseStat).filter(PhaseStat.team_id == team_id)

    if event_id is not None:
        q = q.join(Match, Match.match_id == PhaseStat.match_id).filter(
            Match.event_id == event_id
        )

    rows = q.all()

    def _phase_mean(phase: str, field: str) -> float:
        vals = [getattr(r, field) for r in rows if r.phase == phase]
        return float(np.mean(vals)) if vals else 0.0

    # Win rate from RobotPerformance → Alliance.won
    rp_query = (
        db.query(Alliance.won)
        .join(RobotPerformance, RobotPerformance.alliance_id == Alliance.alliance_id)
        .filter(RobotPerformance.team_id == team_id, Alliance.won.isnot(None))
    )
    if event_id is not None:
        rp_query = rp_query.join(Match, Match.match_id == Alliance.match_id).filter(
            Match.event_id == event_id
        )
    outcomes = [r.won for r in rp_query.all()]
    win_rate = float(np.mean([1.0 if w else 0.0 for w in outcomes])) if outcomes else 0.0
    matches_played = len(set(r.match_id for r in rows))

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
            (_phase_mean("auto", "max_velocity_fps"),
             _phase_mean("teleop", "max_velocity_fps")),
        ),
        time_in_scoring_zone_s=(
            _phase_mean("auto", "time_in_scoring_zone_s") +
            _phase_mean("teleop", "time_in_scoring_zone_s")
        ),
        win_rate=win_rate,
        matches_played=matches_played,
    )


def _build_training_data(db) -> tuple[list[list[float]], list[int]]:
    """
    Build the full training matrix from historical match data.

    Returns (X rows, y labels) where y=1 → red wins, y=0 → blue wins.
    Only includes matches where:
    - Alliance.won is not None (result is known)
    - Both alliances have at least one robot with PhaseStat data
    """
    from app.models.match import Match
    from app.models.alliance import Alliance
    from app.models.robot_performance import RobotPerformance

    X: list[list[float]] = []
    y: list[int] = []

    # Fetch all completed matches (both alliances have won set)
    matches = (
        db.query(Match)
        .filter(Match.processing_status == "complete")
        .all()
    )

    for match in matches:
        alliances = {a.color: a for a in match.alliances}
        if "red" not in alliances or "blue" not in alliances:
            continue

        red_alliance = alliances["red"]
        blue_alliance = alliances["blue"]

        if red_alliance.won is None:
            continue

        # Get team IDs for each alliance
        red_team_ids = [
            rp.team_id for rp in
            db.query(RobotPerformance)
            .filter(RobotPerformance.alliance_id == red_alliance.alliance_id)
            .all()
        ]
        blue_team_ids = [
            rp.team_id for rp in
            db.query(RobotPerformance)
            .filter(RobotPerformance.alliance_id == blue_alliance.alliance_id)
            .all()
        ]

        if not red_team_ids or not blue_team_ids:
            continue

        red_stats = [_build_team_stats(db, tid) for tid in red_team_ids]
        blue_stats = [_build_team_stats(db, tid) for tid in blue_team_ids]

        # Skip if no phase data available for any team
        if all(s.matches_played == 0 for s in red_stats + blue_stats):
            continue

        row = build_match_feature_row(red_stats, blue_stats)
        label = 1 if red_alliance.won else 0

        X.append(row)
        y.append(label)

    return X, y


# ── Training task ─────────────────────────────────────────────────────────────

def _run_training() -> dict:
    """Core training logic — separated for testability."""
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline

    with SessionLocal() as db:
        X_raw, y = _build_training_data(db)

    if len(X_raw) < 10:
        logger.warning(
            "train_prediction_model: only %d training samples — need >= 10. "
            "Skipping training, heuristic fallback remains active.",
            len(X_raw),
        )
        return {
            "status": "skipped",
            "reason": "insufficient_data",
            "samples": len(X_raw),
            "required": 10,
        }

    X = np.array(X_raw)
    y_arr = np.array(y)

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", GradientBoostingClassifier(
            n_estimators=150,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.85,
            min_samples_leaf=2,
            random_state=42,
        )),
    ])

    # Cross-validation on available data
    if len(X) >= 20:
        cv_scores = cross_val_score(model, X, y_arr, cv=5, scoring="roc_auc")
        mean_auc = float(np.mean(cv_scores))
        std_auc = float(np.std(cv_scores))
        logger.info(
            "train_prediction_model: CV ROC-AUC = %.3f ± %.3f", mean_auc, std_auc
        )
    else:
        mean_auc = None
        std_auc = None
        logger.info(
            "train_prediction_model: skipping CV (< 20 samples), training on full set"
        )

    # Final fit on all data
    model.fit(X, y_arr)
    save_model(model)

    result = {
        "status": "complete",
        "samples": len(X_raw),
        "positive_rate": round(float(np.mean(y_arr)), 3),
    }
    if mean_auc is not None and std_auc is not None:
        result["cv_roc_auc_mean"] = round(mean_auc, 4)
        result["cv_roc_auc_std"] = round(std_auc, 4)

    logger.info("train_prediction_model: %s", result)
    return result


@celery_app.task(
    bind=True,
    name="prediction_tasks.train_prediction_model",
    queue="analytics",
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
)
def _train_prediction_model_celery(self: Task) -> dict:
    try:
        return _run_training()
    except Exception as exc:
        logger.error("train_prediction_model failed: %s", exc)
        raise


train_prediction_model: Task = cast(Task, _train_prediction_model_celery)


# ── Batch prediction task ─────────────────────────────────────────────────────

def _run_batch_predictions(event_id: int) -> dict:
    """Compute and cache predictions for all upcoming matches in an event."""
    from app.models.match import Match
    from app.models.alliance import Alliance
    from app.models.robot_performance import RobotPerformance

    model = load_model()

    with SessionLocal() as db:
        # Target: matches that are pending (not yet played) in the event
        matches = (
            db.query(Match)
            .filter(Match.event_id == event_id)
            .all()
        )

        predicted = 0
        cached = 0
        errors = 0
        prediction_summaries = []

        for match in matches:
            try:
                alliances = {a.color: a for a in match.alliances}
                if "red" not in alliances or "blue" not in alliances:
                    continue

                red_ids = [
                    rp.team_id for rp in
                    db.query(RobotPerformance)
                    .filter(RobotPerformance.alliance_id == alliances["red"].alliance_id)
                    .all()
                ]
                blue_ids = [
                    rp.team_id for rp in
                    db.query(RobotPerformance)
                    .filter(RobotPerformance.alliance_id == alliances["blue"].alliance_id)
                    .all()
                ]

                if not red_ids or not blue_ids:
                    continue

                red_stats = [_build_team_stats(db, tid, event_id) for tid in red_ids]
                blue_stats = [_build_team_stats(db, tid, event_id) for tid in blue_ids]

                prediction = predict_match_outcome(red_stats, blue_stats, model=model)

                payload = {
                    "match_id": match.match_id,
                    "tba_match_key": match.tba_match_key,
                    "match_type": match.match_type,
                    "match_number": match.match_number,
                    "red_win_probability": prediction.red_win_probability,
                    "blue_win_probability": prediction.blue_win_probability,
                    "predicted_red_score": prediction.predicted_red_score,
                    "predicted_blue_score": prediction.predicted_blue_score,
                    "red_score_low": prediction.red_score_low,
                    "red_score_high": prediction.red_score_high,
                    "blue_score_low": prediction.blue_score_low,
                    "blue_score_high": prediction.blue_score_high,
                    "confidence": prediction.confidence,
                    "model_available": prediction.model_available,
                }

                cache.set(_prediction_key(match.match_id), payload, ttl=_PREDICTION_TTL)
                prediction_summaries.append(payload)
                predicted += 1

            except Exception as exc:
                logger.warning(
                    "batch_predictions: failed for match %d: %s",
                    match.match_id, exc
                )
                errors += 1

        # Also cache team strength scores for the event
        team_ids_seen: set[int] = set()
        for match in matches:
            for alliance in match.alliances:
                for rp in db.query(RobotPerformance).filter(
                    RobotPerformance.alliance_id == alliance.alliance_id
                ).all():
                    team_ids_seen.add(rp.team_id)

        for team_id in team_ids_seen:
            try:
                stats = _build_team_stats(db, team_id, event_id)
                strength = compute_team_strength(stats)
                cache.set(_strength_key(team_id), {
                    "team_id": strength.team_id,
                    "strength_score": strength.strength_score,
                    "auto_contribution": strength.auto_contribution,
                    "teleop_contribution": strength.teleop_contribution,
                    "endgame_contribution": strength.endgame_contribution,
                    "win_rate_contribution": strength.win_rate_contribution,
                    "matches_played": strength.matches_played,
                    "confidence": strength.confidence,
                }, ttl=_STRENGTH_TTL)
                cached += 1
            except Exception as exc:
                logger.warning("batch_predictions: strength cache failed team %d: %s", team_id, exc)

        # Cache the full event prediction list for the summary endpoint
        cache.set(_event_predictions_key(event_id), prediction_summaries, ttl=_PREDICTION_TTL)

    result = {
        "event_id": event_id,
        "matches_predicted": predicted,
        "team_strengths_cached": cached,
        "errors": errors,
        "status": "complete",
    }
    logger.info("run_batch_predictions: %s", result)
    return result


@celery_app.task(
    bind=True,
    name="prediction_tasks.run_batch_predictions",
    queue="analytics",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
)
def _run_batch_predictions_celery(self: Task, event_id: int) -> dict:
    try:
        return _run_batch_predictions(event_id)
    except Exception as exc:
        logger.error("run_batch_predictions failed for event %d: %s", event_id, exc)
        raise


run_batch_predictions: Task = cast(Task, _run_batch_predictions_celery)


# ── Beat-compatible polling tasks ─────────────────────────────────────────────

@celery_app.task(
    name="prediction_tasks.refresh_active_event_predictions",
    queue="analytics",
    max_retries=1,
    autoretry_for=(Exception,),
)
def refresh_active_event_predictions() -> dict:
    """
    Beat-triggered task: dispatch run_batch_predictions for every active/upcoming
    event so prediction cache stays fresh without manual API calls.
    Runs every 10 minutes — fast enough to reflect new match results.
    """
    from app.models.event import Event
    from datetime import date, timedelta

    today = date.today()
    window_end = today + timedelta(days=7)

    with SessionLocal() as db:
        events = (
            db.query(Event)
            .filter(Event.start_date <= window_end, Event.end_date >= today)
            .all()
        )
        event_ids = [e.event_id for e in events]

    if not event_ids:
        logger.info("refresh_active_event_predictions: no active/upcoming events")
        return {"dispatched": 0}

    dispatched = 0
    for event_id in event_ids:
        try:
            run_batch_predictions.apply_async(
                kwargs={"event_id": event_id},
                queue="analytics",
            )
            dispatched += 1
        except Exception as exc:
            logger.warning("Failed to dispatch predictions for event %d: %s", event_id, exc)

    logger.info("refresh_active_event_predictions: dispatched %d event(s)", dispatched)
    return {"dispatched": dispatched}


@celery_app.task(
    name="prediction_tasks.scheduled_model_retrain",
    queue="analytics",
    max_retries=1,
    autoretry_for=(Exception,),
)
def scheduled_model_retrain() -> dict:
    """
    Beat-triggered task: retrain the prediction model nightly so it
    incorporates the day's new match results automatically.
    """
    logger.info("scheduled_model_retrain: dispatching train_prediction_model")
    try:
        result = train_prediction_model.apply_async(queue="analytics")
        return {"task_id": result.id, "status": "dispatched"}
    except Exception as exc:
        logger.error("scheduled_model_retrain: failed to dispatch: %s", exc)
        raise