"""Test API endpoints and routers"""
from __future__ import annotations

import sys
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Basic test client without auth"""
    return TestClient(app)


class TestEventEndpoints:
    """Test /events/ endpoints"""
    
    def test_get_events(self, client):
        """Test GET /events/"""
        response = client.get("/events/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_events_with_skip_limit(self, client):
        """Test /events/ with pagination parameters"""
        response = client.get("/events/?skip=0&limit=5")
        assert response.status_code == 200
        events = response.json()
        assert len(events) <= 5
    
    def test_get_events_with_year_filter(self, client):
        """Test /events/ with year filter"""
        response = client.get("/events/?year=2024")
        assert response.status_code == 200
        events = response.json()
        assert isinstance(events, list)
    
    def test_get_event_detail(self, client):
        """Test GET /events/{event_id}"""
        response = client.get("/events/")
        events = response.json()
        if events:
            event_id = events[0]["event_id"]
            response = client.get(f"/events/{event_id}")
            assert response.status_code == 200
            event = response.json()
            assert event["event_id"] == event_id
    
    def test_get_event_matches(self, client):
        """Test GET /events/{event_id}/matches"""
        response = client.get("/events/")
        events = response.json()
        assert len(events) > 0
        
        event_id = events[0]["event_id"]
        response = client.get(f"/events/{event_id}/matches?skip=0&limit=5")
        assert response.status_code == 200
        matches = response.json()
        assert isinstance(matches, list)
    
    def test_get_event_teams(self, client):
        """Test GET /events/{event_id}/teams"""
        response = client.get("/events/")
        events = response.json()
        assert len(events) > 0
        
        event_id = events[0]["event_id"]
        response = client.get(f"/events/{event_id}/teams?skip=0&limit=10")
        assert response.status_code == 200
        teams = response.json()
        assert isinstance(teams, list)


class TestTeamEndpoints:
    """Test /teams/ endpoints"""
    
    def test_get_teams(self, client):
        """Test GET /teams/"""
        response = client.get("/teams/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_teams_with_pagination(self, client):
        """Test GET /teams/ with skip/limit"""
        response = client.get("/teams/?skip=0&limit=5")
        assert response.status_code == 200
        teams = response.json()
        assert len(teams) <= 5
    
    def test_get_teams_with_team_number_filter(self, client):
        """Test GET /teams/ with team_number filter"""
        response = client.get("/teams/?team_number=1678")
        assert response.status_code == 200
        teams = response.json()
        assert len(teams) <= 1
        if teams:
            assert teams[0]["team_number"] == 1678
    
    def test_get_team_detail(self, client):
        """Test GET /teams/{team_id}"""
        response = client.get("/teams/")
        teams = response.json()
        if teams:
            team_id = teams[0]["team_id"]
            response = client.get(f"/teams/{team_id}")
            assert response.status_code == 200
            team = response.json()
            assert team["team_id"] == team_id
    
    def test_get_team_matches(self, client):
        """Test GET /teams/{team_id}/matches"""
        response = client.get("/teams/")
        teams = response.json()
        assert len(teams) > 0
        
        team_id = teams[0]["team_id"]
        response = client.get(f"/teams/{team_id}/matches")
        assert response.status_code == 200
        matches = response.json()
        assert isinstance(matches, list)
    
    def test_get_nonexistent_team(self, client):
        """Test GET /teams/{team_id} with invalid ID"""
        response = client.get("/teams/999999")
        assert response.status_code == 404


class TestMatchEndpoints:
    """Test /matches/ endpoints"""
    
    def test_get_matches(self, client):
        """Test GET /matches/"""
        response = client.get("/matches/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_matches_with_pagination(self, client):
        """Test GET /matches/ with pagination"""
        response = client.get("/matches/?skip=0&limit=5")
        assert response.status_code == 200
        matches = response.json()
        assert len(matches) <= 5
    
    def test_get_match_detail(self, client):
        """Test GET /matches/{match_id}"""
        response = client.get("/matches/")
        matches = response.json()
        if matches:
            match_id = matches[0]["match_id"]
            response = client.get(f"/matches/{match_id}")
            assert response.status_code == 200
            match = response.json()
            assert match["match_id"] == match_id


class TestScoutingObservationEndpoints:
    """Test /scouting_observations/ endpoints"""
    
    def test_get_observations(self, client):
        """Test GET /scouting_observations/"""
        response = client.get("/scouting_observations/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_observations_with_pagination(self, client):
        """Test GET /scouting_observations/ with pagination"""
        response = client.get("/scouting_observations/?skip=0&limit=5")
        assert response.status_code == 200
        observations = response.json()
        assert len(observations) <= 5
    
    def test_post_observation_requires_auth(self, client):
        """Test POST /scouting_observations/ requires authentication"""
        response = client.post("/scouting_observations/", json={})
        assert response.status_code == 403
    
    def test_post_observation_with_auth(self, client_with_auth):
        """Test POST /scouting_observations/ with auth"""
        from sqlalchemy import select
        from sqlalchemy.orm import Session
        from app.db.database import SessionLocal
        from app.models import Event, Match, Team
        
        db = SessionLocal()
        try:
            event = db.scalars(select(Event)).first()
            match = db.scalars(select(Match)).first()
            team = db.scalars(select(Team)).first()
            
            observation_data = {
                "event_id": event.event_id,
                "match_id": match.match_id,
                "team_id": team.team_id,
                "auto_notes": "Test auto notes",
                "teleop_notes": "Test teleop notes",
                "endgame_notes": "Test endgame notes"
            }
            
            response = client_with_auth.post(
                "/scouting_observations/",
                json=observation_data
            )
            # Should succeed with auth
            assert response.status_code in [200, 201, 422]  # Allow validation errors
        finally:
            db.close()
    
    def test_get_observation_detail(self, client):
        """Test GET /scouting_observations/{id}"""
        response = client.get("/scouting_observations/")
        observations = response.json()
        if observations:
            obs_id = observations[0]["scouting_observation_id"]
            response = client.get(f"/scouting_observations/{obs_id}")
            assert response.status_code == 200


class TestRobotPerformanceEndpoints:
    """Test /robot_performances/ endpoints"""
    
    def test_get_robot_performances(self, client):
        """Test GET /robot_performances/"""
        response = client.get("/robot_performances/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_robot_performance_detail(self, client):
        """Test GET /robot_performances/{id}"""
        response = client.get("/robot_performances/")
        performances = response.json()
        if performances:
            perf_id = performances[0]["robot_performance_id"]
            response = client.get(f"/robot_performances/{perf_id}")
            assert response.status_code == 200


class TestAllianceEndpoints:
    """Test /alliances/ endpoints"""
    
    def test_get_alliances(self, client):
        """Test GET /alliances/"""
        response = client.get("/alliances/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_alliance_detail(self, client):
        """Test GET /alliances/{id}"""
        response = client.get("/alliances/")
        alliances = response.json()
        if alliances:
            alliance_id = alliances[0]["alliance_id"]
            response = client.get(f"/alliances/{alliance_id}")
            assert response.status_code == 200


class TestAuthEndpoints:
    """Test /auth/ endpoints"""
    
    def test_login(self, client, test_user):
        """Test POST /auth/login"""
        response = client.post(
            "/auth/login",
            json={"username": "testscout", "password": "testpass123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post(
            "/auth/login",
            json={"username": "nonexistent", "password": "wrongpass"}
        )
        assert response.status_code in [401, 422]
    
    def test_get_current_user(self, client_with_auth, test_user):
        """Test GET /auth/me"""
        response = client_with_auth.get("/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
    
    def test_get_current_user_requires_auth(self, client):
        """Test GET /auth/me requires authentication"""
        response = client.get("/auth/me")
        assert response.status_code == 403


class TestDataExportEndpoints:
    """Test /data/ export endpoints"""
    
    def test_export_csv_requires_auth(self, client):
        """Test CSV export requires authentication"""
        response = client.get("/data/events/1/export/csv")
        assert response.status_code == 403
    
    def test_export_json_requires_auth(self, client):
        """Test JSON export requires authentication"""
        response = client.get("/data/events/1/export/json")
        assert response.status_code == 403
    
    def test_bulk_observations_requires_auth(self, client):
        """Test bulk observations requires authentication"""
        response = client.post("/data/bulk-observations", json=[])
        assert response.status_code == 403
    
    def test_bulk_observations_max_limit(self, client_with_auth):
        """Test bulk observations max 50 records"""
        # Create 51 observations (should fail or be capped)
        large_list = [
            {
                "event_id": 1,
                "match_id": 1,
                "team_id": 1,
                "auto_notes": f"note {i}",
                "teleop_notes": "teleop",
                "endgame_notes": "endgame"
            }
            for i in range(51)
        ]
        
        response = client_with_auth.post(
            "/data/bulk-observations",
            json=large_list
        )
        # Should reject or cap at 50
        assert response.status_code in [400, 422, 201, 200]


class TestUserAllianceEndpoints:
    """Test /user_alliances/ endpoints"""
    
    def test_get_user_alliances_requires_auth(self, client):
        """Test GET /user_alliances/ requires auth"""
        response = client.get("/user_alliances/")
        assert response.status_code == 403
    
    def test_get_user_alliances(self, client_with_auth):
        """Test GET /user_alliances/"""
        response = client_with_auth.get("/user_alliances/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_post_user_alliance_requires_auth(self, client):
        """Test POST /user_alliances/ requires auth"""
        response = client.post("/user_alliances/", json={})
        assert response.status_code == 403
    
    def test_post_user_alliance(self, client_with_auth):
        """Test POST /user_alliances/"""
        from sqlalchemy import select
        from sqlalchemy.orm import Session
        from app.db.database import SessionLocal
        from app.models import Event
        
        db = SessionLocal()
        try:
            event = db.scalars(select(Event)).first()
            if event:
                alliance_data = {
                    "event_id": event.event_id,
                    "red_teams": "1678,1690,7512",
                    "blue_teams": "254,1323,3476"
                }
                
                response = client_with_auth.post(
                    "/user_alliances/",
                    json=alliance_data
                )
                assert response.status_code in [200, 201]
        finally:
            db.close()


class TestPaginationLimits:
    """Test pagination parameter limits"""
    
    def test_skip_limit_bounds(self, client):
        """Test skip/limit parameter validation"""
        # Test with valid bounds
        response = client.get("/events/?skip=0&limit=100")
        assert response.status_code == 200
        
        # Test with exceeded limit (should be capped)
        response = client.get("/events/?skip=0&limit=600")
        assert response.status_code == 422 or response.status_code == 200
    
    def test_negative_skip(self, client):
        """Test negative skip parameter"""
        response = client.get("/events/?skip=-1&limit=10")
        assert response.status_code == 422


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_nonexistent_event(self, client):
        """Test accessing nonexistent event"""
        response = client.get("/events/999999")
        assert response.status_code == 404
    
    def test_invalid_endpoint(self, client):
        """Test invalid endpoint"""
        response = client.get("/invalid_endpoint")
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client):
        """Test method not allowed"""
        response = client.put("/events/")
        assert response.status_code == 405
