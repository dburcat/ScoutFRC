"""
performance_calculator.py
=========================
Pure-function analytics engine for Phase 2 Tier 3.

Takes a list of MovementTrackCreate (or any NamedTuple/dataclass with the
same fields) and returns a list of PhaseStatResult dataclasses — one per
(team_id, phase) combination.

No database I/O here; all DB interaction is handled by the caller
(analytics_tasks.py).

FRC 2024 Crescendo timing constants (season-configurable via env):
  AUTO_END_MS    = 15 000  ms
  TELEOP_END_MS  = 135 000 ms  (15 + 120)
  MATCH_END_MS   = 150 000 ms  (15 + 120 + 15)

FRC 2024 Crescendo scoring zones (field feet, origin = Blue-Near corner):
  Speaker zones  — within 8 ft of each speaker opening
  Amp zones      — within 4 ft of each amp
  Stage/trap      — centre field box 17–37 ft x 8–19 ft
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

# ── Timing constants (ms) ─────────────────────────────────────────────────────

AUTO_END_MS: int = int(os.getenv("AUTO_END_MS", "15000"))
TELEOP_END_MS: int = int(os.getenv("TELEOP_END_MS", "135000"))
MATCH_END_MS: int = int(os.getenv("MATCH_END_MS", "150000"))

# ── Velocity cap (fps) — anything above this is a tracking artefact ───────────
MAX_PLAUSIBLE_VELOCITY_FPS: float = 20.0   # FRC robots top out ~18 fps

# ── Confidence thresholds ─────────────────────────────────────────────────────
HIGH_CONFIDENCE_TRACK_MIN = 20    # frames needed for HIGH confidence
LOW_CONFIDENCE_TRACK_MAX = 5      # below this → LOW


# ── Scoring zone definitions (field feet) ─────────────────────────────────────
# Each zone is a bounding rectangle (x_min, x_max, y_min, y_max).
# These approximate FRC 2024 Crescendo; update per season.

SCORING_ZONES: list[dict[str, Any]] = [
    # Blue speaker area (near Blue-Near corner)
    {"name": "blue_speaker", "x_min": 0.0,  "x_max": 8.0,  "y_min": 4.0,  "y_max": 8.5,  "pts": 2},
    # Red speaker area (near Red-Near corner)
    {"name": "red_speaker",  "x_min": 46.0, "x_max": 54.0, "y_min": 4.0,  "y_max": 8.5,  "pts": 2},
    # Blue amp
    {"name": "blue_amp",     "x_min": 0.0,  "x_max": 4.0,  "y_min": 21.5, "y_max": 27.0, "pts": 1},
    # Red amp
    {"name": "red_amp",      "x_min": 50.0, "x_max": 54.0, "y_min": 21.5, "y_max": 27.0, "pts": 1},
    # Stage (centre, both alliances fight here in endgame)
    {"name": "stage",        "x_min": 17.0, "x_max": 37.0, "y_min": 8.0,  "y_max": 19.0, "pts": 0},
]


# ── Protocol / duck-type for a single track row ───────────────────────────────

class TrackRow(Protocol):
    match_id: int
    team_id: int | None
    timestamp_ms: int
    field_x: float | None
    field_y: float | None
    flagged_for_review: bool


# ── Output dataclass ──────────────────────────────────────────────────────────

@dataclass
class PhaseStatResult:
    match_id: int
    team_id: int
    phase: str                          # "auto" | "teleop" | "endgame"
    distance_traveled_ft: float = 0.0
    avg_velocity_fps: float = 0.0
    max_velocity_fps: float = 0.0
    time_in_scoring_zone_s: float = 0.0
    estimated_score: float = 0.0
    actions_detected: list[str] = field(default_factory=list)
    track_count: int = 0
    data_confidence: str = "high"       # "high" | "medium" | "low"


# ── Phase segmentation ────────────────────────────────────────────────────────

def _phase_for_ms(ts_ms: int) -> str:
    if ts_ms <= AUTO_END_MS:
        return "auto"
    if ts_ms <= TELEOP_END_MS:
        return "teleop"
    return "endgame"


# ── Zone helpers ──────────────────────────────────────────────────────────────

def _in_any_scoring_zone(x: float, y: float) -> tuple[bool, float]:
    """Return (in_zone, zone_pts) for the first matching zone."""
    for z in SCORING_ZONES:
        if z["x_min"] <= x <= z["x_max"] and z["y_min"] <= y <= z["y_max"]:
            return True, float(z["pts"])
    return False, 0.0


# ── Kinematics ────────────────────────────────────────────────────────────────

def _euclidean(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


# ── Core computation ──────────────────────────────────────────────────────────

def compute_phase_stats(
    match_id: int,
    tracks: Sequence[Any],
) -> list[PhaseStatResult]:
    """
    Aggregate MovementTrack rows into PhaseStatResult records.

    Parameters
    ----------
    match_id:
        The match these tracks belong to.
    tracks:
        Iterable of objects with fields matching the TrackRow protocol.
        May be MovementTrackCreate DTOs or ORM instances.

    Returns
    -------
    list[PhaseStatResult]
        One record per (team_id, phase) combination that has at least
        one data point.  Teams with no tracks return nothing.
    """
    # Group rows by (team_id, phase) ─────────────────────────────────────────
    # key = (team_id, phase_str)
    grouped: dict[tuple[int, str], list[Any]] = {}

    for row in tracks:
        tid = row.team_id
        if tid is None:
            continue  # unidentified robot — skip

        phase = _phase_for_ms(row.timestamp_ms)
        key = (tid, phase)
        grouped.setdefault(key, []).append(row)

    results: list[PhaseStatResult] = []

    for (team_id, phase), rows in grouped.items():
        # Sort by timestamp to get ordered trajectory
        rows_sorted = sorted(rows, key=lambda r: r.timestamp_ms)

        # Filter to rows that have valid field coordinates
        coord_rows = [
            r for r in rows_sorted
            if r.field_x is not None and r.field_y is not None
        ]

        stat = PhaseStatResult(
            match_id=match_id,
            team_id=team_id,
            phase=phase,
            track_count=len(rows_sorted),
        )

        # ── Confidence ────────────────────────────────────────────────────────
        n = len(coord_rows)
        if n >= HIGH_CONFIDENCE_TRACK_MIN:
            stat.data_confidence = "high"
        elif n >= LOW_CONFIDENCE_TRACK_MAX:
            stat.data_confidence = "medium"
        else:
            stat.data_confidence = "low"

        if n == 0:
            # No usable coordinates — return zero stats with low confidence
            stat.data_confidence = "low"
            results.append(stat)
            continue

        # ── Kinematics ────────────────────────────────────────────────────────
        total_distance = 0.0
        velocities: list[float] = []
        zone_time_s = 0.0
        score_estimate = 0.0
        prev_in_zone = False

        for i in range(1, len(coord_rows)):
            prev = coord_rows[i - 1]
            curr = coord_rows[i]

            dt_s = (curr.timestamp_ms - prev.timestamp_ms) / 1000.0
            if dt_s <= 0:
                continue

            dist = _euclidean(prev.field_x, prev.field_y, curr.field_x, curr.field_y)

            # Clamp implausible jumps (tracking glitches)
            velocity_fps = dist / dt_s
            if velocity_fps > MAX_PLAUSIBLE_VELOCITY_FPS:
                # Treat as interpolation gap — skip distance, still track position
                continue

            total_distance += dist
            velocities.append(velocity_fps)

            # Zone time — if current position is in a scoring zone
            in_zone, zone_pts = _in_any_scoring_zone(curr.field_x, curr.field_y)
            if in_zone:
                zone_time_s += dt_s
                # Estimate score: 1 pt per ~3 s in scoring zone (heuristic)
                score_estimate += zone_pts * (dt_s / 3.0)

            prev_in_zone = in_zone

        stat.distance_traveled_ft = round(total_distance, 3)
        stat.avg_velocity_fps = round(sum(velocities) / len(velocities), 3) if velocities else 0.0
        stat.max_velocity_fps = round(max(velocities), 3) if velocities else 0.0
        stat.time_in_scoring_zone_s = round(zone_time_s, 2)
        stat.estimated_score = round(score_estimate, 2)

        # ── Action heuristics (lightweight, no vision required) ───────────────
        actions: list[str] = []

        if stat.time_in_scoring_zone_s > 2.0:
            actions.append("approached_scoring_zone")

        if phase == "endgame" and stat.time_in_scoring_zone_s > 5.0:
            actions.append("possible_climb_attempt")

        if stat.distance_traveled_ft < 3.0 and stat.track_count > 10:
            actions.append("stationary_or_disabled")
        elif stat.distance_traveled_ft > 80.0:
            actions.append("high_mobility")

        stat.actions_detected = actions
        results.append(stat)

    return results