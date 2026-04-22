from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, desc, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class SyncLog(Base):
	__tablename__ = "sync_log"
	__table_args__ = (
		Index("idx_sync_log_type_resource", "sync_type", "resource_id"),
		Index("idx_sync_log_timestamp_desc", desc("sync_timestamp")),
	)

	sync_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
	sync_type: Mapped[str] = mapped_column(String(30))
	resource_id: Mapped[str] = mapped_column(String(50))
	status: Mapped[str] = mapped_column(String(20), default="success")
	records_created: Mapped[int] = mapped_column(Integer, default=0)
	records_updated: Mapped[int] = mapped_column(Integer, default=0)
	old_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
	new_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
	error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
	sync_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	triggered_by: Mapped[int | None] = mapped_column(ForeignKey("user.user_id", ondelete="SET NULL"), nullable=True)

	trigger_user = relationship("User", back_populates="sync_logs")
