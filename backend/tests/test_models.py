from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import Alliance, Event, Match, RobotPerformance, ScoutingObservation, SyncLog, Team, User


def test_seeded_schema_counts(db_session):
    assert db_session.scalar(select(func.count()).select_from(Event)) == 1
    assert db_session.scalar(select(func.count()).select_from(Team)) == 30
    assert db_session.scalar(select(func.count()).select_from(Match)) == 12
    assert db_session.scalar(select(func.count()).select_from(Alliance)) == 24
    assert db_session.scalar(select(func.count()).select_from(RobotPerformance)) == 72
    assert db_session.scalar(select(func.count()).select_from(User)) == 2
    assert db_session.scalar(select(func.count()).select_from(ScoutingObservation)) == 12
    assert db_session.scalar(select(func.count()).select_from(SyncLog)) == 12


def test_event_match_relationship(db_session):
    event = db_session.scalars(select(Event)).one()
    assert len(event.matches) == 12
    assert all(match.event_id == event.event_id for match in event.matches)


def test_match_alliance_and_robot_relationships(db_session):
    match = db_session.scalars(select(Match).order_by(Match.match_number)).first()
    assert match is not None
    assert len(match.alliances) == 2
    assert len(match.robot_performances) == 6
    assert {alliance.color for alliance in match.alliances} == {"red", "blue"}


def test_team_robot_performance_relationship(db_session):
    team = db_session.scalars(select(Team).where(Team.team_number == 1678)).one()
    assert len(team.robot_performances) >= 1


def test_unique_team_number_constraint(db_session):
    team = Team(team_number=9999, team_name="Temp Team")
    db_session.add(team)
    db_session.flush()

    db_session.add(Team(team_number=9999, team_name="Duplicate Team"))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_check_constraint_on_alliance_color(db_session):
    event = db_session.scalars(select(Event)).one()
    invalid_match = Match(
        event_id=event.event_id,
        tba_match_key="bad_match_key",
        match_type="qualification",
        match_number=99,
    )
    db_session.add(invalid_match)
    db_session.flush()

    db_session.add(Alliance(match_id=invalid_match.match_id, color="pink"))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_foreign_key_constraint_on_match_event(db_session):
    db_session.add(
        Match(
            event_id=999999,
            tba_match_key="fk_fail_key",
            match_type="qualification",
            match_number=100,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()