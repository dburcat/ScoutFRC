"""
report_tasks.py
===============
Phase 2 Tier 6 — Report Generation & Distribution

Celery task: export_reports
  Accepts event_id, formats, and optional email_to list.
  Persists report metadata to the DB after generation.
"""

from __future__ import annotations

import logging
from typing import cast

from celery import Task

from app.celery_app import celery_app
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def _persist_report_meta(db, meta) -> int:
    """
    Persist a ReportRecord to the database.
    Returns the new record's ID.
    """
    from app.models.report_record import ReportRecord

    record = ReportRecord(
        report_id=meta.report_id,
        event_id=meta.event_id,
        event_name=meta.event_name,
        generated_at=meta.generated_at,
        formats=meta.formats,
        files=[
            {
                "format": f.format,
                "filename": f.filename,
                "storage_key": f.storage_key,
                "size_bytes": f.size_bytes,
                "checksum": f.checksum,
            }
            for f in meta.files
        ],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record.id


def run_export(
    event_id: int,
    formats: list[str] | None = None,
    email_to: list[str] | None = None,
) -> dict:
    """Core logic — separated so tests can call directly without Celery."""
    from app.services.report_generator import ReportGenerator

    with SessionLocal() as db:
        gen = ReportGenerator(db)
        meta = gen.generate(event_id=event_id, formats=formats, email_to=email_to)
        record_id = _persist_report_meta(db, meta)

    return {
        "report_id": meta.report_id,
        "record_id": record_id,
        "event_id": meta.event_id,
        "formats_generated": [f.format for f in meta.files],
        "files": [
            {
                "format": f.format,
                "filename": f.filename,
                "size_bytes": f.size_bytes,
            }
            for f in meta.files
        ],
        "status": "complete" if meta.files else "no_data",
    }


@celery_app.task(
    bind=True,
    name="report_tasks.export_reports",
    queue="reports",
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def _export_reports_celery(
    self: Task,
    event_id: int,
    formats: list[str] | None = None,
    email_to: list[str] | None = None,
) -> dict:
    """Celery entry-point for report generation."""
    logger.info("export_reports: starting for event %d formats=%s", event_id, formats)
    try:
        result = run_export(event_id=event_id, formats=formats, email_to=email_to)
        logger.info("export_reports: complete %s", result)
        return result
    except Exception as exc:
        logger.error("export_reports failed for event %d: %s", event_id, exc)
        raise


export_reports: Task = cast(Task, _export_reports_celery)