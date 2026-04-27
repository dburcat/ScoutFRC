from sqlalchemy import ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from .base import Base


class UserAlliance(Base):
    __tablename__ = "user_alliance"

    alliance_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.user_id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    red_teams: Mapped[str] = mapped_column(String(255))  # Comma-separated team IDs: "1234,4567,7890"
    blue_teams: Mapped[str] = mapped_column(String(255))  # Comma-separated team IDs: "2345,5678,8901"
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    user = relationship("User", back_populates="user_alliances")
