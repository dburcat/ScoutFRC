"""
Tests for trajectories API endpoints.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.models import Match, Team, Event, MovementTrack, User
from app.core.security import create_access_token


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def authenticated_headers(db):
    """Create an authenticated user and return auth headers."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed",
        is_active=True
    )
    db.add(user)
    db.commit()
    
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def match_with_trajectories(db):
    """Create a match with movement tracks."""
    
    # Create event
    event = Event(
        tba_id="2024cutsr",
        name="Test Event",
        event_code="test",
        year=2024,
        state="CA",
        country="USA"
    )
    db.add(event)
    db.flush()
    
    # Create match
    match = Match(
        event_id=event.id,
        match_number=1,
        scheduled_time=datetime.utcnow(),
        status="completed"
    )
    db.add(match)
    db.flush()
    
    # Create movement tracks
    for i in range(10):
        track = MovementTrack(
            match_id=match.id,
            team_id=1690,
            timestamp_ms=i * 1000,
            field_x=10 + i,
            field_y=10 + i,
            confidence=0.95
        )
        db.add(track)
    
    db.commit()
    return match


class TestTrajectoriesEndpoints:
    """Tests for trajectories API endpoints."""

    def test_get_match_trajectories(self, client, match_with_trajectories, authenticated_headers):
        """Test GET /matches/{match_id}/trajectories"""
        
        response = client.get(
            f"/matches/{match_with_trajectories.id}/trajectories",
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["match_id"] == match_with_trajectories.id
        assert "teams" in data
        assert 1690 in data["teams"]
        assert data["field_width"] == 54
        assert data["field_height"] == 27

    def test_get_match_trajectories_phase_filter(self, client, match_with_trajectories, authenticated_headers):
        """Test GET /matches/{match_id}/trajectories with phase filter."""
        
        response = client.get(
            f"/matches/{match_with_trajectories.id}/trajectories?phase=auto",
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should still have teams but with filtered coordinates
        assert "teams" in data

    def test_get_match_trajectories_invalid_phase(self, client, match_with_trajectories, authenticated_headers):
        """Test GET /matches/{match_id}/trajectories with invalid phase."""
        
        response = client.get(
            f"/matches/{match_with_trajectories.id}/trajectories?phase=invalid",
            headers=authenticated_headers
        )
        
        assert response.status_code == 422

    def test_get_match_trajectories_not_found(self, client, authenticated_headers):
        """Test GET /matches/{match_id}/trajectories with non-existent match."""
        
        response = client.get(
            "/matches/9999/trajectories",
            headers=authenticated_headers
        )
        
        assert response.status_code == 404

    def test_get_match_heatmap(self, client, match_with_trajectories, authenticated_headers):
        """Test GET /matches/{match_id}/heatmap"""
        
        response = client.get(
            f"/matches/{match_with_trajectories.id}/heatmap",
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["match_id"] == match_with_trajectories.id
        assert "bins" in data
        assert "max_intensity" in data
        assert "total_points" in data

    def test_get_match_heatmap_single_team(self, client, match_with_trajectories, authenticated_headers):
        """Test GET /matches/{match_id}/heatmap with team filter."""
        
        response = client.get(
            f"/matches/{match_with_trajectories.id}/heatmap?team_id=1690",
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have bins for this team
        assert len(data["bins"]) > 0

    def test_get_match_heatmap_nonexistent_team(self, client, match_with_trajectories, authenticated_headers):
        """Test GET /matches/{match_id}/heatmap with non-existent team."""
        
        response = client.get(
            f"/matches/{match_with_trajectories.id}/heatmap?team_id=9999",
            headers=authenticated_headers
        )
        
        assert response.status_code == 404

    def test_get_match_heatmap_bin_size(self, client, match_with_trajectories, authenticated_headers):
        """Test GET /matches/{match_id}/heatmap with custom bin size."""
        
        response = client.get(
            f"/matches/{match_with_trajectories.id}/heatmap?bin_size=2.0",
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "bins" in data

    def test_get_field_layout(self, client, match_with_trajectories, authenticated_headers):
        """Test GET /matches/{match_id}/field-layout"""
        
        response = client.get(
            f"/matches/{match_with_trajectories.id}/field-layout",
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "width_ft" in data
        assert "height_ft" in data
        assert "zones" in data

    def test_unauthorized_access(self, client, match_with_trajectories):
        """Test that endpoints require authentication."""
        
        response = client.get(f"/matches/{match_with_trajectories.id}/trajectories")
        assert response.status_code == 401
        
        response = client.get(f"/matches/{match_with_trajectories.id}/heatmap")
        assert response.status_code == 401
        
        response = client.get(f"/matches/{match_with_trajectories.id}/field-layout")
        assert response.status_code == 401


class TestTrajectoryResponseFormat:
    """Tests for response data format and structure."""

    def test_trajectory_response_schema(self, client, match_with_trajectories, authenticated_headers):
        """Test that trajectory response matches expected schema."""
        
        response = client.get(
            f"/matches/{match_with_trajectories.id}/trajectories",
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert isinstance(data["teams"], dict)
        for team_id, team_data in data["teams"].items():
            assert isinstance(team_id, (int, str))
            assert "team_id" in team_data
            assert "alliance" in team_data
            assert "coordinates" in team_data
            assert "stats" in team_data
            assert isinstance(team_data["coordinates"], list)
            assert isinstance(team_data["stats"], dict)

    def test_heatmap_response_schema(self, client, match_with_trajectories, authenticated_headers):
        """Test that heatmap response matches expected schema."""
        
        response = client.get(
            f"/matches/{match_with_trajectories.id}/heatmap",
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert isinstance(data["bins"], list)
        if len(data["bins"]) > 0:
            bin = data["bins"][0]
            assert "x_min" in bin
            assert "x_max" in bin
            assert "y_min" in bin
            assert "y_max" in bin
            assert "center_x" in bin
            assert "center_y" in bin
            assert "count" in bin
            assert "intensity" in bin

    def test_coordinates_are_numeric(self, client, match_with_trajectories, authenticated_headers):
        """Test that coordinates are numeric values."""
        
        response = client.get(
            f"/matches/{match_with_trajectories.id}/trajectories",
            headers=authenticated_headers
        )
        
        data = response.json()
        for team_data in data["teams"].values():
            for coord in team_data["coordinates"]:
                assert len(coord) == 2
                assert isinstance(coord[0], (int, float))
                assert isinstance(coord[1], (int, float))


class TestPhaseFiltering:
    """Tests for phase filtering functionality."""

    def test_all_phases_included(self, client, match_with_trajectories, authenticated_headers):
        """Test that 'all' phase returns all coordinates."""
        
        response = client.get(
            f"/matches/{match_with_trajectories.id}/trajectories?phase=all",
            headers=authenticated_headers
        )
        
        assert response.status_code == 200
        all_data = response.json()
        all_coords = len(all_data["teams"][1690]["coordinates"])
        
        # All phase should have the most coordinates
        assert all_coords > 0

    def test_phase_heatmap_filtering(self, client, match_with_trajectories, authenticated_headers):
        """Test heatmap filtering by phase."""
        
        response_all = client.get(
            f"/matches/{match_with_trajectories.id}/heatmap?phase=all",
            headers=authenticated_headers
        )
        
        response_auto = client.get(
            f"/matches/{match_with_trajectories.id}/heatmap?phase=auto",
            headers=authenticated_headers
        )
        
        assert response_all.status_code == 200
        assert response_auto.status_code == 200
        
        all_data = response_all.json()
        auto_data = response_auto.json()
        
        # Auto phase should have fewer or equal points
        assert auto_data["total_points"] <= all_data["total_points"]
