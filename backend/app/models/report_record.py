"""
report_record.py
================
ORM model for persisting report metadata.
One row per generated report (versioned — old reports retained).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ReportRecord(Base):
    __tablename__ = "report_record"
    __table_args__ = (
        Index("idx_rr_event_id", "event_id"),
        Index("idx_rr_report_id", "report_id"),
        Index("idx_rr_generated_at", "generated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    event_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_at: Mapped[str] = mapped_column(String(32), nullable=False)
    formats: Mapped[list] = mapped_column(JSON, nullable=False)
    files: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )