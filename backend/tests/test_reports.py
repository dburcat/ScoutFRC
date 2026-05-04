"""
test_reports.py
===============
Phase 2 Tier 6 — Report Generation & Distribution

Test coverage
-------------
Unit (generators — DB mocked with fixture data)
  - generate_pdf: produces valid PDF bytes
  - generate_csv: correct headers, correct row count, handles empty data
  - generate_json: validates schema, correct structure
  - ReportGenerator.generate: all formats, storage write called, meta returned

Integration (API endpoints)
  - POST /reports/generate — queued response, invalid format 422
  - GET  /reports/         — lists records, event_id filter
  - GET  /reports/{id}/download/{fmt} — returns bytes with correct content-type
  - 404 for missing report or format
"""

from __future__ import annotations

import csv
import io
import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from app.db.session import get_db

client = TestClient(fastapi_app)


# ── Auth helper ───────────────────────────────────────────────────────────────

def _auth_header(db_session, role: str = "SCOUT") -> dict:
    from app.models.user import User
    from app.core.security import get_password_hash, create_access_token
    from datetime import timedelta
    import time

    uid = int(time.time() * 1000) % 1_000_000
    user = User(
        email=f"user{uid}@test.com",
        username=f"user{uid}",
        hashed_password=get_password_hash("pass"),
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    token = create_access_token(subject=user.user_id, expires_delta=timedelta(days=1))
    return {"Authorization": f"Bearer {token}"}


# ── Shared fixture data ───────────────────────────────────────────────────────

SAMPLE_DATA = {
    "event": {
        "event_id": 1,
        "name": "Test Regional",
        "tba_event_key": "2024test",
        "season_year": 2024,
        "start_date": "2024-03-01",
        "end_date": "2024-03-03",
    },
    "rankings": [
        {
            "rank": 1, "team_id": 1, "team_number": 254,
            "team_name": "The Cheesy Poofs",
            "total_score": 42.5, "avg_velocity_fps": 3.2,
            "avg_distance_ft": 120.0, "matches_played": 6,
        },
        {
            "rank": 2, "team_id": 2, "team_number": 1678,
            "team_name": "Citrus Circuits",
            "total_score": 38.0, "avg_velocity_fps": 2.9,
            "avg_distance_ft": 105.0, "matches_played": 6,
        },
        {
            "rank": 3, "team_id": 3, "team_number": 971,
            "team_name": "Spartan Robotics",
            "total_score": 31.0, "avg_velocity_fps": 2.5,
            "avg_distance_ft": 90.0, "matches_played": 5,
        },
    ],
    "team_stats": {
        1: [
            {"match_id": 1, "phase": "auto", "distance_traveled_ft": 25.0,
             "avg_velocity_fps": 3.0, "estimated_score": 4.0,
             "time_in_scoring_zone_s": 3.0, "actions_detected": ["high_mobility"],
             "data_confidence": "high"},
            {"match_id": 1, "phase": "teleop", "distance_traveled_ft": 80.0,
             "avg_velocity_fps": 3.5, "estimated_score": 6.0,
             "time_in_scoring_zone_s": 8.0, "actions_detected": [],
             "data_confidence": "high"},
        ],
        2: [
            {"match_id": 1, "phase": "auto", "distance_traveled_ft": 20.0,
             "avg_velocity_fps": 2.8, "estimated_score": 3.5,
             "time_in_scoring_zone_s": 2.5, "actions_detected": [],
             "data_confidence": "medium"},
        ],
        3: [],
    },
}


# ════════════════════════════════════════════════════════════════════════════
# Unit tests — PDF generator
# ════════════════════════════════════════════════════════════════════════════

from app.services.report_generator import generate_pdf, generate_csv, generate_json


class TestGeneratePDF:
    def test_returns_bytes(self):
        pytest.importorskip("reportlab", reason="reportlab not installed")
        result = generate_pdf(SAMPLE_DATA)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_starts_with_pdf_header(self):
        pytest.importorskip("reportlab", reason="reportlab not installed")
        result = generate_pdf(SAMPLE_DATA)
        assert result[:4] == b"%PDF"

    def test_non_empty_with_no_rankings(self):
        pytest.importorskip("reportlab", reason="reportlab not installed")
        data = {**SAMPLE_DATA, "rankings": [], "team_stats": {}}
        result = generate_pdf(data)
        assert result[:4] == b"%PDF"


# ════════════════════════════════════════════════════════════════════════════
# Unit tests — CSV generator
# ════════════════════════════════════════════════════════════════════════════

class TestGenerateCSV:
    def test_returns_bytes(self):
        result = generate_csv(SAMPLE_DATA)
        assert isinstance(result, bytes)

    def test_has_correct_headers(self):
        result = generate_csv(SAMPLE_DATA)
        text = result.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        expected = {
            "event_id", "event_name", "tba_event_key", "team_id", "team_number",
            "team_name", "match_id", "phase", "distance_traveled_ft",
            "avg_velocity_fps", "estimated_score", "time_in_scoring_zone_s",
            "actions_detected", "data_confidence",
        }
        assert set(reader.fieldnames or []) == expected

    def test_correct_row_count(self):
        result = generate_csv(SAMPLE_DATA)
        text = result.decode("utf-8")
        rows = list(csv.DictReader(io.StringIO(text)))
        # team 1: 2 rows, team 2: 1 row, team 3: 0 rows = 3 total
        assert len(rows) == 3

    def test_empty_data_returns_header_only(self):
        empty = {**SAMPLE_DATA, "team_stats": {}}
        result = generate_csv(empty)
        text = result.decode("utf-8")
        rows = list(csv.DictReader(io.StringIO(text)))
        assert len(rows) == 0

    def test_actions_joined_with_pipe(self):
        result = generate_csv(SAMPLE_DATA)
        text = result.decode("utf-8")
        rows = list(csv.DictReader(io.StringIO(text)))
        mobility_row = next(
            (r for r in rows if r.get("actions_detected") == "high_mobility"), None
        )
        assert mobility_row is not None


# ════════════════════════════════════════════════════════════════════════════
# Unit tests — JSON generator
# ════════════════════════════════════════════════════════════════════════════

class TestGenerateJSON:
    def test_returns_bytes(self):
        result = generate_json(SAMPLE_DATA)
        assert isinstance(result, bytes)

    def test_valid_json(self):
        result = generate_json(SAMPLE_DATA)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_schema_version_present(self):
        parsed = json.loads(generate_json(SAMPLE_DATA))
        assert parsed["schema_version"] == "1.0"

    def test_event_block_present(self):
        parsed = json.loads(generate_json(SAMPLE_DATA))
        assert "event" in parsed
        assert parsed["event"]["event_id"] == 1

    def test_teams_block_structure(self):
        parsed = json.loads(generate_json(SAMPLE_DATA))
        assert "teams" in parsed
        assert len(parsed["teams"]) == 3

        team = parsed["teams"][0]
        assert "team_id" in team
        assert "rank" in team
        assert "summary" in team
        assert "matches" in team

    def test_team_summary_fields(self):
        parsed = json.loads(generate_json(SAMPLE_DATA))
        summary = parsed["teams"][0]["summary"]
        assert "total_score" in summary
        assert "matches_played" in summary
        assert "avg_velocity_fps" in summary

    def test_generated_at_present(self):
        parsed = json.loads(generate_json(SAMPLE_DATA))
        assert "generated_at" in parsed

    def test_empty_data_still_valid(self):
        data = {**SAMPLE_DATA, "rankings": [], "team_stats": {}}
        parsed = json.loads(generate_json(data))
        assert parsed["teams"] == []


# ════════════════════════════════════════════════════════════════════════════
# Unit tests — ReportGenerator orchestration
# ════════════════════════════════════════════════════════════════════════════

from app.services.report_generator import ReportGenerator, LocalStorageBackend


class TestReportGenerator:
    def _mock_db(self):
        """Return a db mock that makes _fetch_report_data return SAMPLE_DATA."""
        return MagicMock()

    def test_generate_all_formats(self, tmp_path):
        storage = LocalStorageBackend(base_path=tmp_path)
        gen = ReportGenerator(db=MagicMock(), storage=storage)

        with patch("app.services.report_generator._fetch_report_data",
                   return_value=SAMPLE_DATA):
            meta = gen.generate(event_id=1, formats=["pdf", "csv", "json"])

        # PDF may be skipped if reportlab not installed — at minimum csv+json succeed
        formats_generated = {f.format for f in meta.files}
        assert "csv" in formats_generated
        assert "json" in formats_generated
        assert len(meta.files) >= 2

    def test_storage_write_called_per_format(self, tmp_path):
        storage = LocalStorageBackend(base_path=tmp_path)
        gen = ReportGenerator(db=MagicMock(), storage=storage)

        with patch("app.services.report_generator._fetch_report_data",
                   return_value=SAMPLE_DATA):
            meta = gen.generate(event_id=1, formats=["csv", "json"])

        # Files should be readable from storage
        for rf in meta.files:
            data = storage.read(rf.storage_key)
            assert len(data) > 0

    def test_report_id_is_uuid(self, tmp_path):
        import uuid
        storage = LocalStorageBackend(base_path=tmp_path)
        gen = ReportGenerator(db=MagicMock(), storage=storage)

        with patch("app.services.report_generator._fetch_report_data",
                   return_value=SAMPLE_DATA):
            meta = gen.generate(event_id=1, formats=["json"])

        uuid.UUID(meta.report_id)  # raises if invalid

    def test_unknown_format_skipped(self, tmp_path):
        storage = LocalStorageBackend(base_path=tmp_path)
        gen = ReportGenerator(db=MagicMock(), storage=storage)

        with patch("app.services.report_generator._fetch_report_data",
                   return_value=SAMPLE_DATA):
            meta = gen.generate(event_id=1, formats=["json", "xlsx"])

        assert len(meta.files) == 1
        assert meta.files[0].format == "json"

    def test_checksum_populated(self, tmp_path):
        storage = LocalStorageBackend(base_path=tmp_path)
        gen = ReportGenerator(db=MagicMock(), storage=storage)

        with patch("app.services.report_generator._fetch_report_data",
                   return_value=SAMPLE_DATA):
            meta = gen.generate(event_id=1, formats=["json"])

        assert meta.files[0].checksum is not None
        assert len(meta.files[0].checksum) == 32  # MD5 hex


# ════════════════════════════════════════════════════════════════════════════
# Integration tests — API endpoints
# ════════════════════════════════════════════════════════════════════════════

class TestGenerateEndpoint:
    def test_requires_auth(self):
        resp = client.post("/reports/generate", json={"event_id": 1})
        assert resp.status_code == 401

    def test_returns_202_queued(self, db_session):
        headers = _auth_header(db_session)
        mock_task = MagicMock()
        mock_task.apply_async.return_value = MagicMock(id="task-abc")

        fastapi_app.dependency_overrides[get_db] = lambda: db_session
        with patch("app.tasks.report_tasks.export_reports", mock_task):
            resp = client.post("/reports/generate",
                               json={"event_id": 1, "formats": ["csv"]},
                               headers=headers)
        fastapi_app.dependency_overrides.clear()

        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "queued"
        assert data["event_id"] == 1
        assert "task_id" in data

    def test_invalid_format_returns_422(self, db_session):
        headers = _auth_header(db_session)
        fastapi_app.dependency_overrides[get_db] = lambda: db_session
        resp = client.post("/reports/generate",
                           json={"event_id": 1, "formats": ["xlsx"]},
                           headers=headers)
        fastapi_app.dependency_overrides.clear()
        assert resp.status_code == 422


class TestListReportsEndpoint:
    def test_requires_auth(self):
        resp = client.get("/reports/")
        assert resp.status_code == 401

    def test_returns_empty_list(self, db_session):
        headers = _auth_header(db_session)
        fastapi_app.dependency_overrides[get_db] = lambda: db_session
        resp = client.get("/reports/", headers=headers)
        fastapi_app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_seeded_records(self, db_session):
        from app.models.report_record import ReportRecord
        import uuid

        rec = ReportRecord(
            report_id=str(uuid.uuid4()),
            event_id=55001,
            event_name="Test Event",
            generated_at="2024-03-01T00:00:00+00:00",
            formats=["csv"],
            files=[{"format": "csv", "filename": "r.csv",
                    "storage_key": "/tmp/r.csv", "size_bytes": 100,
                    "checksum": "abc"}],
        )
        db_session.add(rec)
        db_session.flush()

        headers = _auth_header(db_session)
        fastapi_app.dependency_overrides[get_db] = lambda: db_session
        resp = client.get("/reports/", headers=headers)
        fastapi_app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_event_id_filter(self, db_session):
        from app.models.report_record import ReportRecord
        import uuid

        for eid in [55002, 55003]:
            db_session.add(ReportRecord(
                report_id=str(uuid.uuid4()),
                event_id=eid,
                event_name=f"Event {eid}",
                generated_at="2024-03-01T00:00:00+00:00",
                formats=["json"],
                files=[],
            ))
        db_session.flush()

        headers = _auth_header(db_session)
        fastapi_app.dependency_overrides[get_db] = lambda: db_session
        resp = client.get("/reports/?event_id=55002", headers=headers)
        fastapi_app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert all(r["event_id"] == 55002 for r in resp.json())


class TestDownloadEndpoint:
    def test_requires_auth(self):
        resp = client.get("/reports/fake-id/download/pdf")
        assert resp.status_code == 401

    def test_returns_404_for_missing_report(self, db_session):
        headers = _auth_header(db_session)
        fastapi_app.dependency_overrides[get_db] = lambda: db_session
        resp = client.get("/reports/nonexistent-id/download/pdf", headers=headers)
        fastapi_app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_returns_404_for_missing_format(self, db_session):
        from app.models.report_record import ReportRecord
        import uuid

        rid = str(uuid.uuid4())
        db_session.add(ReportRecord(
            report_id=rid, event_id=55004, event_name="E",
            generated_at="2024-03-01T00:00:00+00:00",
            formats=["csv"], files=[],
        ))
        db_session.flush()

        headers = _auth_header(db_session)
        fastapi_app.dependency_overrides[get_db] = lambda: db_session
        resp = client.get(f"/reports/{rid}/download/pdf", headers=headers)
        fastapi_app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_returns_file_bytes(self, db_session, tmp_path):
        from app.models.report_record import ReportRecord
        from app.services.report_generator import LocalStorageBackend
        import uuid

        rid = str(uuid.uuid4())
        storage_key = f"test/{rid}/report.json"
        content = b'{"test": true}'

        # Write to tmp storage
        storage = LocalStorageBackend(base_path=tmp_path)
        stored_path = storage.write(storage_key, content)

        db_session.add(ReportRecord(
            report_id=rid, event_id=55005, event_name="E",
            generated_at="2024-03-01T00:00:00+00:00",
            formats=["json"],
            files=[{"format": "json", "filename": "report.json",
                    "storage_key": stored_path, "size_bytes": len(content),
                    "checksum": "abc"}],
        ))
        db_session.flush()

        headers = _auth_header(db_session)
        fastapi_app.dependency_overrides[get_db] = lambda: db_session
        with patch("app.services.report_generator.get_storage", return_value=storage):
            resp = client.get(f"/reports/{rid}/download/json", headers=headers)
        fastapi_app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.content == content
        assert "application/json" in resp.headers["content-type"]