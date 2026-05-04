"""
report_generator.py
===================
Phase 2 Tier 6 — Report Generation & Distribution

Generates scouting reports in three formats:
  - PDF  (ReportLab — event summary, rankings table, per-team stats)
  - CSV  (pandas — flat table: team/match/phase/metric columns)
  - JSON (structured hierarchy: event → teams → matches → stats)

Object storage abstraction allows switching between local filesystem
and S3-compatible storage via REPORT_STORAGE_BACKEND env var.

Usage
-----
    from app.services.report_generator import ReportGenerator
    gen = ReportGenerator(db)
    meta = gen.generate(event_id=42, formats=["pdf", "csv", "json"])
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Storage config ────────────────────────────────────────────────────────────
STORAGE_BACKEND: str = os.getenv("REPORT_STORAGE_BACKEND", "local")
LOCAL_STORAGE_PATH: Path = Path(os.getenv("REPORT_LOCAL_PATH", "/tmp/scouterfrc_reports"))
S3_BUCKET: str = os.getenv("REPORT_S3_BUCKET", "scouterfrc-reports")
S3_PREFIX: str = os.getenv("REPORT_S3_PREFIX", "reports/")


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class ReportFile:
    format: str          # "pdf" | "csv" | "json"
    filename: str
    storage_key: str     # local path or S3 key
    size_bytes: int
    checksum: str


@dataclass
class ReportMeta:
    report_id: str
    event_id: int
    event_name: str
    generated_at: str
    formats: list[str]
    files: list[ReportFile] = field(default_factory=list)


# ── Storage layer ─────────────────────────────────────────────────────────────

class StorageBackend:
    """Abstract storage — write bytes, return storage key."""

    def write(self, key: str, data: bytes) -> str:
        raise NotImplementedError

    def read(self, key: str) -> bytes:
        raise NotImplementedError

    def list_prefix(self, prefix: str) -> list[str]:
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_path: Path = LOCAL_STORAGE_PATH):
        self.base = base_path
        self.base.mkdir(parents=True, exist_ok=True)

    def write(self, key: str, data: bytes) -> str:
        dest = self.base / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return str(dest)

    def read(self, key: str) -> bytes:
        return (self.base / key).read_bytes()

    def list_prefix(self, prefix: str) -> list[str]:
        return [
            str(p.relative_to(self.base))
            for p in self.base.rglob("*")
            if p.is_file() and str(p.relative_to(self.base)).startswith(prefix)
        ]


class S3StorageBackend(StorageBackend):
    def __init__(self):
        import boto3
        self._s3 = boto3.client("s3")

    def write(self, key: str, data: bytes) -> str:
        full_key = f"{S3_PREFIX}{key}"
        self._s3.put_object(Bucket=S3_BUCKET, Key=full_key, Body=data)
        return full_key

    def read(self, key: str) -> bytes:
        resp = self._s3.get_object(Bucket=S3_BUCKET, Key=key)
        return resp["Body"].read()

    def list_prefix(self, prefix: str) -> list[str]:
        resp = self._s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=f"{S3_PREFIX}{prefix}")
        return [obj["Key"] for obj in resp.get("Contents", [])]


def get_storage() -> StorageBackend:
    if STORAGE_BACKEND == "s3":
        return S3StorageBackend()
    return LocalStorageBackend()


# ── Data fetcher ──────────────────────────────────────────────────────────────

def _fetch_report_data(db, event_id: int) -> dict:
    """
    Query all data needed for the report in one place.
    Returns a dict with event, rankings, and team_stats.
    """
    from sqlalchemy import func
    from app.models.event import Event
    from app.models.match import Match
    from app.models.team import Team
    from app.models.phase_stat import PhaseStat

    event = db.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        raise ValueError(f"Event {event_id} not found")

    # Rankings: aggregate phase stats across matches in this event
    rows = (
        db.query(
            PhaseStat.team_id,
            func.sum(PhaseStat.estimated_score).label("total_score"),
            func.avg(PhaseStat.avg_velocity_fps).label("avg_velocity"),
            func.avg(PhaseStat.distance_traveled_ft).label("avg_distance"),
            func.count(PhaseStat.match_id.distinct()).label("matches_played"),
        )
        .join(Match, Match.match_id == PhaseStat.match_id)
        .filter(Match.event_id == event_id)
        .group_by(PhaseStat.team_id)
        .order_by(func.sum(PhaseStat.estimated_score).desc())
        .all()
    )

    rankings = []
    team_stats: dict[int, list[dict]] = {}

    for rank, row in enumerate(rows, start=1):
        team = db.query(Team).filter(Team.team_id == row.team_id).first()
        entry = {
            "rank": rank,
            "team_id": row.team_id,
            "team_number": team.team_number if team else row.team_id,
            "team_name": (team.team_name or f"Team {team.team_number}") if team else str(row.team_id),
            "total_score": round(float(row.total_score or 0), 2),
            "avg_velocity_fps": round(float(row.avg_velocity or 0), 2),
            "avg_distance_ft": round(float(row.avg_distance or 0), 2),
            "matches_played": row.matches_played,
        }
        rankings.append(entry)

        # Per-team phase breakdown
        phase_rows = (
            db.query(PhaseStat)
            .join(Match, Match.match_id == PhaseStat.match_id)
            .filter(Match.event_id == event_id, PhaseStat.team_id == row.team_id)
            .all()
        )
        team_stats[row.team_id] = [
            {
                "match_id": ps.match_id,
                "phase": ps.phase,
                "distance_traveled_ft": ps.distance_traveled_ft,
                "avg_velocity_fps": ps.avg_velocity_fps,
                "estimated_score": ps.estimated_score,
                "time_in_scoring_zone_s": ps.time_in_scoring_zone_s,
                "actions_detected": ps.actions_detected or [],
                "data_confidence": ps.data_confidence,
            }
            for ps in phase_rows
        ]

    return {
        "event": {
            "event_id": event.event_id,
            "name": event.name,
            "tba_event_key": event.tba_event_key,
            "season_year": event.season_year,
            "start_date": str(event.start_date) if event.start_date else None,
            "end_date": str(event.end_date) if event.end_date else None,
        },
        "rankings": rankings,
        "team_stats": team_stats,
    }


# ── PDF generator ─────────────────────────────────────────────────────────────

def generate_pdf(data: dict) -> bytes:
    """Generate a PDF scouting report using ReportLab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, HRFlowable,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story = []

    # ── Title ─────────────────────────────────────────────────────────────────
    title_style = ParagraphStyle("Title", parent=styles["Title"],
                                 fontSize=20, spaceAfter=6)
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"],
                               fontSize=11, textColor=colors.grey, spaceAfter=12)

    event = data["event"]
    story.append(Paragraph(f"ScouterFRC Scouting Report", title_style))
    story.append(Paragraph(
        f"{event['name']} &bull; {event.get('start_date', '')} – {event.get('end_date', '')}",
        sub_style,
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a56db")))
    story.append(Spacer(1, 0.2*inch))

    # ── Summary box ───────────────────────────────────────────────────────────
    rankings = data["rankings"]
    summary_data = [
        ["Teams Ranked", "Total Matches", "Top Team", "Top Score"],
        [
            str(len(rankings)),
            str(sum(r["matches_played"] for r in rankings)),
            rankings[0]["team_name"] if rankings else "—",
            str(rankings[0]["total_score"]) if rankings else "—",
        ],
    ]
    summary_table = Table(summary_data, colWidths=[1.5*inch]*4)
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a56db")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))

    # ── Rankings table ────────────────────────────────────────────────────────
    story.append(Paragraph("Team Rankings", styles["Heading2"]))
    story.append(Spacer(1, 0.1*inch))

    headers = ["Rank", "Team #", "Team Name", "Score", "Matches", "Avg Vel (fps)", "Avg Dist (ft)"]
    table_data = [headers]
    for r in rankings:
        table_data.append([
            str(r["rank"]),
            str(r["team_number"]),
            r["team_name"][:28],
            str(r["total_score"]),
            str(r["matches_played"]),
            str(r["avg_velocity_fps"]),
            str(r["avg_distance_ft"]),
        ])

    col_widths = [0.5*inch, 0.65*inch, 2.2*inch, 0.7*inch, 0.7*inch, 0.9*inch, 0.9*inch]
    rank_table = Table(table_data, colWidths=col_widths)
    rank_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#374151")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (2, 1), (2, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#fef3c7")),  # highlight top team
    ]))
    story.append(rank_table)
    story.append(Spacer(1, 0.3*inch))

    # ── Alliance recommendation ───────────────────────────────────────────────
    story.append(Paragraph("Alliance Recommendations", styles["Heading2"]))
    story.append(Spacer(1, 0.1*inch))

    if len(rankings) >= 3:
        rec_text = (
            f"Based on estimated scores, the recommended first-pick alliance captains are: "
            f"<b>{rankings[0]['team_name']} (#{rankings[0]['team_number']})</b>, "
            f"<b>{rankings[1]['team_name']} (#{rankings[1]['team_number']})</b>, and "
            f"<b>{rankings[2]['team_name']} (#{rankings[2]['team_number']})</b>."
        )
    elif rankings:
        rec_text = f"Insufficient data for full alliance recommendation. Top team: {rankings[0]['team_name']}."
    else:
        rec_text = "No performance data available for this event."

    story.append(Paragraph(rec_text, styles["Normal"]))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph(
        "<i>Note: Recommendations are based on estimated scores from movement tracking. "
        "Manual review is recommended before finalizing alliance selections.</i>",
        ParagraphStyle("Note", parent=styles["Normal"], fontSize=8,
                       textColor=colors.grey, italics=True),
    ))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.4*inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d1d5db")))
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph(
        f"Generated by ScouterFRC &bull; {generated_at}",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8,
                       textColor=colors.grey, alignment=1),
    ))

    doc.build(story)
    return buf.getvalue()


# ── CSV generator ─────────────────────────────────────────────────────────────

def generate_csv(data: dict) -> bytes:
    """Generate a flat CSV: one row per (team, match, phase)."""
    import pandas as pd

    rows = []
    event = data["event"]

    for team_id, phases in data["team_stats"].items():
        # Find team info from rankings
        ranking = next((r for r in data["rankings"] if r["team_id"] == team_id), None)
        team_number = ranking["team_number"] if ranking else team_id
        team_name = ranking["team_name"] if ranking else str(team_id)

        for ps in phases:
            rows.append({
                "event_id": event["event_id"],
                "event_name": event["name"],
                "tba_event_key": event["tba_event_key"],
                "team_id": team_id,
                "team_number": team_number,
                "team_name": team_name,
                "match_id": ps["match_id"],
                "phase": ps["phase"],
                "distance_traveled_ft": ps["distance_traveled_ft"],
                "avg_velocity_fps": ps["avg_velocity_fps"],
                "estimated_score": ps["estimated_score"],
                "time_in_scoring_zone_s": ps["time_in_scoring_zone_s"],
                "actions_detected": "|".join(ps.get("actions_detected") or []),
                "data_confidence": ps["data_confidence"],
            })

    if not rows:
        # Return header-only CSV when no data
        headers = [
            "event_id", "event_name", "tba_event_key", "team_id", "team_number",
            "team_name", "match_id", "phase", "distance_traveled_ft",
            "avg_velocity_fps", "estimated_score", "time_in_scoring_zone_s",
            "actions_detected", "data_confidence",
        ]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers)
        writer.writeheader()
        return buf.getvalue().encode("utf-8")

    df = pd.DataFrame(rows)
    df = df.sort_values(["team_number", "match_id", "phase"])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


# ── JSON generator ────────────────────────────────────────────────────────────

def generate_json(data: dict) -> bytes:
    """
    Generate structured JSON: event → teams → matches → phase stats.
    """
    event = data["event"]
    teams_out = []

    for ranking in data["rankings"]:
        tid = ranking["team_id"]
        phases = data["team_stats"].get(tid, [])

        # Group phases by match
        matches: dict[int, list] = {}
        for ps in phases:
            matches.setdefault(ps["match_id"], []).append(ps)

        teams_out.append({
            "team_id": tid,
            "team_number": ranking["team_number"],
            "team_name": ranking["team_name"],
            "rank": ranking["rank"],
            "summary": {
                "total_score": ranking["total_score"],
                "avg_velocity_fps": ranking["avg_velocity_fps"],
                "avg_distance_ft": ranking["avg_distance_ft"],
                "matches_played": ranking["matches_played"],
            },
            "matches": [
                {
                    "match_id": mid,
                    "phases": sorted(phase_list, key=lambda p: p["phase"]),
                }
                for mid, phase_list in sorted(matches.items())
            ],
        })

    output = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "teams": teams_out,
    }
    return json.dumps(output, indent=2, default=str).encode("utf-8")


# ── Email distribution ────────────────────────────────────────────────────────

def send_report_email(
    to_addresses: list[str],
    event_name: str,
    report_files: list[ReportFile],
    storage: StorageBackend,
) -> bool:
    """
    Send report email with attachments via SMTP.
    Configure via env vars:
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
      REPORT_FROM_EMAIL, SMTP_USE_TLS
    """
    import smtplib
    from email.message import EmailMessage

    smtp_host = os.getenv("SMTP_HOST", "localhost")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")
    from_email = os.getenv("REPORT_FROM_EMAIL", "reports@scouterfrc.local")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    msg = EmailMessage()
    msg["Subject"] = f"ScouterFRC Report — {event_name}"
    msg["From"] = from_email
    msg["To"] = ", ".join(to_addresses)
    msg.set_content(
        f"Please find attached the ScouterFRC scouting report for {event_name}.\n\n"
        f"Reports generated: {', '.join(f.format.upper() for f in report_files)}\n\n"
        f"— ScouterFRC"
    )

    for rf in report_files:
        try:
            data = storage.read(rf.storage_key)
            mime_map = {
                "pdf": ("application", "pdf"),
                "csv": ("text", "csv"),
                "json": ("application", "json"),
            }
            maintype, subtype = mime_map.get(rf.format, ("application", "octet-stream"))
            msg.add_attachment(data, maintype=maintype, subtype=subtype,
                               filename=rf.filename)
        except Exception as exc:
            logger.warning("Failed to attach %s: %s", rf.filename, exc)

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if use_tls:
                server.starttls()
            if smtp_user:
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        logger.info("Report email sent to %s", to_addresses)
        return True
    except Exception as exc:
        logger.error("Failed to send report email: %s", exc)
        return False


# ── Main generator class ──────────────────────────────────────────────────────

class ReportGenerator:
    """
    Orchestrates report generation across formats.

    Usage
    -----
    gen = ReportGenerator(db)
    meta = gen.generate(event_id=42, formats=["pdf", "csv", "json"])
    """

    def __init__(self, db, storage: StorageBackend | None = None):
        self.db = db
        self.storage = storage or get_storage()

    def generate(
        self,
        event_id: int,
        formats: list[str] | None = None,
        email_to: list[str] | None = None,
    ) -> ReportMeta:
        formats = formats or ["pdf", "csv", "json"]
        report_id = str(uuid.uuid4())
        data = _fetch_report_data(self.db, event_id)

        meta = ReportMeta(
            report_id=report_id,
            event_id=event_id,
            event_name=data["event"]["name"],
            generated_at=datetime.now(timezone.utc).isoformat(),
            formats=formats,
        )

        generators = {
            "pdf": (generate_pdf, "application/pdf"),
            "csv": (generate_csv, "text/csv"),
            "json": (generate_json, "application/json"),
        }

        for fmt in formats:
            if fmt not in generators:
                logger.warning("Unknown report format: %s", fmt)
                continue

            gen_fn, _ = generators[fmt]
            try:
                content = gen_fn(data)
                filename = f"report_{data['event']['tba_event_key']}_{report_id[:8]}.{fmt}"
                storage_key = f"{event_id}/{report_id}/{filename}"

                stored_path = self.storage.write(storage_key, content)

                import hashlib
                checksum = hashlib.md5(content).hexdigest()

                meta.files.append(ReportFile(
                    format=fmt,
                    filename=filename,
                    storage_key=stored_path,
                    size_bytes=len(content),
                    checksum=checksum,
                ))
                logger.info("Generated %s report: %s (%d bytes)", fmt, filename, len(content))

            except Exception as exc:
                logger.error("Failed to generate %s report for event %d: %s", fmt, event_id, exc)

        if email_to and meta.files:
            send_report_email(email_to, data["event"]["name"], meta.files, self.storage)

        return meta