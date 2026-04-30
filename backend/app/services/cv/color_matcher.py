"""
HSV histogram-based robot color matching.

Builds a per-team color profile from the bumper region during the
calibration pass (first 30 frames when OCR confirms identity),
then uses Bhattacharyya distance for subsequent identification.
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

HISTOGRAM_BINS = [30, 32]           # Hue × Saturation bins
HISTOGRAM_RANGES = [0, 180, 0, 256]
MATCH_THRESHOLD = 0.45              # Bhattacharyya distance (lower = more similar)
BUMPER_REGION_RATIO = 0.70          # Use bottom 30% of bbox as bumper region


class TeamColorMatcher:
    """
    Maintains an HSV histogram color profile per team number.

    Profiles are calibrated at match start when OCR confirms a robot's
    identity, then used as a fallback when the number is unreadable.
    """

    def __init__(self, profiles_path: Path | None = None) -> None:
        self.profiles: dict[int, np.ndarray] = {}  # team_number → histogram
        if profiles_path and profiles_path.exists():
            with open(profiles_path, "rb") as f:
                self.profiles = pickle.load(f)
            logger.info(
                "Loaded color profiles for %d teams from %s",
                len(self.profiles), profiles_path,
            )

    # ── Calibration ───────────────────────────────────────────────────────────

    def calibrate_team(
        self, team_number: int, frame: np.ndarray, bbox: np.ndarray
    ) -> None:
        """
        Build (or update) the color profile for team_number using the
        bumper region extracted from frame at bbox.
        Call once per team when OCR confidence > 0.85.
        """
        region = self._bumper_region(frame, bbox)
        if region.size == 0:
            logger.warning("Empty bumper region for team %d — skipping calibration", team_number)
            return
        self.profiles[team_number] = self._histogram(region)
        logger.info("Calibrated color profile for team %d", team_number)

    def save(self, path: Path) -> None:
        with open(path, "wb") as f:
            pickle.dump(self.profiles, f)

    # ── Matching ──────────────────────────────────────────────────────────────

    def match(
        self,
        frame: np.ndarray,
        bbox: np.ndarray,
        candidate_teams: list[int],
    ) -> tuple[int | None, float]:
        """
        Return (team_number, confidence) for the best color match
        among candidate_teams.  Returns (None, 0.0) when no profile
        matches within MATCH_THRESHOLD.
        """
        region = self._bumper_region(frame, bbox)
        if region.size == 0:
            return None, 0.0

        query_hist = self._histogram(region)
        best_team: int | None = None
        best_dist = float("inf")

        for team_num in candidate_teams:
            profile = self.profiles.get(team_num)
            if profile is None:
                continue
            dist = float(
                cv2.compareHist(query_hist, profile, cv2.HISTCMP_BHATTACHARYYA)
            )
            if dist < best_dist:
                best_dist = dist
                best_team = team_num

        if best_team is None or best_dist > MATCH_THRESHOLD:
            return None, 0.0

        # Map distance to [0, 1] confidence (lower distance → higher confidence)
        confidence = max(0.0, 1.0 - (best_dist / MATCH_THRESHOLD))
        return best_team, confidence

    @property
    def calibrated_teams(self) -> list[int]:
        return list(self.profiles.keys())

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _bumper_region(self, frame: np.ndarray, bbox: np.ndarray) -> np.ndarray:
        x1, y1, x2, y2 = bbox.astype(int)
        bumper_y1 = y1 + int((y2 - y1) * BUMPER_REGION_RATIO)
        region = frame[bumper_y1:y2, x1:x2]
        return region

    def _histogram(self, region: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist(
            [hsv], [0, 1], None, HISTOGRAM_BINS, HISTOGRAM_RANGES
        )
        cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        return hist