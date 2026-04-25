"""
Tests for TBA integration — tba_client, tba_mapper, and the admin sync endpoint.
All HTTP calls to TBA are mocked so no API key or network is needed.
"""
from __future__ import annotations

from datetime import date
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.integrations import tba_client, tba_mapper
from app.models import Alliance, Event, Match, RobotPerformance, Team
from app.crud import crud_sync_log

# ── Fixtures ─────────────────────────────────────────────────────────────────

TBA_EVENT = {
    "key": "2024test",
    "name": "Test Regional",
    "city": "San Jose",
    "state_prov": "CA",
    "country": "USA",
    "start_date": "2024-03-01",
    "end_date": "2024-03-03",
    "year": 2024,
}

TBA_TEAMS = [
    {
        "team_number": 254,
        "nickname": "The Cheesy Poofs",
        "school_name": "Bellarmine College Prep",
        "city": "San Jose",
        "state_prov": "CA",
        "country": "USA",
        "rookie_year": 1999,
    },
    {
        "team_number": 971,
        "nickname": "Spartan Robotics",
        "school_name": "Mountain View High School",
        "city": "Mountain View",
        "state_prov": "CA",
        "country": "USA",
        "rookie_year": 2002,
    },
    {
        "team_number": 1678,
        "nickname": "Citrus Circuits",
        "school_name": "Da Vinci Charter Academy",
        "city": "Davis",
        "state_prov": "CA",
        "country": "USA",
        "rookie_year": 2005,
    },
    {
        "team_number": 4,
        "nickname": "Team 4",
        "school_name": None,
        "city": "Anytown",
        "state_prov": "CA",
        "country": "USA",
        "rookie_year": 2000,
    },
    {
        "team_number": 5,
        "nickname": "Team 5",
        "school_name": None,
        "city": "Anytown",
        "state_prov": "CA",
        "country": "USA",
        "rookie_year": 2000,
    },
    {
        "team_number": 6,
        "nickname": "Team 6",
        "school_name": None,
        "city": "Anytown",
        "state_prov": "CA",
        "country": "USA",
        "rookie_year": 2000,
    },
]

TBA_MATCHES = [
    {
        "key": "2024test_qm1",
        "comp_level": "qm",
        "match_number": 1,
        "time": 1709300000,
        "videos": [{"type": "youtube", "key": "abc123"}],
        "winning_alliance": "red",
        "alliances": {
            "red": {
                "score": 100,
                "team_keys": ["frc254", "frc971", "frc1678"],
            },
            "blue": {
                "score": 80,
                "team_keys": ["frc4", "frc5", "frc6"],
            },
        },
    },
    {
        "key": "2024test_qm2",
        "comp_level": "qm",
        "match_number": 2,
        "time": None,
        "videos": [],
        "winning_alliance": "",
        "alliances": {
            "red": {"score": -1, "team_keys": ["frc254", "frc4", "frc5"]},
            "blue": {"score": -1, "team_keys": ["frc971", "frc1678", "frc6"]},
        },
    },
]


# ── tba_client tests ──────────────────────────────────────────────────────────

class TestTbaClient:
    def test_get_event_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = TBA_EVENT

        with patch("httpx.get", return_value=mock_response):
            result = cast(dict[str, Any], tba_client.get_event("2024test"))

        assert result["key"] == "2024test"
        assert result["name"] == "Test Regional"

    def test_get_event_404_raises_value_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.get", return_value=mock_response):
            with pytest.raises(ValueError, match="404"):
                tba_client.get_event("invalid_key")

    def test_get_event_429_retries_then_raises(self):
        mock_response = MagicMock()
        mock_response.status_code = 429

        with patch("httpx.get", return_value=mock_response):
            with patch("time.sleep"):  # don't actually sleep in tests
                with pytest.raises(RuntimeError, match="rate limit"):
                    tba_client.get_event("2024test")

    def test_get_event_teams(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = TBA_TEAMS

        with patch("httpx.get", return_value=mock_response):
            result = tba_client.get_event_teams("2024test")

        assert len(result) == 6
        assert result[0]["team_number"] == 254

    def test_get_event_matches(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = TBA_MATCHES

        with patch("httpx.get", return_value=mock_response):
            result = tba_client.get_event_matches("2024test")

        assert len(result) == 2


# ── tba_mapper tests ──────────────────────────────────────────────────────────

class TestTbaMapper:
    def test_upsert_event(self, db_session: Session):
        event = tba_mapper.upsert_event(db_session, TBA_EVENT)

        assert isinstance(event, Event)
        assert event.tba_event_key == "2024test"
        assert event.name == "Test Regional"
        assert event.city == "San Jose"
        assert event.state_prov == "CA"
        assert event.country == "USA"
        assert event.start_date == date(2024, 3, 1)
        assert event.end_date == date(2024, 3, 3)
        assert event.season_year == 2024

    def test_upsert_event_is_idempotent(self, db_session: Session):
        tba_mapper.upsert_event(db_session, TBA_EVENT)
        # second call should update, not duplicate
        updated = {**TBA_EVENT, "name": "Updated Regional"}
        event = tba_mapper.upsert_event(db_session, updated)

        assert event.name == "Updated Regional"
        count = db_session.query(Event).filter_by(tba_event_key="2024test").count()
        assert count == 1

    def test_upsert_team(self, db_session: Session):
        team = tba_mapper.upsert_team(db_session, TBA_TEAMS[0])

        assert isinstance(team, Team)
        assert team.team_number == 254
        assert team.team_name == "The Cheesy Poofs"
        assert team.city == "San Jose"

    def test_upsert_team_is_idempotent(self, db_session: Session):
        tba_mapper.upsert_team(db_session, TBA_TEAMS[0])
        updated = {**TBA_TEAMS[0], "nickname": "Updated Name"}
        team = tba_mapper.upsert_team(db_session, updated)

        assert team.team_name == "Updated Name"
        count = db_session.query(Team).filter_by(team_number=254).count()
        assert count == 1

    def test_upsert_match_creates_alliances_and_performances(self, db_session: Session):
        event = tba_mapper.upsert_event(db_session, TBA_EVENT)
        team_number_to_id = {}
        for tba_team in TBA_TEAMS:
            team = tba_mapper.upsert_team(db_session, tba_team)
            team_number_to_id[tba_team["team_number"]] = team.team_id

        match = tba_mapper.upsert_match(db_session, TBA_MATCHES[0], event, team_number_to_id)

        assert isinstance(match, Match)
        assert match.tba_match_key == "2024test_qm1"
        assert match.match_type == "qualification"
        assert match.match_number == 1
        assert match.video_url == "https://www.youtube.com/watch?v=abc123"

        alliances = db_session.query(Alliance).filter_by(match_id=match.match_id).all()
        assert len(alliances) == 2

        colors = {a.color for a in alliances}
        assert colors == {"red", "blue"}

        red = next(a for a in alliances if a.color == "red")
        assert red.total_score == 100
        assert red.won is True

        blue = next(a for a in alliances if a.color == "blue")
        assert blue.total_score == 80
        assert blue.won is False

        perfs = db_session.query(RobotPerformance).filter_by(match_id=match.match_id).all()
        assert len(perfs) == 6  # 3 per alliance

    def test_upsert_match_handles_unplayed(self, db_session: Session):
        """Unplayed matches have score=-1 from TBA — should store as None."""
        event = tba_mapper.upsert_event(db_session, TBA_EVENT)
        team_number_to_id = {}
        for tba_team in TBA_TEAMS:
            team = tba_mapper.upsert_team(db_session, tba_team)
            team_number_to_id[tba_team["team_number"]] = team.team_id

        match = tba_mapper.upsert_match(db_session, TBA_MATCHES[1], event, team_number_to_id)

        alliances = db_session.query(Alliance).filter_by(match_id=match.match_id).all()
        for alliance in alliances:
            assert alliance.total_score is None
            assert alliance.won is None

    def test_match_type_mapping(self, db_session: Session):
        event = tba_mapper.upsert_event(db_session, TBA_EVENT)
        team_number_to_id = {}
        for tba_team in TBA_TEAMS:
            team = tba_mapper.upsert_team(db_session, tba_team)
            team_number_to_id[tba_team["team_number"]] = team.team_id

        for comp_level, expected_type in [("qm", "qualification"), ("sf", "semifinal"), ("f", "final"), ("ef", "semifinal")]:
            tba_match = {
                **TBA_MATCHES[0],
                "key": f"2024test_{comp_level}1",
                "comp_level": comp_level,
            }
            match = tba_mapper.upsert_match(db_session, tba_match, event, team_number_to_id)
            assert match.match_type == expected_type


# ── sync log tests ────────────────────────────────────────────────────────────

class TestSyncLog:
    def test_create_sync_log_success(self, db_session: Session):
        log = crud_sync_log.create_sync_log(
            db_session,
            sync_type="event",
            resource_id="2024test",
            status="success",
            records_created=135,
            new_values={"teams_synced": 42, "matches_synced": 93},
        )
        db_session.flush()

        assert log.sync_type == "event"
        assert log.resource_id == "2024test"
        assert log.status == "success"
        assert log.records_created == 135
        assert log.new_values is not None
        assert log.new_values["teams_synced"] == 42

    def test_create_sync_log_failure(self, db_session: Session):
        log = crud_sync_log.create_sync_log(
            db_session,
            sync_type="event",
            resource_id="bad_key",
            status="failed",
            error_message="TBA returned 404 for /event/bad_key",
        )
        db_session.flush()

        assert log.status == "failed"
        assert log.error_message is not None
        assert "404" in log.error_message