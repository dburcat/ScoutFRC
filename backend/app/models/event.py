from datetime import date, datetime

from sqlalchemy import Date, DateTime, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Event(Base):
    __tablename__ = "event"

    event_id: Mapped[int] = mapped_column(primary_key=True)
    tba_event_key: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state_prov: Mapped[str | None] = mapped_column(String(60), nullable=True)
    country: Mapped[str | None] = mapped_column(String(60), nullable=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    season_year: Mapped[int] = mapped_column(SmallInteger, index=True)
    perspective_matrix: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    matches = relationship("Match", back_populates="event")
    camera_calibrations = relationship("EventCameraCalibration", back_populates="event", cascade="all, delete-orphan")