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
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class IdentificationMethod(str, enum.Enum):
    OCR = "OCR"
    OCR_POST_CONFIG_CHANGE = "OCR_post_config_change"
    OCR_MULTI_FRAME_VOTE = "OCR_MultiFrameVote"
    DEEPSORT = "DeepSORT"
    COLOR = "Color"
    COLOR_POST_CONFIG_CHANGE = "Color_post_config_change"
    SPATIAL = "Spatial"
    TRACK_CONTINUITY_POST_CONFIG = "TrackContinuity_post_config_change"
    KALMAN = "Kalman"
    UNKNOWN = "UNKNOWN"


class MovementTrack(Base):
    __tablename__ = "movement_track"
    __table_args__ = (
        Index("idx_mt_match_id", "match_id"),
        Index("idx_mt_team_id", "team_id"),
        Index("idx_mt_flagged", "flagged_for_review"),
        Index("idx_mt_match_frame", "match_id", "frame_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("match.match_id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("team.team_id", ondelete="SET NULL"), nullable=True
    )
    # DeepSORT internal track ID — unique per video, not globally
    track_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # ── Position ─────────────────────────────────────────────────────────────
    frame_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    pixel_x: Mapped[float] = mapped_column(Float, nullable=False)
    pixel_y: Mapped[float] = mapped_column(Float, nullable=False)
    field_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    field_y: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Bounding box ─────────────────────────────────────────────────────────
    bounding_box_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    bounding_box_height: Mapped[float | None] = mapped_column(Float, nullable=True)
    bounding_box_size_change: Mapped[float] = mapped_column(Float, default=0.0)

    # ── Identification ────────────────────────────────────────────────────────
    identification_method: Mapped[str] = mapped_column(
        String(64), default=IdentificationMethod.UNKNOWN
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    team_number_visible: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Quality flags ─────────────────────────────────────────────────────────
    interpolated: Mapped[bool] = mapped_column(Boolean, default=False)
    configuration_changed: Mapped[bool] = mapped_column(Boolean, default=False)
    flagged_for_review: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    review_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manually_corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    corrected_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("team.team_id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    match = relationship("Match", back_populates="movement_tracks")
    team = relationship("Team", foreign_keys=[team_id], back_populates="movement_tracks")
    corrected_team = relationship("Team", foreign_keys=[corrected_team_id])