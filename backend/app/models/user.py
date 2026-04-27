from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
	__tablename__ = "user"
	__table_args__ = (
		CheckConstraint(
			"role in ('SCOUT', 'COACH', 'TEAM_ADMIN', 'SYSTEM_ADMIN')",
			name="ck_user_role",
		),
	)

	user_id: Mapped[int] = mapped_column(primary_key=True)
	username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
	email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
	hashed_password: Mapped[str] = mapped_column(String(200))
	team_id: Mapped[int | None] = mapped_column(ForeignKey("team.team_id", ondelete="SET NULL"), index=True, nullable=True)
	role: Mapped[str] = mapped_column(String(20), default="SCOUT")
	is_active: Mapped[bool] = mapped_column(Boolean, default=True)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

	team = relationship("Team", back_populates="users")
	scouting_observations = relationship("ScoutingObservation", back_populates="scout")
	sync_logs = relationship("SyncLog", back_populates="trigger_user")
	user_alliances = relationship("UserAlliance", back_populates="user")
