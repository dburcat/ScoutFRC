"""
reports.py
==========
Phase 2 Tier 6 — Report Generation & Distribution

Endpoints
---------
POST /reports/generate
    Trigger async report generation for an event.
    Returns task_id for polling.

GET  /reports
    List all generated reports, optionally filtered by event_id.

GET  /reports/{report_id}/download/{format}
    Download a specific report file (pdf, csv, or json).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.routers.deps import get_current_user
from app.models.user import User

reports_router = APIRouter(prefix="/reports", tags=["reports"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    event_id: int
    formats: list[str] = ["pdf", "csv", "json"]
    email_to: list[str] = []


class ReportFileRead(BaseModel):
    format: str
    filename: str
    size_bytes: int
    checksum: str | None = None


class ReportRecordRead(BaseModel):
    id: int
    report_id: str
    event_id: int
    event_name: str
    generated_at: str
    formats: list[str]
    files: list[ReportFileRead]

    model_config = {"from_attributes": True}


class GenerateResponse(BaseModel):
    task_id: str
    event_id: int
    status: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@reports_router.post(
    "/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger async report generation for an event",
)
def generate_report(
    body: GenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dispatch the export_reports Celery task.
    Returns task_id for polling via GET /tasks/{id}/status.
    """
    from app.tasks.report_tasks import export_reports

    valid_formats = {"pdf", "csv", "json"}
    invalid = set(body.formats) - valid_formats
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid formats: {invalid}. Must be one of {valid_formats}",
        )

    result = export_reports.apply_async(  # type: ignore[union-attr]
        kwargs={
            "event_id": body.event_id,
            "formats": body.formats,
            "email_to": body.email_to or None,
        },
        queue="reports",
    )

    return GenerateResponse(
        task_id=result.id,
        event_id=body.event_id,
        status="queued",
    )


@reports_router.get(
    "/",
    response_model=list[ReportRecordRead],
    summary="List generated reports",
)
def list_reports(
    event_id: int | None = Query(None, description="Filter by event ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.report_record import ReportRecord

    q = db.query(ReportRecord).order_by(ReportRecord.created_at.desc())
    if event_id is not None:
        q = q.filter(ReportRecord.event_id == event_id)
    records = q.offset(skip).limit(limit).all()

    return [
        ReportRecordRead(
            id=r.id,
            report_id=r.report_id,
            event_id=r.event_id,
            event_name=r.event_name,
            generated_at=r.generated_at,
            formats=r.formats,
            files=[ReportFileRead(**f) for f in (r.files or [])],
        )
        for r in records
    ]


@reports_router.get(
    "/{report_id}/download/{fmt}",
    summary="Download a report file",
)
def download_report(
    report_id: str,
    fmt: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Download a specific report file by report_id and format.
    Reads from the configured storage backend.
    """
    from app.models.report_record import ReportRecord
    from app.services.report_generator import get_storage

    record = db.query(ReportRecord).filter(
        ReportRecord.report_id == report_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Report not found")

    file_meta = next(
        (f for f in (record.files or []) if f.get("format") == fmt), None
    )
    if not file_meta:
        raise HTTPException(
            status_code=404,
            detail=f"Format '{fmt}' not available for this report",
        )

    try:
        storage = get_storage()
        data = storage.read(file_meta["storage_key"])
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to retrieve report file: {exc}",
        )

    mime_map = {
        "pdf": "application/pdf",
        "csv": "text/csv",
        "json": "application/json",
    }
    media_type = mime_map.get(fmt, "application/octet-stream")

    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{file_meta["filename"]}"',
            "Content-Length": str(len(data)),
        },
    )