from datetime import datetime

from sqlalchemy import DateTime, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Team(Base):
    __tablename__ = "team"

    team_id: Mapped[int] = mapped_column(primary_key=True)
    team_number: Mapped[int] = mapped_column(SmallInteger, unique=True, index=True)
    team_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    school_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state_prov: Mapped[str | None] = mapped_column(String(60), nullable=True)
    country: Mapped[str | None] = mapped_column(String(60), nullable=True)
    rookie_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    robot_performances = relationship("RobotPerformance", back_populates="team")
    scouting_observations = relationship("ScoutingObservation", back_populates="team")
    users = relationship("User", back_populates="team")