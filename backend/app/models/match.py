from datetime import datetime

from sqlalchemy import (
	CheckConstraint,
	DateTime,
	ForeignKey,
	Index,
	SmallInteger,
	String,
	Text,
	func,
	text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Match(Base):
	__tablename__ = "match"
	__table_args__ = (
		CheckConstraint(
			"match_type in ('qualification', 'semifinal', 'final')",
			name="ck_match_match_type",
		),
		CheckConstraint(
			"processing_status in ('pending', 'processing', 'complete', 'failed')",
			name="ck_match_processing_status",
		),
		Index("idx_match_event_schedule", "event_id", "match_type", "match_number"),
		Index(
			"idx_match_processing_status",
			"processing_status",
			postgresql_where=text("processing_status != 'complete'"),
		),
	)

	match_id: Mapped[int] = mapped_column(primary_key=True)
	event_id: Mapped[int] = mapped_column(ForeignKey("event.event_id", ondelete="RESTRICT"), nullable=False)
	tba_match_key: Mapped[str] = mapped_column(String(30), unique=True, index=True)
	match_type: Mapped[str] = mapped_column(String(15))
	match_number: Mapped[int] = mapped_column(SmallInteger)
	video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
	video_s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
	processing_status: Mapped[str] = mapped_column(String(20), default="pending")
	played_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	event = relationship("Event", back_populates="matches")
	alliances = relationship("Alliance", back_populates="match", cascade="all, delete-orphan")
	robot_performances = relationship("RobotPerformance", back_populates="match", cascade="all, delete-orphan")
	scouting_observations = relationship("ScoutingObservation", back_populates="match")
