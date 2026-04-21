from sqlalchemy import (
	Boolean,
	CheckConstraint,
	Computed,
	ForeignKey,
	Index,
	SmallInteger,
	UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RobotPerformance(Base):
	__tablename__ = "robot_performance"
	__table_args__ = (
		UniqueConstraint("match_id", "team_id", name="uq_robot_performance_match_team"),
		CheckConstraint("alliance_position in (1, 2, 3)", name="ck_robot_performance_alliance_position"),
		Index("idx_robot_performance_team_match", "team_id", "match_id"),
	)

	perf_id: Mapped[int] = mapped_column(primary_key=True)
	match_id: Mapped[int] = mapped_column(ForeignKey("match.match_id", ondelete="CASCADE"), index=True)
	team_id: Mapped[int] = mapped_column(ForeignKey("team.team_id", ondelete="RESTRICT"), index=True)
	alliance_id: Mapped[int] = mapped_column(ForeignKey("alliance.alliance_id", ondelete="CASCADE"), index=True)
	alliance_position: Mapped[int] = mapped_column(SmallInteger)
	track_id: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
	auto_score: Mapped[int] = mapped_column(SmallInteger, default=0)
	teleop_score: Mapped[int] = mapped_column(SmallInteger, default=0)
	endgame_score: Mapped[int] = mapped_column(SmallInteger, default=0)
	total_score_contribution: Mapped[int] = mapped_column(
		SmallInteger,
		Computed("auto_score + teleop_score + endgame_score", persisted=True),
	)
	fouls_drawn: Mapped[int] = mapped_column(SmallInteger, default=0)
	fouls_committed: Mapped[int] = mapped_column(SmallInteger, default=0)
	no_show: Mapped[bool] = mapped_column(Boolean, default=False)
	disabled: Mapped[bool] = mapped_column(Boolean, default=False)

	team = relationship("Team", back_populates="robot_performances")
	match = relationship("Match", back_populates="robot_performances")
	alliance = relationship("Alliance", back_populates="robot_performances")
