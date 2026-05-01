"""
Celery task: process_video_file

Downloads a match video (local path for now; S3 path when storage is added),
runs the full CV pipeline, and persists MovementTrack rows to the database.
Progress is reported via Celery task state updates for frontend polling.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import cast

import numpy as np
from celery import Task

from app.celery_app import celery_app
from app.crud.crud_movement_track import bulk_create_movement_tracks, get_calibration_for_event
from app.db.session import SessionLocal
from app.services.video_processor import VideoProcessingError, VideoProcessor

logger = logging.getLogger(__name__)

YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
USE_GPU = os.getenv("CELERY_USE_GPU", "false").lower() == "true"


def _update(task: Task, processed: int, total: int, stage: str) -> None:
    task.update_state(
        state="PROGRESS",
        meta={
            "processed_frames": processed,
            "total_frames": total,
            "stage": stage,
            "percent": int(processed / max(total, 1) * 100),
        },
    )


def _process_video_task(
    self: Task,
    match_id: int,
    video_path: str,
    alliance_teams: dict[str, list[int]],
    event_id: int,
    team_id_lookup: dict[str, int] | None = None,
) -> dict:
    _update(self, 0, 100, "initialising")

    path = Path(video_path)
    if not path.exists():
        raise VideoProcessingError(f"Video file not found: {video_path}")

    # Load perspective calibration if available
    calibration_matrix: np.ndarray | None = None
    with SessionLocal() as db:
        cal = get_calibration_for_event(db, event_id)
        if cal is not None:
            calibration_matrix = np.array(cal.perspective_matrix, dtype=np.float64)
            logger.info("Loaded calibration matrix for event %d", event_id)
        else:
            logger.warning("No calibration found for event %d — field coordinates will be None", event_id)

    _update(self, 0, 100, "processing")

    processor = VideoProcessor(
        model_path=YOLO_MODEL_PATH,
        calibration_matrix=calibration_matrix,
        use_gpu=USE_GPU,
    )

    # Convert str keys to int for team_id_lookup
    tid_lookup: dict[int, int] | None = None
    if team_id_lookup:
        tid_lookup = {int(k): v for k, v in team_id_lookup.items()}

    movement_tracks = processor.process_video(
        video_path=path,
        match_id=match_id,
        alliance_teams=alliance_teams,
        progress_callback=lambda p, t, s: _update(self, p, t, s),
        team_id_lookup=tid_lookup,
    )

    _update(self, len(movement_tracks), len(movement_tracks), "saving")

    with SessionLocal() as db:
        saved = bulk_create_movement_tracks(db, movement_tracks)

    flagged = sum(1 for t in movement_tracks if t.flagged_for_review)
    result = {
        "match_id": match_id,
        "movement_tracks_saved": saved,
        "flagged_tracks": flagged,
        "flagged_rate": round(flagged / max(saved, 1), 3),
        "status": "complete",
    }
    logger.info("process_video_file complete: %s", result)

    # ── Auto-dispatch analytics task ──────────────────────────────────────────
    try:
        from app.tasks.analytics_tasks import compute_robot_performance
        compute_robot_performance.apply_async(
            kwargs={"match_id": match_id},
            queue="analytics",
            countdown=2,  # brief delay to ensure DB writes are visible
        )
        logger.info("Dispatched compute_robot_performance for match %d", match_id)
    except Exception as exc:  # pragma: no cover — don't fail video task if analytics fails to queue
        logger.error("Failed to dispatch analytics task for match %d: %s", match_id, exc)

    return result


@celery_app.task(
    bind=True,
    name="video_tasks.process_video_file",
    queue="video",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def _process_video_task_celery(
    self,
    match_id: int,
    video_path: str,
    alliance_teams: dict,
    event_id: int,
    team_id_lookup: dict | None = None,
) -> dict:
    try:
        return _process_video_task(
            self, match_id, video_path, alliance_teams, event_id, team_id_lookup
        )
    except VideoProcessingError as exc:
        logger.error("VideoProcessingError for match %d: %s", match_id, exc)
        # Do not retry corrupt/unsupported video errors
        raise self.retry(exc=exc, max_retries=0)


process_video_file: Task = cast(Task, _process_video_task_celery)