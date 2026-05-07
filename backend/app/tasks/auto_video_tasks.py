"""
auto_video_tasks.py
-------------------
Celery task that automatically downloads and processes match videos from TBA
YouTube URLs. Called by the scheduler after each active-event sync.

Flow:
  1. Scheduler finds matches with video_url set and processing_status='pending'
  2. Dispatches process_match_video_from_url per match
  3. Task downloads video to a temp file
  4. Runs existing CV pipeline (process_video_file logic)
  5. Deletes temp file immediately — no permanent storage
  6. Updates match.processing_status to 'complete' or 'failed'
"""
from __future__ import annotations

import logging
from typing import cast

from celery import Task

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.video_downloader import VideoDownloadError, download_video_temp
from app.services.websocket_utils import emit_task_progress_sync

logger = logging.getLogger(__name__)


def _set_match_status(match_id: int, status: str) -> None:
    """Update match.processing_status in its own short-lived session."""
    from app.models.match import Match
    with SessionLocal() as db:
        match = db.query(Match).filter(Match.match_id == match_id).first()
        if match:
            match.processing_status = status
            db.commit()


def _get_match_info(match_id: int) -> dict | None:
    """Fetch the data needed to queue CV processing."""
    from app.models.match import Match
    from app.models.alliance import Alliance
    from app.models.robot_performance import RobotPerformance
    from sqlalchemy.orm import joinedload

    with SessionLocal() as db:
        match = (
            db.query(Match)
            .options(
                joinedload(Match.alliances).joinedload(Alliance.robot_performances)
            )
            .filter(Match.match_id == match_id)
            .first()
        )
        if not match:
            return None

        # Build alliance_teams dict: {"red": [team_numbers], "blue": [team_numbers]}
        # and team_id_lookup: {team_number: team_id}
        from app.models.team import Team
        alliance_teams: dict[str, list[int]] = {"red": [], "blue": []}
        team_id_lookup: dict[str, int] = {}

        for alliance in match.alliances:
            for perf in alliance.robot_performances:
                team = db.query(Team).filter(Team.team_id == perf.team_id).first()
                if team:
                    alliance_teams[alliance.color].append(team.team_number)
                    team_id_lookup[str(team.team_number)] = team.team_id

        return {
            "match_id": match.match_id,
            "event_id": match.event_id,
            "video_url": match.video_url,
            "alliance_teams": alliance_teams,
            "team_id_lookup": team_id_lookup,
        }


@celery_app.task(
    bind=True,
    name="auto_video_tasks.process_match_video_from_url",
    queue="video",
    max_retries=2,
    autoretry_for=(),   # We handle retries manually — don't retry download errors
    retry_backoff=True,
    retry_backoff_max=600,
)
def process_match_video_from_url(self: Task, match_id: int) -> dict:
    """
    Download the TBA YouTube video for a match and run CV processing.
    The video file is deleted immediately after processing — no permanent storage.
    """
    logger.info("auto_video: starting for match %d", match_id)

    # Mark as processing so the scheduler doesn't re-queue it
    _set_match_status(match_id, "processing")

    try:
        info = _get_match_info(match_id)
        if not info:
            raise ValueError(f"Match {match_id} not found")
        if not info["video_url"]:
            raise ValueError(f"Match {match_id} has no video_url")

        def _emit(stage: str, current: int = 0, total: int = 100) -> None:
            try:
                emit_task_progress_sync(
                    task_id=self.request.id,
                    status="PROGRESS",
                    stage=stage,
                    current=current,
                    total=total,
                )
            except Exception:
                pass

        _emit("downloading", 0, 100)

        # Download to temp file — deleted automatically on context exit
        with download_video_temp(info["video_url"], match_id) as video_path:
            _emit("processing", 10, 100)

            # Run the CV pipeline inline (same logic as process_video_file task)
            import os
            import numpy as np
            from app.crud.crud_movement_track import (
                bulk_create_movement_tracks,
                get_calibration_for_event,
            )
            from app.services.video_processor import VideoProcessor, VideoProcessingError

            YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
            USE_GPU = os.getenv("CELERY_USE_GPU", "false").lower() == "true"

            calibration_matrix: np.ndarray | None = None
            with SessionLocal() as db:
                cal = get_calibration_for_event(db, info["event_id"])
                if cal is not None:
                    calibration_matrix = np.array(
                        cal.perspective_matrix, dtype=np.float64
                    )

            processor = VideoProcessor(
                model_path=YOLO_MODEL_PATH,
                calibration_matrix=calibration_matrix,
                use_gpu=USE_GPU,
            )

            tid_lookup = (
                {int(k): v for k, v in info["team_id_lookup"].items()}
                if info["team_id_lookup"]
                else None
            )

            movement_tracks = processor.process_video(
                video_path=video_path,
                match_id=match_id,
                alliance_teams=info["alliance_teams"],
                progress_callback=lambda p, t, s: _emit(s, p, t),
                team_id_lookup=tid_lookup,
            )

            _emit("saving", 95, 100)

            with SessionLocal() as db:
                saved = bulk_create_movement_tracks(db, movement_tracks)

        # Video file is now deleted (context manager exited above)
        _set_match_status(match_id, "complete")

        # Dispatch analytics task
        try:
            from app.tasks.analytics_tasks import compute_robot_performance
            compute_robot_performance.apply_async(
                kwargs={"match_id": match_id},
                queue="analytics",
                countdown=2,
            )
        except Exception as exc:
            logger.warning("Failed to dispatch analytics for match %d: %s", match_id, exc)

        result = {
            "match_id": match_id,
            "movement_tracks_saved": saved,
            "status": "complete",
            "video_retained": False,  # Explicitly confirm no storage used
        }
        logger.info("auto_video: complete for match %d — %d tracks saved", match_id, saved)
        _emit("complete", 100, 100)
        return result

    except VideoDownloadError as exc:
        # Don't retry download errors (video may be unavailable/private)
        logger.warning("auto_video: download failed for match %d: %s", match_id, exc)
        _set_match_status(match_id, "failed")
        return {"match_id": match_id, "status": "failed", "reason": str(exc)}

    except Exception as exc:
        logger.error("auto_video: error for match %d: %s", match_id, exc)
        _set_match_status(match_id, "failed")
        raise


process_match_video_from_url_task: Task = cast(Task, process_match_video_from_url)


@celery_app.task(
    name="auto_video_tasks.queue_pending_video_matches",
    queue="default",
    max_retries=1,
    autoretry_for=(Exception,),
)
def queue_pending_video_matches_task() -> dict:
    """
    Beat-triggered poll task: find matches with a video_url and
    processing_status='pending', then dispatch process_match_video_from_url
    for each. Runs every 2 minutes so new TBA video URLs are picked up quickly
    after each active-event sync.
    """
    queued = queue_pending_video_matches()
    return {"queued": queued}


def queue_pending_video_matches() -> int:
    """
    Find all matches that have a video_url but haven't been processed yet,
    and dispatch process_match_video_from_url for each.

    Called by the scheduler after each active-event sync.
    Returns the number of matches queued.
    """
    from app.models.match import Match
    from app.models.event import Event
    from datetime import date, timedelta

    # Only process matches from active/recently-completed events
    # (avoid re-processing old historical matches)
    today = date.today()
    window_start = today - timedelta(days=3)

    with SessionLocal() as db:
        pending = (
            db.query(Match)
            .join(Event, Event.event_id == Match.event_id)
            .filter(
                Match.video_url.isnot(None),
                Match.processing_status == "pending",
                Event.start_date >= window_start,
            )
            .all()
        )

        queued = 0
        for match in pending:
            try:
                process_match_video_from_url_task.apply_async(
                    kwargs={"match_id": match.match_id},
                    queue="video",
                )
                # Mark as 'processing' immediately to prevent double-queuing
                match.processing_status = "processing"
                queued += 1
                logger.info(
                    "auto_video: queued match %d (%s)",
                    match.match_id,
                    match.tba_match_key,
                )
            except Exception as exc:
                logger.warning(
                    "auto_video: failed to queue match %d: %s", match.match_id, exc
                )

        if queued:
            db.commit()

    logger.info("auto_video: queued %d match(es) for video processing", queued)
    return queued