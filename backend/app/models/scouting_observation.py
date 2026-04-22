from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class ScoutingObservation(Base):
	__tablename__ = "scouting_observation"
	__table_args__ = (
		CheckConstraint("rating BETWEEN 1 AND 5", name="ck_scouting_observation_rating"),
		Index("idx_scouting_observation_team_match", "team_id", "match_id"),
	)

	observation_id: Mapped[int] = mapped_column(primary_key=True)
	team_id: Mapped[int] = mapped_column(ForeignKey("team.team_id", ondelete="RESTRICT"), nullable=False)
	match_id: Mapped[int] = mapped_column(ForeignKey("match.match_id", ondelete="RESTRICT"), nullable=False)
	scout_id: Mapped[int] = mapped_column(ForeignKey("user.user_id", ondelete="RESTRICT"), nullable=False, index=True)
	notes: Mapped[str | None] = mapped_column(Text, nullable=True)
	rating: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
	actions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
	submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

	team = relationship("Team", back_populates="scouting_observations")
	match = relationship("Match", back_populates="scouting_observations")
	scout = relationship("User", back_populates="scouting_observations")
