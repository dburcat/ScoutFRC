from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Alliance(Base):
    __tablename__ = "alliance"
    __table_args__ = (
        UniqueConstraint("match_id", "color", name="uq_alliance_match_color"),
        CheckConstraint("color in ('red', 'blue')", name="ck_alliance_color"),
    )

    alliance_id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("match.match_id", ondelete="CASCADE"), index=True)
    color: Mapped[str] = mapped_column(String(4))
    total_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    rp_earned: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    won: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    match = relationship("Match", back_populates="alliances")
    robot_performances = relationship("RobotPerformance", back_populates="alliance", cascade="all, delete-orphan")
