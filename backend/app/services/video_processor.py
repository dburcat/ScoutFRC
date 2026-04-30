"""
Main video processing pipeline orchestrator.

Stages:
  1. Decode frames at target FPS
  2. YOLOv8 robot detection
  3. Cascaded team identification
  4. DeepSORT tracking + re-identification
  5. Perspective transform → field coordinates
  6. Build MovementTrack records (returned to caller for bulk DB write)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from .cv.detector import RobotDetector
from .cv.perspective import FieldPerspectiveTransform
from .cv.team_identifier import TeamIdentifier
from .cv.tracker import RobotTracker

logger = logging.getLogger(__name__)

# ── Review flag thresholds ────────────────────────────────────────────────────
REVIEW_CONFIDENCE_THRESHOLD = 0.60
FRAME_SAMPLE_FPS = 10           # Extract this many frames per second
PROGRESS_INTERVAL = 50          # Report progress every N processed frames

ACCEPTED_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv"}


class VideoProcessingError(Exception):
    """Raised for unrecoverable video errors (corrupt, unsupported format, etc.)"""


@dataclass
class MovementTrackCreate:
    """DTO — matches MovementTrack model columns, used for bulk insert."""
    match_id: int
    team_id: int | None
    track_id: int
    frame_number: int
    timestamp_ms: int
    pixel_x: float
    pixel_y: float
    field_x: float | None
    field_y: float | None
    bounding_box_width: float | None
    bounding_box_height: float | None
    bounding_box_size_change: float
    identification_method: str
    confidence_score: float
    team_number_visible: bool
    interpolated: bool
    configuration_changed: bool
    flagged_for_review: bool
    review_reason: str | None

    def to_dict(self) -> dict:
        return self.__dict__.copy()


ProgressCallback = Callable[[int, int, str], None]


class VideoProcessor:
    """
    Orchestrates the full CV pipeline for a single match video file.

    Parameters
    ----------
    model_path:
        Path to YOLOv8 .pt weights (fine-tuned or placeholder).
    calibration_matrix:
        Optional 3×3 numpy array from EventCameraCalibration.
    processing_fps:
        Number of frames per second to process (default 10).
    use_gpu:
        Whether to enable GPU for YOLO and EasyOCR.
    """

    def __init__(
        self,
        model_path: str | Path = "yolov8n.pt",
        calibration_matrix: np.ndarray | None = None,
        processing_fps: int = FRAME_SAMPLE_FPS,
        use_gpu: bool = False,
    ) -> None:
        self.detector = RobotDetector(model_path=model_path)
        self.tracker = RobotTracker()
        self.identifier = TeamIdentifier(use_gpu=use_gpu)
        self.transform = FieldPerspectiveTransform(matrix=calibration_matrix)
        self.processing_fps = processing_fps
        self._frame_interval_ms = 1000 / processing_fps

    # ── Public API ────────────────────────────────────────────────────────────

    def process_video(
        self,
        video_path: Path,
        match_id: int,
        alliance_teams: dict[str, list[int]],
        progress_callback: ProgressCallback | None = None,
        team_id_lookup: dict[int, int] | None = None,
    ) -> list[MovementTrackCreate]:
        """
        Process video_path and return a list of MovementTrackCreate records.

        Parameters
        ----------
        video_path:
            Local path to the video file.
        match_id:
            DB match_id to attach all records to.
        alliance_teams:
            {"red": [team_number, ...], "blue": [team_number, ...]}
        progress_callback:
            Optional function(processed_frames, total_frames, stage_name).
        team_id_lookup:
            Optional {team_number → team_id} dict for FK resolution.
            When absent, team_id is stored as None.
        """
        self._validate_video(video_path)

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise VideoProcessingError(f"Could not open video file: {video_path}")

        source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_skip = max(1, round(source_fps / self.processing_fps))
        estimated_processed = max(1, total_frames // frame_skip)

        logger.info(
            "Processing video: %s  source_fps=%.1f  frame_skip=%d  "
            "estimated_frames=%d",
            video_path.name, source_fps, frame_skip, estimated_processed,
        )

        if progress_callback:
            progress_callback(0, estimated_processed, "extracting")

        all_tracks: list[MovementTrackCreate] = []
        frame_number = 0
        processed_count = 0

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_number += 1
                if frame_number % frame_skip != 0:
                    continue

                tracks = self._process_frame(
                    frame, frame_number, match_id, alliance_teams, team_id_lookup
                )
                all_tracks.extend(tracks)
                processed_count += 1

                if progress_callback and processed_count % PROGRESS_INTERVAL == 0:
                    progress_callback(processed_count, estimated_processed, "tracking")

        except Exception as exc:
            logger.exception("Error during video processing at frame %d", frame_number)
            raise VideoProcessingError(
                f"Processing failed at frame {frame_number}: {exc}"
            ) from exc
        finally:
            cap.release()

        if progress_callback:
            progress_callback(processed_count, estimated_processed, "complete")

        flagged = sum(1 for t in all_tracks if t.flagged_for_review)
        logger.info(
            "Video processing complete: %d frames → %d track rows (%d flagged)",
            processed_count, len(all_tracks), flagged,
        )
        return all_tracks

    # ── Private helpers ───────────────────────────────────────────────────────

    def _validate_video(self, video_path: Path) -> None:
        if not video_path.exists():
            raise VideoProcessingError(f"Video file not found: {video_path}")
        if video_path.suffix.lower() not in ACCEPTED_SUFFIXES:
            raise VideoProcessingError(
                f"Unsupported video format '{video_path.suffix}'. "
                f"Accepted: {', '.join(ACCEPTED_SUFFIXES)}"
            )

    def _process_frame(
        self,
        frame: np.ndarray,
        frame_number: int,
        match_id: int,
        alliance_teams: dict[str, list[int]],
        team_id_lookup: dict[int, int] | None,
    ) -> list[MovementTrackCreate]:
        # Stage 1: Detect
        detections = self.detector.detect(frame)
        robot_detections = [
            d for d in detections if d.class_name in ("robot_red", "robot_blue")
        ]
        if not robot_detections:
            return []

        # Stage 2: Identify
        identifications = self.identifier.identify_all(
            frame, robot_detections, alliance_teams, frame_number
        )

        # Stage 3: Track
        tracked = self.tracker.update(frame, robot_detections, identifications)

        # Stage 4: Build records
        records: list[MovementTrackCreate] = []
        for robot in tracked:
            field_x, field_y = self.transform.apply(
                robot.bbox_center_x, robot.bbox_center_y
            )

            # Resolve team_number → team_id FK
            team_id: int | None = None
            if robot.team_number is not None and team_id_lookup:
                team_id = team_id_lookup.get(robot.team_number)

            # Apply review flag for low confidence
            flagged = robot.flagged or robot.confidence < REVIEW_CONFIDENCE_THRESHOLD
            review_reason = robot.flag_reason
            if not flagged and robot.confidence < REVIEW_CONFIDENCE_THRESHOLD:
                flagged = True
                review_reason = "low_confidence"

            records.append(
                MovementTrackCreate(
                    match_id=match_id,
                    team_id=team_id,
                    track_id=robot.track_id,
                    frame_number=frame_number,
                    timestamp_ms=int(frame_number * self._frame_interval_ms),
                    pixel_x=robot.bbox_center_x,
                    pixel_y=robot.bbox_center_y,
                    field_x=field_x,
                    field_y=field_y,
                    bounding_box_width=robot.bbox_width,
                    bounding_box_height=robot.bbox_height,
                    bounding_box_size_change=robot.bbox_size_change,
                    identification_method=robot.identification_method,
                    confidence_score=robot.confidence,
                    team_number_visible=robot.team_number_visible,
                    interpolated=robot.is_predicted,
                    configuration_changed=robot.configuration_changed,
                    flagged_for_review=flagged,
                    review_reason=review_reason,
                )
            )

        return records