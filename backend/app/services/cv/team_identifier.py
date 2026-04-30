"""
Cascaded team identification pipeline.

Priority order (per strategy doc):
  1. OCR  — read team number directly from bumper
  2. Color matching — match HSV histogram to calibrated profile
  3. Spatial constraint — use alliance + position to narrow candidates
  4. UNKNOWN — flag for manual review
"""

from __future__ import annotations

import logging

import numpy as np

from .color_matcher import TeamColorMatcher
from .ocr_reader import TeamNumberOCR
from .types import Detection, TeamIdentification

logger = logging.getLogger(__name__)

OCR_MIN_CONFIDENCE = 0.80
SPATIAL_CONFIDENCE = 0.65
OCR_FLAG_THRESHOLD = 0.65
COLOR_MIN_CONFIDENCE = 0.55
COLOR_FLAG_THRESHOLD = 0.70

# Calibration: when OCR confidence is above this during first 30 frames,
# build the color profile for the team
CALIBRATION_OCR_THRESHOLD = 0.85
CALIBRATION_FRAME_LIMIT = 30 * 10  # 30 seconds × 10 FPS


class TeamIdentifier:
    """
    Runs the full cascaded identification for each detected robot in a frame.
    """

    def __init__(self, use_gpu: bool = False) -> None:
        self.ocr = TeamNumberOCR(use_gpu=use_gpu)
        self.color = TeamColorMatcher()

    # ── Public API ────────────────────────────────────────────────────────────

    def identify_all(
        self,
        frame: np.ndarray,
        detections: list[Detection],
        alliance_teams: dict[str, list[int]],
        frame_number: int,
    ) -> list[TeamIdentification]:
        """
        Run cascaded identification for every robot detection in the frame.

        alliance_teams: {"red": [254, 1678, 118], "blue": [148, 1114, 33]}
        """
        results: list[TeamIdentification] = []

        for det in detections:
            # Candidates are the 3 teams from the matching alliance
            candidates = alliance_teams.get(det.alliance or "", [])
            if not candidates:
                candidates = alliance_teams.get("red", []) + alliance_teams.get("blue", [])

            ident = self._identify_one(frame, det, candidates, frame_number)
            results.append(ident)

            # Calibrate color profile during the opening of the match
            if (
                frame_number <= CALIBRATION_FRAME_LIMIT
                and ident.team_number is not None
                and ident.method.startswith("OCR")
                and ident.confidence >= CALIBRATION_OCR_THRESHOLD
                and ident.team_number not in self.color.calibrated_teams
            ):
                self.color.calibrate_team(ident.team_number, frame, det.bbox)

        return results

    # ── Private helpers ───────────────────────────────────────────────────────

    def _identify_one(
        self,
        frame: np.ndarray,
        det: Detection,
        candidates: list[int],
        frame_number: int,
    ) -> TeamIdentification:
        # ── Step 1: OCR ───────────────────────────────────────────────────────
        ocr = self.ocr.read_team_number(frame, det.bbox)

        if ocr.team_number is not None:
            if ocr.team_number in candidates or not candidates:
                if ocr.confidence >= OCR_MIN_CONFIDENCE:
                    return TeamIdentification(
                        team_number=ocr.team_number,
                        method="OCR",
                        confidence=ocr.confidence,
                    )
                if ocr.confidence >= OCR_FLAG_THRESHOLD:
                    return TeamIdentification(
                        team_number=ocr.team_number,
                        method="OCR",
                        confidence=ocr.confidence,
                        flagged=True,
                        flag_reason="low_confidence_ocr",
                    )

        # ── Step 2: Color matching ────────────────────────────────────────────
        color_team, color_conf = self.color.match(frame, det.bbox, candidates)

        if color_team is not None:
            if color_conf >= COLOR_MIN_CONFIDENCE:
                flagged = color_conf < COLOR_FLAG_THRESHOLD
                return TeamIdentification(
                    team_number=color_team,
                    method="Color",
                    confidence=color_conf,
                    flagged=flagged,
                    flag_reason="low_confidence_color" if flagged else None,
                )

        # ── Step 3: Spatial (alliance constraint only) ────────────────────────
        if len(candidates) == 1:
            return TeamIdentification(
                team_number=candidates[0],
                method="Spatial",
                confidence=SPATIAL_CONFIDENCE,
                flagged=True,
                flag_reason="low_confidence_spatial_only",
            )

        # ── Step 4: UNKNOWN ───────────────────────────────────────────────────
        return TeamIdentification(
            team_number=None,
            method="UNKNOWN",
            confidence=0.0,
            flagged=True,
            flag_reason="all_identification_methods_failed",
        )