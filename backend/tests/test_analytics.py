"""
test_analytics.py
=================
Phase 2 Tier 3 — Robot Performance Analytics

Test coverage
-------------
Unit
  - performance_calculator: basic kinematics, phase segmentation,
    scoring zone detection, confidence levels, action heuristics,
    multi-team / multi-phase grouping, velocity clamping, empty input.

Integration (DB)
  - _upsert_phase_stats: insert, idempotent re-run, partial update.
  - analytics_tasks._run_analytics: end-to-end with real DB session.

API
  - GET  /matches/{id}/performance  — happy path, 404 no-data, 404 no-tracks.
  - GET  /teams/{id}/performance    — happy path, phase filter, bad phase 422.
  - POST /matches/{id}/performance/compute — queued, 404 no-tracks (Celery mocked).
"""

from __future__ import annotations

import types
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ── Shared fake track dataclass ───────────────────────────────────────────────

@dataclass
class FakeTrack:
    match_id: int
    team_id: int | None
    timestamp_ms: int
    field_x: float | None
    field_y: float | None
    flagged_for_review: bool = False


# ════════════════════════════════════════════════════════════════════════════
# Unit tests — performance_calculator
# ════════════════════════════════════════════════════════════════════════════

from app.services.performance_calculator import (
    _phase_for_ms,
    _in_any_scoring_zone,
    compute_phase_stats,
    AUTO_END_MS,
    TELEOP_END_MS,
)


class TestPhaseSegmentation:
    def test_auto_boundary(self):
        assert _phase_for_ms(0) == "auto"
        assert _phase_for_ms(AUTO_END_MS) == "auto"

    def test_teleop_boundary(self):
        assert _phase_for_ms(AUTO_END_MS + 1) == "teleop"
        assert _phase_for_ms(TELEOP_END_MS) == "teleop"

    def test_endgame_boundary(self):
        assert _phase_for_ms(TELEOP_END_MS + 1) == "endgame"
        assert _phase_for_ms(200_000) == "endgame"


class TestScoringZones:
    def test_blue_speaker_inside(self):
        in_zone, pts = _in_any_scoring_zone(3.0, 6.0)
        assert in_zone is True
        assert pts == 2.0

    def test_outside_all_zones(self):
        in_zone, pts = _in_any_scoring_zone(25.0, 2.0)   # middle of field, outside all zones
        assert in_zone is False
        assert pts == 0.0

    def test_red_amp_inside(self):
        in_zone, pts = _in_any_scoring_zone(52.0, 24.0)
        assert in_zone is True
        assert pts == 1.0

    def test_stage_zone_zero_pts(self):
        in_zone, pts = _in_any_scoring_zone(27.0, 13.0)
        assert in_zone is True
        assert pts == 0.0


class TestComputePhaseStats:
    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _linear_tracks(
        team_id: int,
        match_id: int,
        n: int,
        start_ms: int,
        step_ms: int,
        dx: float = 1.0,
        dy: float = 0.0,
        start_x: float = 20.0,
        start_y: float = 12.0,
    ) -> list[FakeTrack]:
        """Generate n evenly-spaced tracks in a straight line."""
        tracks = []
        for i in range(n):
            tracks.append(FakeTrack(
                match_id=match_id,
                team_id=team_id,
                timestamp_ms=start_ms + i * step_ms,
                field_x=start_x + i * dx,
                field_y=start_y + i * dy,
            ))
        return tracks

    # ── tests ─────────────────────────────────────────────────────────────────

    def test_empty_input_returns_empty(self):
        assert compute_phase_stats(match_id=1, tracks=[]) == []

    def test_no_team_id_skipped(self):
        tracks = [FakeTrack(match_id=1, team_id=None, timestamp_ms=0,
                            field_x=10.0, field_y=10.0)]
        assert compute_phase_stats(match_id=1, tracks=tracks) == []

    def test_single_team_auto_kinematics(self):
        """25 frames, 1 ft apart, 500 ms apart → ~1.905 fps avg."""
        tracks = self._linear_tracks(
            team_id=100, match_id=1, n=25,
            start_ms=0, step_ms=500, dx=1.0,
        )
        results = compute_phase_stats(match_id=1, tracks=tracks)
        # All timestamps 0–12000 ms → should be auto
        auto = next((r for r in results if r.phase == "auto"), None)
        assert auto is not None
        assert auto.team_id == 100
        assert auto.distance_traveled_ft == pytest.approx(24.0, abs=0.1)
        assert auto.avg_velocity_fps == pytest.approx(2.0, abs=0.05)
        assert auto.max_velocity_fps == pytest.approx(2.0, abs=0.05)
        assert auto.track_count == 25

    def test_multi_team_separation(self):
        """Two teams in same match must produce separate results."""
        t1 = self._linear_tracks(101, 1, 20, start_ms=0, step_ms=600)
        t2 = self._linear_tracks(102, 1, 20, start_ms=0, step_ms=600, start_x=30.0)
        results = compute_phase_stats(match_id=1, tracks=t1 + t2)
        team_ids = {r.team_id for r in results}
        assert {101, 102}.issubset(team_ids)

    def test_multi_phase_split(self):
        """Tracks spanning auto + teleop produce two phase records."""
        auto_tracks = self._linear_tracks(
            team_id=200, match_id=2, n=10,
            start_ms=1_000, step_ms=1_000,   # 1 s – 10 s (auto)
        )
        teleop_tracks = self._linear_tracks(
            team_id=200, match_id=2, n=10,
            start_ms=16_000, step_ms=5_000,  # 16 s – 61 s (teleop)
        )
        results = compute_phase_stats(match_id=2, tracks=auto_tracks + teleop_tracks)
        phases = {r.phase for r in results}
        assert "auto" in phases
        assert "teleop" in phases

    def test_confidence_high(self):
        tracks = self._linear_tracks(300, 5, 30, start_ms=0, step_ms=400)
        results = compute_phase_stats(5, tracks)
        assert all(r.data_confidence == "high" for r in results)

    def test_confidence_medium(self):
        tracks = self._linear_tracks(300, 5, 10, start_ms=0, step_ms=1_000)
        results = compute_phase_stats(5, tracks)
        assert any(r.data_confidence == "medium" for r in results)

    def test_confidence_low(self):
        tracks = self._linear_tracks(300, 5, 3, start_ms=0, step_ms=1_000)
        results = compute_phase_stats(5, tracks)
        assert any(r.data_confidence == "low" for r in results)

    def test_velocity_clamping_ignores_glitches(self):
        """A single frame that teleports 500 ft should not inflate distance."""
        tracks = [
            FakeTrack(match_id=1, team_id=10, timestamp_ms=0,    field_x=0.0, field_y=0.0),
            FakeTrack(match_id=1, team_id=10, timestamp_ms=100,  field_x=500.0, field_y=0.0),  # glitch
            FakeTrack(match_id=1, team_id=10, timestamp_ms=200,  field_x=1.0, field_y=0.0),
        ]
        results = compute_phase_stats(match_id=1, tracks=tracks)
        auto = next(r for r in results if r.phase == "auto")
        # Glitch frame skipped — only real move counted
        assert auto.distance_traveled_ft < 10.0

    def test_null_coordinates_skipped(self):
        tracks = [
            FakeTrack(match_id=1, team_id=55, timestamp_ms=0,   field_x=None, field_y=None),
            FakeTrack(match_id=1, team_id=55, timestamp_ms=500, field_x=5.0,  field_y=5.0),
            FakeTrack(match_id=1, team_id=55, timestamp_ms=1000, field_x=6.0, field_y=5.0),
        ]
        results = compute_phase_stats(match_id=1, tracks=tracks)
        assert len(results) == 1
        assert results[0].distance_traveled_ft == pytest.approx(1.0, abs=0.01)

    def test_action_stationary(self):
        """Robot that barely moves with many frames → stationary_or_disabled."""
        tracks = [
            FakeTrack(match_id=1, team_id=77, timestamp_ms=i * 500,
                      field_x=10.0 + i * 0.01, field_y=10.0)
            for i in range(20)
        ]
        results = compute_phase_stats(match_id=1, tracks=tracks)
        auto = next(r for r in results if r.phase == "auto")
        assert "stationary_or_disabled" in auto.actions_detected

    def test_action_high_mobility(self):
        """Robot covering 100+ ft → high_mobility."""
        tracks = self._linear_tracks(88, 1, 25, start_ms=0, step_ms=400, dx=4.5)
        results = compute_phase_stats(match_id=1, tracks=tracks)
        auto = next(r for r in results if r.phase == "auto")
        assert "high_mobility" in auto.actions_detected

    def test_scoring_zone_time_accumulated(self):
        """Tracks inside blue speaker zone should accumulate zone time."""
        tracks = [
            FakeTrack(match_id=1, team_id=99, timestamp_ms=i * 1_000,
                      field_x=3.0, field_y=6.0)   # inside blue_speaker
            for i in range(10)
        ]
        results = compute_phase_stats(match_id=1, tracks=tracks)
        auto = next(r for r in results if r.phase == "auto")
        assert auto.time_in_scoring_zone_s > 0
        assert auto.estimated_score > 0

    def test_match_id_propagated(self):
        tracks = self._linear_tracks(500, match_id=42, n=10, start_ms=0, step_ms=1_000)
        results = compute_phase_stats(match_id=42, tracks=tracks)
        assert all(r.match_id == 42 for r in results)


# ════════════════════════════════════════════════════════════════════════════
# Integration tests — _upsert_phase_stats & _run_analytics
# ════════════════════════════════════════════════════════════════════════════

from app.tasks.analytics_tasks import _upsert_phase_stats, _run_analytics
from app.services.performance_calculator import PhaseStatResult
from app.models.phase_stat import PhaseStat
from app.models.event import Event
from app.models.match import Match
from app.models.team import Team


# ── Shared DB seed helpers ─────────────────────────────────────────────────

def _seed_event(db, event_id: int) -> Event:
    from datetime import date
    e = Event(
        event_id=event_id,
        season_year=2024,
        tba_event_key=f"2024test{event_id}",
        name=f"Test Event {event_id}",
        start_date=date(2024, 3, 1),
        end_date=date(2024, 3, 3),
    )
    db.add(e)
    db.flush()
    return e


def _seed_team(db, team_id: int) -> Team:
    t = Team(team_id=team_id, team_number=team_id)
    db.add(t)
    db.flush()
    return t


def _seed_match(db, match_id: int, event_id: int) -> Match:
    m = Match(
        match_id=match_id, event_id=event_id,
        tba_match_key=f"2024test{event_id}_qm{match_id}",
        match_type="qualification", match_number=match_id,
    )
    db.add(m)
    db.flush()
    return m


class TestUpsertPhaseStats:
    def _make_stat(self, match_id, team_id, phase="auto", dist=10.0):
        return PhaseStatResult(
            match_id=match_id, team_id=team_id, phase=phase,
            distance_traveled_ft=dist, avg_velocity_fps=2.0,
            max_velocity_fps=3.0, time_in_scoring_zone_s=1.0,
            estimated_score=0.5, actions_detected=["high_mobility"],
            track_count=20, data_confidence="high",
        )

    def test_insert_new_rows(self, db_session):
        _seed_event(db_session, 9001)
        _seed_team(db_session, 9001)
        _seed_match(db_session, 9001, 9001)
        db_session.flush()

        stats = [self._make_stat(match_id=9001, team_id=9001, phase="auto")]
        saved = _upsert_phase_stats(db_session, stats)
        assert saved == 1
        row = db_session.query(PhaseStat).filter_by(
            match_id=9001, team_id=9001, phase="auto"
        ).first()
        assert row is not None
        assert row.distance_traveled_ft == pytest.approx(10.0)

    def test_upsert_updates_existing(self, db_session):
        _seed_event(db_session, 9002)
        _seed_team(db_session, 9002)
        _seed_match(db_session, 9002, 9002)
        db_session.flush()

        stat = self._make_stat(match_id=9002, team_id=9002, phase="teleop", dist=20.0)
        _upsert_phase_stats(db_session, [stat])

        updated = self._make_stat(match_id=9002, team_id=9002, phase="teleop", dist=35.0)
        _upsert_phase_stats(db_session, [updated])

        rows = db_session.query(PhaseStat).filter_by(
            match_id=9002, team_id=9002, phase="teleop"
        ).all()
        assert len(rows) == 1
        assert rows[0].distance_traveled_ft == pytest.approx(35.0)

    def test_empty_list_returns_zero(self, db_session):
        assert _upsert_phase_stats(db_session, []) == 0

    def test_multiple_phases_inserted(self, db_session):
        _seed_event(db_session, 9003)
        _seed_team(db_session, 9003)
        _seed_match(db_session, 9003, 9003)
        db_session.flush()

        stats = [
            self._make_stat(match_id=9003, team_id=9003, phase="auto"),
            self._make_stat(match_id=9003, team_id=9003, phase="teleop"),
            self._make_stat(match_id=9003, team_id=9003, phase="endgame"),
        ]
        saved = _upsert_phase_stats(db_session, stats)
        assert saved == 3


class TestRunAnalytics:
    def test_no_tracks_returns_no_data(self, db_session):
        with patch("app.tasks.analytics_tasks.SessionLocal") as mock_sl:
            mock_sl.return_value.__enter__ = lambda s: db_session
            mock_sl.return_value.__exit__ = MagicMock(return_value=False)
            result = _run_analytics(match_id=99999)
        assert result["status"] == "no_data"
        assert result["phase_stats_saved"] == 0

    def test_with_tracks_runs_pipeline(self, db_session):
        """Seed Event/Match/Team/MovementTrack rows and verify analytics produces PhaseStat rows."""
        from app.models.movement_track import MovementTrack

        _seed_event(db_session, 8001)
        _seed_team(db_session, 8001)
        _seed_match(db_session, 8001, 8001)
        db_session.flush()

        for i in range(25):
            db_session.add(MovementTrack(
                match_id=8001,
                team_id=8001,
                track_id=i,
                frame_number=i,
                timestamp_ms=i * 500,
                field_x=float(i),
                field_y=5.0,
                pixel_x=float(100 + i),
                pixel_y=200.0,
                confidence_score=0.9,
                flagged_for_review=False,
            ))
        db_session.flush()

        with patch("app.tasks.analytics_tasks.SessionLocal") as mock_sl:
            mock_sl.return_value.__enter__ = lambda s: db_session
            mock_sl.return_value.__exit__ = MagicMock(return_value=False)
            result = _run_analytics(match_id=8001)

        assert result["status"] == "complete"
        assert result["teams_processed"] >= 1
        assert result["phase_stats_saved"] >= 1


# ════════════════════════════════════════════════════════════════════════════
# API tests
# ════════════════════════════════════════════════════════════════════════════

from fastapi.testclient import TestClient
from datetime import timedelta
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)


def _auth_header(db_session, role="SCOUT") -> dict:
    from app.models.user import User
    from app.core.security import get_password_hash
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
    db_session.refresh(user)
    token = create_access_token(subject=user.user_id, expires_delta=timedelta(days=1))
    return {"Authorization": f"Bearer {token}"}


class TestMatchPerformanceEndpoint:
    def test_returns_404_when_no_data(self, db_session):
        from app.db.session import get_db
        app.dependency_overrides[get_db] = lambda: db_session
        resp = client.get("/matches/999999/performance")
        app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_returns_performance_data(self, db_session):
        from app.db.session import get_db

        _seed_event(db_session, 7001)
        _seed_team(db_session, 7001)
        _seed_match(db_session, 7001, 7001)
        db_session.add(PhaseStat(
            match_id=7001, team_id=7001, phase="auto",
            distance_traveled_ft=30.0, avg_velocity_fps=3.0,
            max_velocity_fps=5.0, time_in_scoring_zone_s=2.5,
            estimated_score=1.5, actions_detected=["high_mobility"],
            track_count=25, data_confidence="high",
        ))
        db_session.flush()

        app.dependency_overrides[get_db] = lambda: db_session
        resp = client.get("/matches/7001/performance")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["match_id"] == 7001
        assert len(data["teams"]) == 1
        assert data["teams"][0]["team_id"] == 7001
        assert data["teams"][0]["phases"][0]["phase"] == "auto"

    def test_groups_multiple_teams(self, db_session):
        from app.db.session import get_db

        _seed_event(db_session, 7002)
        _seed_match(db_session, 7002, 7002)
        for team_id in [7010, 7020, 7030]:
            _seed_team(db_session, team_id)
            db_session.add(PhaseStat(
                match_id=7002, team_id=team_id, phase="teleop",
                distance_traveled_ft=15.0, avg_velocity_fps=2.0,
                max_velocity_fps=4.0, time_in_scoring_zone_s=1.0,
                estimated_score=0.5, track_count=20, data_confidence="medium",
            ))
        db_session.flush()

        app.dependency_overrides[get_db] = lambda: db_session
        resp = client.get("/matches/7002/performance")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert len(resp.json()["teams"]) == 3


class TestTeamPerformanceEndpoint:
    def test_returns_empty_list_for_unknown_team(self, db_session):
        from app.db.session import get_db
        app.dependency_overrides[get_db] = lambda: db_session
        resp = client.get("/teams/999999/performance")
        app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json() == []

    def test_phase_filter_works(self, db_session):
        from app.db.session import get_db

        _seed_event(db_session, 6001)
        _seed_team(db_session, 6001)
        _seed_match(db_session, 6001, 6001)
        for phase in ["auto", "teleop", "endgame"]:
            db_session.add(PhaseStat(
                match_id=6001, team_id=6001, phase=phase,
                distance_traveled_ft=10.0, avg_velocity_fps=2.0,
                max_velocity_fps=3.0, time_in_scoring_zone_s=0.5,
                estimated_score=0.2, track_count=15, data_confidence="high",
            ))
        db_session.flush()

        app.dependency_overrides[get_db] = lambda: db_session
        resp = client.get("/teams/6001/performance?phase=auto")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert all(r["phase"] == "auto" for r in resp.json())

    def test_invalid_phase_returns_422(self, db_session):
        from app.db.session import get_db
        app.dependency_overrides[get_db] = lambda: db_session
        resp = client.get("/teams/1/performance?phase=badphase")
        app.dependency_overrides.clear()
        assert resp.status_code == 422


class TestComputeEndpoint:
    def test_returns_404_when_no_tracks(self, db_session):
        from app.db.session import get_db
        headers = _auth_header(db_session, role="SYSTEM_ADMIN")
        app.dependency_overrides[get_db] = lambda: db_session
        resp = client.post("/matches/999888/performance/compute", headers=headers)
        app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_dispatches_task_when_tracks_exist(self, db_session):
        from app.models.movement_track import MovementTrack
        from app.db.session import get_db

        _seed_event(db_session, 5001)
        _seed_team(db_session, 5001)
        _seed_match(db_session, 5001, 5001)
        db_session.add(MovementTrack(
            match_id=5001, team_id=5001,
            track_id=1, frame_number=1, timestamp_ms=1000,
            field_x=10.0, field_y=10.0,
            pixel_x=100.0, pixel_y=200.0,
            confidence_score=0.9, flagged_for_review=False,
        ))
        db_session.flush()

        headers = _auth_header(db_session, role="SYSTEM_ADMIN")
        mock_task = MagicMock()
        mock_task.apply_async.return_value = MagicMock(id="mock-task-id-123")

        app.dependency_overrides[get_db] = lambda: db_session
        with patch("app.tasks.analytics_tasks._compute_robot_performance_celery", mock_task):
            resp = client.post("/matches/5001/performance/compute", headers=headers)
        app.dependency_overrides.clear()

        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "queued"
        assert data["match_id"] == 5001
        assert "task_id" in data