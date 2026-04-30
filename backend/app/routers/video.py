"""
Video processing & CV admin endpoints.

POST /matches/{match_id}/video        — Upload match video, dispatch Celery task
GET  /tasks/{task_id}/status          — Poll task progress
GET  /admin/cv/flagged                — List tracks flagged for review
PATCH /admin/cv/tracks/{track_id}     — Correct a flagged track
POST /admin/cv/calibration/{event_id} — Store perspective calibration matrix
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.crud.crud_movement_track import (
    correct_track,
    create_calibration,
    get_flagged_tracks,
)
from app.routers.deps import get_current_user, get_db
from app.tasks.video_tasks import process_video_file

ACCEPTED_MIME = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska"}
ACCEPTED_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv"}
VIDEO_UPLOAD_DIR = Path(os.getenv("VIDEO_UPLOAD_DIR", "/tmp/scouterfrc_videos"))

video_router = APIRouter(tags=["video"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class VideoUploadResponse(BaseModel):
    task_id: str
    match_id: int
    status: str


class TrackCorrectionRequest(BaseModel):
    correct_team_id: int


class CalibrationRequest(BaseModel):
    camera_position: str
    pixel_points: list[list[float]]   # 4 × [x, y] clicked by the user


class CalibrationResponse(BaseModel):
    id: int
    event_id: int
    camera_position: str
    active: bool


# ── Endpoints ─────────────────────────────────────────────────────────────────

@video_router.post(
    "/matches/{match_id}/video",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def upload_match_video(
    match_id: int,
    file: UploadFile = File(...),
    alliance_red: str = "",    # comma-separated team numbers e.g. "254,1678,118"
    alliance_blue: str = "",
    event_id: int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Accept an MP4/MOV video upload, save locally, and dispatch the
    process_video_file Celery task.
    Returns the task_id for polling via GET /tasks/{task_id}/status.
    """
    # Validate file type
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ACCEPTED_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported video format '{suffix}'. Accepted: {', '.join(ACCEPTED_SUFFIXES)}",
        )

    # Save to disk
    VIDEO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = VIDEO_UPLOAD_DIR / f"match_{match_id}{suffix}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # Parse alliance teams
    def parse_teams(s: str) -> list[int]:
        return [int(t.strip()) for t in s.split(",") if t.strip().isdigit()]

    alliance_teams = {
        "red": parse_teams(alliance_red),
        "blue": parse_teams(alliance_blue),
    }

    # Dispatch Celery task
    result = process_video_file.apply_async(
        kwargs={
            "match_id": match_id,
            "video_path": str(dest),
            "alliance_teams": alliance_teams,
            "event_id": event_id,
        },
        queue="video",
    )

    return VideoUploadResponse(
        task_id=result.id,
        match_id=match_id,
        status="queued",
    )


@video_router.get("/tasks/{task_id}/status")
def get_task_status(task_id: str):
    """Poll the status and progress of a Celery video processing task."""
    result = AsyncResult(task_id, app=celery_app)

    if result.state == "PENDING":
        return {"task_id": task_id, "state": "PENDING", "percent": 0, "stage": "queued"}

    if result.state == "PROGRESS":
        meta = result.info or {}
        return {
            "task_id": task_id,
            "state": "PROGRESS",
            "percent": meta.get("percent", 0),
            "stage": meta.get("stage", ""),
            "processed_frames": meta.get("processed_frames", 0),
            "total_frames": meta.get("total_frames", 0),
        }

    if result.state == "SUCCESS":
        return {"task_id": task_id, "state": "SUCCESS", "result": result.result}

    if result.state == "FAILURE":
        return {
            "task_id": task_id,
            "state": "FAILURE",
            "error": str(result.result),
        }

    return {"task_id": task_id, "state": result.state}


@video_router.get("/admin/cv/flagged")
def list_flagged_tracks(
    match_id: int | None = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all MovementTrack rows flagged for manual review."""
    tracks = get_flagged_tracks(db, match_id=match_id, skip=skip, limit=limit)
    return tracks


@video_router.patch("/admin/cv/tracks/{track_id}")
def correct_flagged_track(
    track_id: int,
    body: TrackCorrectionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Manually assign a team to a flagged MovementTrack row and clear the flag."""
    track = correct_track(db, track_id=track_id, correct_team_id=body.correct_team_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    return track


@video_router.post("/admin/cv/calibration/{event_id}", response_model=CalibrationResponse)
def save_calibration(
    event_id: int,
    body: CalibrationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Compute and store a perspective calibration matrix for an event.

    pixel_points: 4 × [x, y] pixel coordinates of the field corners
    in order [Blue-Near, Red-Near, Red-Far, Blue-Far].
    """
    from app.services.cv.perspective import FieldPerspectiveTransform

    if len(body.pixel_points) != 4:
        raise HTTPException(
            status_code=422,
            detail="Exactly 4 pixel_points are required (one per field corner).",
        )

    transform = FieldPerspectiveTransform.from_pixel_points(
        [(p[0], p[1]) for p in body.pixel_points]
    )
    matrix_json = transform.to_json()

    cal = create_calibration(
        db,
        event_id=event_id,
        camera_position=body.camera_position,
        perspective_matrix=matrix_json,
        calibrated_by=current_user.username,
    )
    return CalibrationResponse(
        id=cal.id,
        event_id=cal.event_id,
        camera_position=cal.camera_position,
        active=cal.active,
    )