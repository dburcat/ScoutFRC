from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class EventCameraCalibration(Base):
    __tablename__ = "event_camera_calibration"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("event.event_id", ondelete="CASCADE"), nullable=False
    )
    # e.g. "overhead_center", "red_alliance_wall", "blue_alliance_wall"
    camera_position: Mapped[str] = mapped_column(String(64), nullable=False)
    # 3×3 perspective transformation matrix stored as nested list
    perspective_matrix: Mapped[list] = mapped_column(JSON, nullable=False)
    calibrated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    calibrated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    event = relationship("Event", back_populates="camera_calibrations")