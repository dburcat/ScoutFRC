"""
Tests for trajectory processing from movement tracks.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models import Match, Team, Event, MovementTrack
from app.services.trajectory_processor import TrajectoryProcessor


@pytest.fixture
def setup_match_with_movements(db_session: Session):
    """Create a match with movement tracks for testing."""
    
    # Create event
    event = Event(
        tba_event_key="2024cutsr",
        name="Silicon Valley Regionals",
        city="Santa Clara",
        state_prov="CA",
        country="USA",
        start_date=datetime.now().date(),
        end_date=datetime.now().date(),
        season_year=2024
    )
    db_session.add(event)
    db_session.flush()
    
    # Create teams with unique numbers for testing
    team1 = Team(team_number=9999, team_name="Test Team 1")
    team2 = Team(team_number=8888, team_name="Test Team 2")
    db_session.add_all([team1, team2])
    db_session.flush()
    
    # Create match (without alliances for simplicity)
    match = Match(
        event_id=event.event_id,
        tba_match_key="2024cutsr_f1m1",
        match_type="qualification",
        match_number=42
    )
    db_session.add(match)
    db_session.flush()
    
    # Create movement tracks for team 1690
    # Auto phase (0-15s)
    for i in range(5):
        track = MovementTrack(
            match_id=match.match_id,
            team_id=team1.team_id,
            track_id=i,
            frame_number=i,
            timestamp_ms=i * 1000,  # 0, 1, 2, 3, 4 seconds
            pixel_x=100 + i * 10,
            pixel_y=100 + i * 10,
            field_x=10 + i,
            field_y=10 + i,
            confidence_score=0.95
        )
        db_session.add(track)
    
    # Teleop phase (15-135s)
    for i in range(10):
        track = MovementTrack(
            match_id=match.match_id,
            team_id=team1.team_id,
            track_id=5 + i,
            frame_number=5 + i,
            timestamp_ms=(15 + i * 10) * 1000,  # 15, 25, 35, ... 105 seconds
            pixel_x=200 + i * 10,
            pixel_y=200 + i * 10,
            field_x=20 + i,
            field_y=15 + i,
            confidence_score=0.95
        )
        db_session.add(track)
    
    # Endgame phase (135-150s)
    for i in range(3):
        track = MovementTrack(
            match_id=match.match_id,
            team_id=team1.team_id,
            track_id=15 + i,
            frame_number=15 + i,
            timestamp_ms=(135 + i * 5) * 1000,  # 135, 140, 145 seconds
            pixel_x=300 + i * 10,
            pixel_y=300 + i * 10,
            field_x=30 + i,
            field_y=20 + i,
            confidence_score=0.95
        )
        db_session.add(track)
    
    # Create movement tracks for team 1836
    for i in range(15):
        track = MovementTrack(
            match_id=match.match_id,
            team_id=team2.team_id,
            track_id=100 + i,
            frame_number=i,
            timestamp_ms=i * 10000,  # Every 10 seconds
            pixel_x=400 + i * 10,
            pixel_y=400 + i * 10,
            field_x=5 + i,
            field_y=5 + i,
            confidence_score=0.90
        )
        db_session.add(track)
    
    db_session.commit()
    return match, team1, team2


class TestTrajectoryProcessor:
    """Tests for trajectory processing."""

    def test_initialization(self, db_session: Session):
        """Test processor initialization."""
        processor = TrajectoryProcessor(db_session)
        assert processor.db == db_session

    def test_phase_timings(self):
        """Test phase timing constants."""
        processor = TrajectoryProcessor(None)
        
        assert processor.PHASE_TIMINGS["auto"] == (0, 15)
        assert processor.PHASE_TIMINGS["teleop"] == (15, 135)
        assert processor.PHASE_TIMINGS["endgame"] == (135, 150)

    def test_get_phase_at_time(self):
        """Test phase determination at given times."""
        processor = TrajectoryProcessor(None)
        
        # Auto phase
        assert processor._get_phase_at_time(5) == "auto"
        assert processor._get_phase_at_time(0) == "auto"
        assert processor._get_phase_at_time(14.9) == "auto"
        
        # Teleop phase
        assert processor._get_phase_at_time(15) == "teleop"
        assert processor._get_phase_at_time(75) == "teleop"
        assert processor._get_phase_at_time(134.9) == "teleop"
        
        # Endgame phase
        assert processor._get_phase_at_time(135) == "endgame"
        assert processor._get_phase_at_time(140) == "endgame"
        assert processor._get_phase_at_time(150) == "endgame"
        
        # Out of bounds
        assert processor._get_phase_at_time(-1) is None
        assert processor._get_phase_at_time(151) is None

    def test_compute_distance(self):
        """Test distance calculation."""
        processor = TrajectoryProcessor(None)
        
        # Straight line
        coords = [(0, 0), (3, 4)]
        distance = processor._compute_distance(coords)
        assert distance == 5.0  # 3-4-5 triangle
        
        # Multiple points
        coords = [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
        distance = processor._compute_distance(coords)
        assert abs(distance - 4.0) < 0.01  # Square perimeter
        
        # No movement
        coords = [(5, 5)] * 3
        distance = processor._compute_distance(coords)
        assert distance == 0

    def test_get_match_trajectories(self, db_session: Session, setup_match_with_movements):
        """Test retrieving all trajectories for a match."""
        match, team1, team2 = setup_match_with_movements
        
        processor = TrajectoryProcessor(db_session)
        trajectories = processor.get_match_trajectories(match.match_id)
        
        # Should have 2 teams
        assert len(trajectories) == 2
        
        # Team 1 should be present
        assert team1.team_id in trajectories
        traj1 = trajectories[team1.team_id]
        assert traj1["team_id"] == team1.team_id
        assert len(traj1["all_coordinates"]) == 18  # 5 auto + 10 teleop + 3 endgame
        assert traj1["stats"]["distance_traveled"] > 0
        assert traj1["stats"]["total_points"] == 18

    def test_get_team_trajectory(self, db_session: Session, setup_match_with_movements):
        """Test retrieving trajectory for specific team."""
        match, team1, team2 = setup_match_with_movements
        
        processor = TrajectoryProcessor(db_session)
        traj = processor.get_team_trajectory(match.match_id, team1.team_id)
        
        assert traj is not None
        assert traj["team_id"] == team1.team_id
        assert len(traj["all_coordinates"]) == 18
        
        # Non-existent team
        traj = processor.get_team_trajectory(match.match_id, 9999)
        assert traj is None

    def test_get_phase_trajectories_all(self, db_session: Session, setup_match_with_movements):
        """Test retrieving all trajectories (no phase filter)."""
        match, team1, team2 = setup_match_with_movements
        
        processor = TrajectoryProcessor(db_session)
        phase_trajs = processor.get_phase_trajectories(match.match_id, "all")
        
        # Should have 2 teams
        assert len(phase_trajs) == 2
        
        # Team 1 should have all points
        assert len(phase_trajs[team1.team_id]) == 18

    def test_get_phase_trajectories_auto(self, db_session: Session, setup_match_with_movements):
        """Test retrieving auto phase trajectories."""
        match, team1, team2 = setup_match_with_movements
        
        processor = TrajectoryProcessor(db_session)
        phase_trajs = processor.get_phase_trajectories(match.match_id, "auto")
        
        # Should have data for team 1 (has auto phase data)
        assert len(phase_trajs[team1.team_id]) == 5

    def test_get_phase_trajectories_teleop(self, db_session: Session, setup_match_with_movements):
        """Test retrieving teleop phase trajectories."""
        match, team1, team2 = setup_match_with_movements
        
        processor = TrajectoryProcessor(db_session)
        phase_trajs = processor.get_phase_trajectories(match.match_id, "teleop")
        
        # Should have data for team 1
        assert len(phase_trajs[team1.team_id]) == 10

    def test_get_phase_trajectories_endgame(self, db_session: Session, setup_match_with_movements):
        """Test retrieving endgame phase trajectories."""
        match, team1, team2 = setup_match_with_movements
        
        processor = TrajectoryProcessor(db_session)
        phase_trajs = processor.get_phase_trajectories(match.match_id, "endgame")
        
        # Should have data for team 1
        assert len(phase_trajs[team1.team_id]) == 3

    def test_interpolate_trajectory_upsample(self):
        """Test upsampling trajectory."""
        processor = TrajectoryProcessor(None)
        
        # Simple 2-point trajectory
        coords = [(0, 0), (10, 10)]
        interp = processor.interpolate_trajectory(coords, num_points=5)
        
        assert len(interp) == 5
        # First and last should be close to originals
        assert abs(interp[0][0] - 0) < 0.1
        assert abs(interp[-1][0] - 10) < 0.1

    def test_interpolate_trajectory_downsample(self):
        """Test downsampling trajectory."""
        processor = TrajectoryProcessor(None)
        
        # Many-point trajectory
        coords = [(i, i) for i in range(100)]
        interp = processor.interpolate_trajectory(coords, num_points=10)
        
        assert len(interp) == 10

    def test_interpolate_trajectory_single_point(self):
        """Test interpolation with single point."""
        processor = TrajectoryProcessor(None)
        
        coords = [(5, 5)]
        interp = processor.interpolate_trajectory(coords, num_points=5)
        
        # Should return original
        assert len(interp) == 1
        assert interp[0] == (5, 5)

    def test_match_not_found(self, db_session: Session):
        """Test handling of non-existent match."""
        processor = TrajectoryProcessor(db_session)
        trajectories = processor.get_match_trajectories(9999)
        
        assert trajectories == {}


class TestTrajectoryPhaseOrganization:
    """Tests for phase-based trajectory organization."""

    def test_phases_populated_correctly(self, db_session: Session, setup_match_with_movements):
        """Test that trajectories are correctly organized by phase."""
        match, team1, team2 = setup_match_with_movements
        
        processor = TrajectoryProcessor(db_session)
        trajectories = processor.get_match_trajectories(match.match_id)
        
        traj = trajectories[team1.team_id]
        
        # Check phase data
        assert len(traj["phases"]["auto"]) == 5
        assert len(traj["phases"]["teleop"]) == 10
        assert len(traj["phases"]["endgame"]) == 3

    def test_statistics_accuracy(self, db_session: Session, setup_match_with_movements):
        """Test that statistics are correctly calculated."""
        match, team1, team2 = setup_match_with_movements
        
        processor = TrajectoryProcessor(db_session)
        trajectories = processor.get_match_trajectories(match.match_id)
        
        traj = trajectories[team1.team_id]
        
        # Total points should match coordinate count
        assert traj["stats"]["total_points"] == len(traj["all_coordinates"])
        
        # Distance should be positive
        assert traj["stats"]["distance_traveled"] > 0
