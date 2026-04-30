"""Test CRUD operations for all models"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models import (
    Event, Team, Match, Alliance, RobotPerformance,
    ScoutingObservation, User, SyncLog, UserAlliance
)
from app.crud import crud_event, crud_team, crud_match, crud_scouting_observation
from app.core.security import get_password_hash


class TestEventCRUD:
    """Test Event CRUD operations"""

    def test_get_events_with_pagination(self, db_session):
        """Test getting events with skip/limit pagination"""
        events = crud_event.get_events(db_session, skip=0, limit=100)
        assert isinstance(events, list)
        assert len(events) > 0

    def test_get_events_with_year_filter(self, db_session):
        """Test filtering events by year"""
        events_2024 = crud_event.get_events(db_session, year=2024, skip=0, limit=100)
        assert isinstance(events_2024, list)
        for event in events_2024:
            # Event uses start_date, not event_date
            assert event.start_date is None or event.start_date.year == 2024

    def test_get_events_count(self, db_session):
        """Test getting total event count"""
        count = crud_event.get_events_count(db_session, year=None)
        assert count > 0

    def test_get_event_by_id(self, db_session):
        """Test getting single event"""
        event = db_session.scalars(select(Event)).first()
        assert event is not None
        assert event.event_id is not None

    def test_create_event(self, db_session):
        """Test creating a new event"""
        from datetime import date
        new_event = Event(
            tba_event_key="2025ca",
            name="California 2025",
            start_date=date(2025, 3, 15),
            end_date=date(2025, 3, 17),
            city="Santa Clara",
            state_prov="CA",
            country="USA",
            season_year=2025,
        )
        db_session.add(new_event)
        db_session.commit()

        retrieved = db_session.scalar(select(Event).where(Event.tba_event_key == "2025ca"))
        assert retrieved is not None
        assert retrieved.name == "California 2025"


class TestTeamCRUD:
    """Test Team CRUD operations"""

    def test_get_teams_with_pagination(self, db_session):
        """Test getting teams with pagination"""
        teams = crud_team.get_teams(db_session, skip=0, limit=10)
        assert len(teams) <= 10
        assert len(teams) > 0

    def test_get_teams_with_team_number_filter(self, db_session):
        """Test filtering teams by team number"""
        teams = crud_team.get_teams(db_session, team_number=1678, skip=0, limit=100)
        assert len(teams) <= 1
        if teams:
            assert teams[0].team_number == 1678

    def test_get_teams_count(self, db_session):
        """Test getting total team count"""
        count = crud_team.get_teams_count(db_session, team_number=None)
        assert count > 0

    def test_get_team_by_id(self, db_session):
        """Test getting team by ID"""
        team = db_session.scalars(select(Team)).first()
        assert team is not None
        assert team.team_id > 0

    def test_create_team(self, db_session):
        """Test creating a new team"""
        new_team = Team(
            team_number=9999,
            team_name="Test Team 9999",
            school_name="Test School",
            city="Test City",
            state_prov="TS",
            country="USA",
        )
        db_session.add(new_team)
        db_session.commit()

        retrieved = db_session.scalar(select(Team).where(Team.team_number == 9999))
        assert retrieved is not None
        assert retrieved.team_name == "Test Team 9999"


class TestMatchCRUD:
    """Test Match CRUD operations"""

    def test_get_matches_with_pagination(self, db_session):
        """Test getting matches with pagination"""
        matches = crud_match.get_matches(db_session, skip=0, limit=5)
        assert len(matches) <= 5
        assert len(matches) > 0

    def test_get_matches_count(self, db_session):
        """Test getting total match count"""
        count = crud_match.get_matches_count(db_session)
        assert count > 0

    def test_get_matches_by_event_with_pagination(self, db_session):
        """Test getting matches for event with pagination"""
        event = db_session.scalars(select(Event)).first()
        assert event is not None

        matches = crud_match.get_matches_by_event(
            event.event_id, db_session, skip=0, limit=100
        )
        assert isinstance(matches, list)
        if matches:
            assert all(m.event_id == event.event_id for m in matches)

    def test_get_matches_by_event_count(self, db_session):
        """Test getting count of matches for event"""
        event = db_session.scalars(select(Event)).first()
        assert event is not None

        count = crud_match.get_matches_by_event_count(event.event_id, db_session)
        assert count >= 0

    def test_create_match(self, db_session):
        """Test creating a new match"""
        event = db_session.scalars(select(Event)).first()
        assert event is not None

        new_match = Match(
            event_id=event.event_id,
            tba_match_key="2025ca_qm999",
            match_type="qualification",
            match_number=999,
        )
        db_session.add(new_match)
        db_session.commit()

        retrieved = db_session.scalar(
            select(Match).where(Match.tba_match_key == "2025ca_qm999")
        )
        assert retrieved is not None
        assert retrieved.match_type == "qualification"


class TestScoutingObservationCRUD:
    """Test ScoutingObservation CRUD operations"""

    def test_get_observations_with_pagination(self, db_session):
        """Test getting observations with pagination"""
        observations = crud_scouting_observation.get_scouting_observations(
            db_session, skip=0, limit=5
        )
        assert len(observations) <= 5
        assert len(observations) >= 0

    def test_get_observations_count(self, db_session):
        """Test getting total observation count"""
        count = crud_scouting_observation.get_scouting_observations_count(db_session)
        assert count >= 0

    def test_create_observation(self, db_session, test_user):
        """Test creating a scouting observation"""
        match = db_session.scalars(select(Match)).first()
        team = db_session.scalars(select(Team)).first()
        assert match is not None and team is not None

        new_obs = ScoutingObservation(
            scout_id=test_user.user_id,
            match_id=match.match_id,
            team_id=team.team_id,
            notes="test observation notes",
            rating=4,
        )
        db_session.add(new_obs)
        db_session.commit()

        retrieved = db_session.scalar(
            select(ScoutingObservation).where(
                ScoutingObservation.observation_id == new_obs.observation_id
            )
        )
        assert retrieved is not None
        assert retrieved.notes == "test observation notes"

    def test_bulk_create_observations(self, db_session, test_user):
        """Test bulk creating observations"""
        match = db_session.scalars(select(Match)).first()
        team = db_session.scalars(select(Team)).first()
        assert match is not None and team is not None

        for i in range(3):
            obs = ScoutingObservation(
                scout_id=test_user.user_id,
                match_id=match.match_id,
                team_id=team.team_id,
                notes=f"bulk test {i}",
                rating=3,
            )
            db_session.add(obs)
        db_session.commit()

        count = db_session.scalar(
            select(func.count()).select_from(ScoutingObservation)
        )
        assert count >= 3


class TestUserCRUD:
    """Test User CRUD operations"""

    def test_get_user_by_email(self, db_session, test_user):
        """Test getting user by email"""
        user = db_session.scalar(
            select(User).where(User.email == test_user.email)
        )
        assert user is not None
        assert user.email == test_user.email

    def test_create_user(self, db_session):
        """Test creating a new user"""
        new_user = User(
            email="newuser@test.com",
            username="newuser",
            hashed_password=get_password_hash("newpass123"),
            role="SCOUT",
            team_id=1,
            is_active=True,
        )
        db_session.add(new_user)
        db_session.commit()

        retrieved = db_session.scalar(
            select(User).where(User.email == "newuser@test.com")
        )
        assert retrieved is not None
        assert retrieved.username == "newuser"

    def test_user_roles(self, db_session):
        """Test different user roles"""
        roles = ["SCOUT", "COACH", "TEAM_ADMIN", "SYSTEM_ADMIN"]
        for role in roles:
            user = User(
                email=f"user_{role}@test.com",
                username=f"user_{role}",
                hashed_password=get_password_hash("pass123"),
                role=role,
                team_id=1 if role != "SYSTEM_ADMIN" else None,
                is_active=True,
            )
            db_session.add(user)
        db_session.commit()

        for role in roles:
            user = db_session.scalar(
                select(User).where(User.role == role)
            )
            assert user is not None
            assert user.role == role


class TestUserAllianceCRUD:
    """Test UserAlliance CRUD operations"""

    def test_create_user_alliance(self, db_session, test_user):
        """Test creating a user alliance"""
        ua = UserAlliance(
            user_id=test_user.user_id,
            name="My Alliance",
            red_teams="1678,1690,7512",
            blue_teams="254,1323,3476",
        )
        db_session.add(ua)
        db_session.commit()

        retrieved = db_session.scalar(
            select(UserAlliance).where(
                UserAlliance.user_id == test_user.user_id
            )
        )
        assert retrieved is not None
        assert retrieved.red_teams == "1678,1690,7512"

    def test_get_user_alliances(self, db_session, test_user):
        """Test getting all user alliances"""
        alliances = db_session.scalars(
            select(UserAlliance).where(UserAlliance.user_id == test_user.user_id)
        ).all()
        assert isinstance(alliances, list)


class TestSyncLogCRUD:
    """Test SyncLog CRUD operations"""

    def test_create_sync_log(self, db_session, test_user):
        """Test creating sync log"""
        # SyncLog uses: sync_id, sync_type, resource_id, status,
        # records_created, records_updated, triggered_by
        log = SyncLog(
            sync_type="tba_import",
            resource_id="2025ca",
            status="success",
            records_created=42,
            records_updated=0,
            triggered_by=test_user.user_id,
        )
        db_session.add(log)
        db_session.commit()

        retrieved = db_session.scalar(
            select(SyncLog).where(SyncLog.sync_id == log.sync_id)
        )
        assert retrieved is not None
        assert retrieved.records_created == 42


class TestDataRelationships:
    """Test relationships between data models"""

    def test_event_has_matches(self, db_session):
        """Test Event -> Matches relationship"""
        event = db_session.scalars(select(Event)).first()
        assert event is not None
        assert len(event.matches) > 0

    def test_match_has_alliances(self, db_session):
        """Test Match -> Alliances relationship"""
        match = db_session.scalars(select(Match)).first()
        assert match is not None
        assert len(match.alliances) == 2

    def test_match_has_robot_performances(self, db_session):
        """Test Match -> RobotPerformances relationship"""
        match = db_session.scalars(select(Match)).first()
        assert match is not None
        assert len(match.robot_performances) == 6

    def test_team_has_robot_performances(self, db_session):
        """Test Team -> RobotPerformances relationship"""
        team = db_session.scalars(select(Team)).first()
        assert team is not None
        assert len(team.robot_performances) >= 1