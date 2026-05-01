"""
PhaseStat ORM model.

One row per (team, match, phase) combination, computed by the
analytics pipeline after video processing completes.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class GamePhase(str, enum.Enum):
    AUTO = "auto"
    TELEOP = "teleop"
    ENDGAME = "endgame"


class ConfidenceLevel(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PhaseStat(Base):
    """
    Aggregated movement statistics for one team, one match, one game phase.

    Fields
    ------
    phase
        auto | teleop | endgame
    distance_traveled_ft
        Total path length in field feet (summed Euclidean deltas).
    avg_velocity_fps
        Mean speed in feet/second during the phase.
    max_velocity_fps
        Peak speed observed in any inter-frame window.
    time_in_scoring_zone_s
        Seconds the robot spent inside any recognised scoring zone.
    estimated_score
        Heuristic point estimate based on zone-proximity events.
    actions_detected
        JSON array of detected game actions (e.g. ["scored_note", "climbed"]).
    track_count
        Number of confirmed MovementTrack frames used for this phase.
    data_confidence
        "high" / "medium" / "low" — reflects completeness of source data.
    """

    __tablename__ = "phase_stat"
    __table_args__ = (
        UniqueConstraint(
            "match_id", "team_id", "phase",
            name="uq_phase_stat_match_team_phase",
        ),
        Index("idx_ps_team_id", "team_id"),
        Index("idx_ps_match_id", "match_id"),
        Index("idx_ps_match_team", "match_id", "team_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    match_id: Mapped[int] = mapped_column(
        ForeignKey("match.match_id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("team.team_id", ondelete="CASCADE"), nullable=False
    )

    phase: Mapped[str] = mapped_column(String(16), nullable=False)

    # ── Kinematics ────────────────────────────────────────────────────────────
    distance_traveled_ft: Mapped[float] = mapped_column(Float, default=0.0)
    avg_velocity_fps: Mapped[float] = mapped_column(Float, default=0.0)
    max_velocity_fps: Mapped[float] = mapped_column(Float, default=0.0)

    # ── Zone analytics ────────────────────────────────────────────────────────
    time_in_scoring_zone_s: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_score: Mapped[float] = mapped_column(Float, default=0.0)

    # ── Game actions ──────────────────────────────────────────────────────────
    actions_detected: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # ── Metadata ──────────────────────────────────────────────────────────────
    track_count: Mapped[int] = mapped_column(Integer, default=0)
    data_confidence: Mapped[str] = mapped_column(
        String(16), default=ConfidenceLevel.HIGH
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    match = relationship("Match", back_populates="phase_stats")
    team = relationship("Team", back_populates="phase_stats")