"""
DeepSORT multi-object tracker with:
  - track_to_team mapping across frames
  - configuration change detection (bbox area change ≥ 35%)
  - multi-frame OCR voting for conflict resolution
  - Kalman gap prediction flags
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict, deque

import numpy as np

from .types import Detection, TeamIdentification, TrackedRobot

logger = logging.getLogger(__name__)

CONFIGURATION_CHANGE_THRESHOLD = 0.35   # 35% area change triggers re-ID
OCR_MIN_CONFIDENCE = 0.80
COLOR_MIN_CONFIDENCE = 0.55
SPATIAL_CONFIDENCE = 0.65
TRACK_CONTINUITY_CONFIDENCE = 0.85
MAX_BBOX_HISTORY = 10
VOTE_WINDOW = 5                          # frames for multi-frame OCR voting
VOTE_MAJORITY = 3                        # out of VOTE_WINDOW


class RobotTracker:
    """
    Wraps deep_sort_realtime and adds FRC-specific identity management.

    Usage:
        tracker = RobotTracker()
        tracked = tracker.update(frame, detections, identifications)
    """

    def __init__(self) -> None:
        self._tracker = self._build_tracker()
        # DeepSORT track_id → confirmed team_number
        self.track_to_team: dict[int, int] = {}
        # Historical bboxes per track_id for size-change detection
        self._bbox_history: dict[int, deque] = defaultdict(
            lambda: deque(maxlen=MAX_BBOX_HISTORY)
        )
        # OCR vote history per track_id for conflict resolution
        self._ocr_votes: dict[int, deque] = defaultdict(
            lambda: deque(maxlen=VOTE_WINDOW)
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def update(
        self,
        frame: np.ndarray,
        detections: list[Detection],
        identifications: list[TeamIdentification],
    ) -> list[TrackedRobot]:
        """
        Feed new detections + identifications to the tracker.
        Returns the list of confirmed tracked robots for this frame.
        """
        # Format for deep_sort_realtime: [[x1,y1,w,h, conf], ...]
        raw = []
        for d in detections:
            x1, y1, x2, y2 = d.bbox
            raw.append(([x1, y1, x2 - x1, y2 - y1], d.confidence, d.class_name))

        tracks = self._tracker.update_tracks(raw, frame=frame)

        results: list[TrackedRobot] = []
        for track in tracks:
            if not track.is_confirmed():
                continue

            tid = track.track_id
            ltrb = track.to_ltrb()
            self._bbox_history[tid].append(ltrb)

            size_change = self._size_change(tid)
            config_changed = size_change > CONFIGURATION_CHANGE_THRESHOLD

            # Pick the best identification for this track
            ident = self._resolve_identity(
                tid,
                identifications,
                config_changed=config_changed,
            )

            # Update team mapping from high-confidence identifications
            if (
                ident.team_number is not None
                and ident.confidence >= OCR_MIN_CONFIDENCE
                and ident.method.startswith("OCR")
            ):
                self.track_to_team[tid] = ident.team_number

            results.append(
                TrackedRobot(
                    track_id=tid,
                    bbox=np.array(ltrb),
                    team_number=ident.team_number,
                    identification_method=ident.method,
                    confidence=ident.confidence,
                    bbox_size_change=size_change,
                    configuration_changed=config_changed,
                    is_predicted=not track.is_confirmed(),
                    team_number_visible=(
                        ident.method.startswith("OCR") and ident.confidence >= OCR_MIN_CONFIDENCE
                    ),
                    flagged=ident.flagged,
                    flag_reason=ident.flag_reason,
                )
            )

        return results

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_tracker(self):
        try:
            from deep_sort_realtime.deepsort_tracker import DeepSort  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "deep-sort-realtime is required. "
                "Install with: pip install deep-sort-realtime"
            ) from exc

        return DeepSort(
            max_age=30,
            n_init=3,
            max_cosine_distance=0.4,
            nn_budget=100,
            embedder="mobilenet",
            half=False,         # FP32 for CPU compatibility
            embedder_gpu=False, # set True on GPU workers
        )

    def _size_change(self, track_id: int) -> float:
        history = self._bbox_history[track_id]
        if len(history) < 2:
            return 0.0
        areas = [(b[2] - b[0]) * (b[3] - b[1]) for b in history]
        avg = sum(areas[:-1]) / len(areas[:-1])
        return abs(areas[-1] - avg) / max(avg, 1.0)

    def _resolve_identity(
        self,
        track_id: int,
        identifications: list[TeamIdentification],
        config_changed: bool,
    ) -> TeamIdentification:
        """
        Pick the best TeamIdentification for this track_id.
        Prioritises OCR, then DeepSORT continuity, then falls through.
        """
        existing_team = self.track_to_team.get(track_id)

        # Find any OCR identification in this frame's results
        ocr_idents = [
            i for i in identifications
            if i.method.startswith("OCR") and i.team_number is not None
        ]

        if ocr_idents:
            best_ocr = max(ocr_idents, key=lambda i: i.confidence)

            if best_ocr.confidence >= OCR_MIN_CONFIDENCE:
                # Check for conflict with existing track assignment
                if (
                    existing_team is not None
                    and best_ocr.team_number != existing_team
                ):
                    return self._vote_on_conflict(track_id, best_ocr, existing_team)

                return TeamIdentification(
                    team_number=best_ocr.team_number,
                    method="OCR_post_config_change" if config_changed else "OCR",
                    confidence=best_ocr.confidence,
                )

        # No good OCR — use DeepSORT track continuity
        if existing_team is not None:
            flagged = config_changed
            return TeamIdentification(
                team_number=existing_team,
                method="TrackContinuity_post_config_change" if config_changed else "DeepSORT",
                confidence=TRACK_CONTINUITY_CONFIDENCE,
                flagged=flagged,
                flag_reason="configuration_change_assumed_same_team" if config_changed else None,
            )

        # Fall through: try any identification from the frame
        color_idents = [
            i for i in identifications
            if i.method == "Color" and i.team_number is not None and i.confidence >= COLOR_MIN_CONFIDENCE
        ]
        if color_idents:
            best = max(color_idents, key=lambda i: i.confidence)
            return best

        # Nothing worked
        return TeamIdentification(
            team_number=None,
            method="UNKNOWN",
            confidence=0.0,
            flagged=True,
            flag_reason="all_identification_methods_failed",
        )

    def _vote_on_conflict(
        self,
        track_id: int,
        ocr_result: TeamIdentification,
        existing_team: int,
    ) -> TeamIdentification:
        """Multi-frame voting to resolve OCR vs. track history conflict."""
        self._ocr_votes[track_id].append(ocr_result.team_number)

        if len(self._ocr_votes[track_id]) < VOTE_WINDOW:
            return TeamIdentification(
                team_number=existing_team,
                method="DeepSORT",
                confidence=0.60,
                flagged=True,
                flag_reason="identity_conflict_pending_resolution",
            )

        vote_counts = Counter(self._ocr_votes[track_id])
        majority_team, count = vote_counts.most_common(1)[0]

        if count >= VOTE_MAJORITY:
            self.track_to_team[track_id] = majority_team
            logger.info(
                "Track %d identity updated to team %d via voting (%d/%d)",
                track_id, majority_team, count, VOTE_WINDOW,
            )
            return TeamIdentification(
                team_number=majority_team,
                method="OCR_MultiFrameVote",
                confidence=count / VOTE_WINDOW,
            )

        return TeamIdentification(
            team_number=existing_team,
            method="DeepSORT",
            confidence=0.50,
            flagged=True,
            flag_reason="identity_conflict_no_majority",
        )