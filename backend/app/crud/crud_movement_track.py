"""CRUD operations for MovementTrack and EventCameraCalibration."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.event_camera_calibration import EventCameraCalibration
from app.models.movement_track import MovementTrack
from app.services.video_processor import MovementTrackCreate

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


def bulk_create_movement_tracks(
    db: Session, records: list[MovementTrackCreate]
) -> int:
    """Insert MovementTrack rows in batches. Returns count of rows saved."""
    saved = 0
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        db.bulk_insert_mappings(
            MovementTrack,  # type: ignore[arg-type]
            [r.to_dict() for r in batch],
        )
        db.commit()
        saved += len(batch)
        logger.debug("Saved batch %d–%d", i, i + len(batch))
    return saved


def get_flagged_tracks(
    db: Session,
    match_id: int | None = None,
    skip: int = 0,
    limit: int = 200,
) -> list[MovementTrack]:
    q = db.query(MovementTrack).filter(MovementTrack.flagged_for_review == True)
    if match_id is not None:
        q = q.filter(MovementTrack.match_id == match_id)
    return q.order_by(MovementTrack.match_id, MovementTrack.frame_number).offset(skip).limit(limit).all()


def correct_track(
    db: Session,
    track_id: int,
    correct_team_id: int,
) -> MovementTrack | None:
    track = db.query(MovementTrack).filter(MovementTrack.id == track_id).first()
    if track is None:
        return None
    track.corrected_team_id = correct_team_id
    track.manually_corrected = True
    track.flagged_for_review = False
    track.review_reason = None
    db.commit()
    db.refresh(track)
    return track


def get_calibration_for_event(
    db: Session, event_id: int
) -> EventCameraCalibration | None:
    return (
        db.query(EventCameraCalibration)
        .filter(
            EventCameraCalibration.event_id == event_id,
            EventCameraCalibration.active == True,
        )
        .order_by(EventCameraCalibration.calibrated_at.desc())
        .first()
    )


def create_calibration(
    db: Session,
    event_id: int,
    camera_position: str,
    perspective_matrix: list,
    calibrated_by: str,
) -> EventCameraCalibration:
    # Deactivate previous calibrations for this event + position
    db.query(EventCameraCalibration).filter(
        EventCameraCalibration.event_id == event_id,
        EventCameraCalibration.camera_position == camera_position,
    ).update({"active": False})

    cal = EventCameraCalibration(
        event_id=event_id,
        camera_position=camera_position,
        perspective_matrix=perspective_matrix,
        calibrated_by=calibrated_by,
        active=True,
    )
    db.add(cal)
    db.commit()
    db.refresh(cal)
    return cal