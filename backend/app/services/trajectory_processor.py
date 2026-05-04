"""
Trajectory computation from movement track data.

Extracts and organizes movement traces for visualization and analysis.
"""

from typing import List, Dict, Tuple
from datetime import timedelta
from sqlalchemy.orm import Session

from app.models import MovementTrack, Match
from app.services.field_definitions import get_field_layout


class TrajectoryProcessor:
    """Process movement tracks into organized trajectory data for visualization."""

    PHASE_TIMINGS = {
        # Timings in seconds (FRC 2024 Crescendo)
        "auto": (0, 15),
        "teleop": (15, 135),
        "endgame": (135, 150),
    }

    def __init__(self, db: Session):
        self.db = db

    def get_match_trajectories(
        self,
        match_id: int,
        include_all_phases: bool = True,
    ) -> Dict[int, Dict]:
        """
        Get all movement trajectories for a match, organized by team.
        
        Args:
            match_id: Match ID
            include_all_phases: Include auto, teleop, endgame data
            
        Returns:
            Dict mapping team_id to trajectory data
        """
        # Query all movement tracks for this match
        tracks = self.db.query(MovementTrack).filter(
            MovementTrack.match_id == match_id,
            MovementTrack.field_x.isnot(None),  # Has field coordinates
            MovementTrack.field_y.isnot(None),
        ).order_by(MovementTrack.timestamp_ms).all()

        if not tracks:
            return {}

        # Get match info for duration
        match = self.db.query(Match).filter(Match.match_id == match_id).first()
        match_duration_s = 150 if match is None else 150  # FRC match is always 150s

        # Group by team
        trajectories_by_team: Dict[int, Dict] = {}

        for track in tracks:
            if track.team_id not in trajectories_by_team:
                trajectories_by_team[track.team_id] = {
                    "team_id": track.team_id,
                    "alliance": track.team_id,  # Could query for actual alliance
                    "all_coordinates": [],
                    "phases": {
                        "auto": [],
                        "teleop": [],
                        "endgame": [],
                    },
                    "stats": {
                        "total_points": 0,
                        "distance_traveled": 0.0,
                    },
                }

            # Determine phase
            phase_name = self._get_phase_at_time(track.timestamp_ms / 1000.0)

            coord = (track.field_x, track.field_y)
            trajectories_by_team[track.team_id]["all_coordinates"].append(coord)

            if include_all_phases and phase_name:
                trajectories_by_team[track.team_id]["phases"][phase_name].append(coord)

        # Compute stats
        for team_id, traj in trajectories_by_team.items():
            traj["stats"]["total_points"] = len(traj["all_coordinates"])
            traj["stats"]["distance_traveled"] = self._compute_distance(
                traj["all_coordinates"]
            )

        return trajectories_by_team

    def get_team_trajectory(
        self,
        match_id: int,
        team_id: int,
    ) -> Dict | None:
        """
        Get trajectory for a specific team in a match.
        
        Args:
            match_id: Match ID
            team_id: Team ID
            
        Returns:
            Trajectory dict or None if not found
        """
        trajectories = self.get_match_trajectories(match_id)
        return trajectories.get(team_id)

    def get_phase_trajectories(
        self,
        match_id: int,
        phase: str = "all",
    ) -> Dict[int, List[Tuple[float, float]]]:
        """
        Get trajectories for a specific phase.
        
        Args:
            match_id: Match ID
            phase: "auto", "teleop", "endgame", or "all"
            
        Returns:
            Dict mapping team_id to list of coordinates
        """
        trajectories = self.get_match_trajectories(match_id)
        
        if phase == "all":
            return {
                team_id: traj["all_coordinates"]
                for team_id, traj in trajectories.items()
            }

        return {
            team_id: traj["phases"].get(phase, [])
            for team_id, traj in trajectories.items()
            if phase in traj["phases"]
        }

    @staticmethod
    def _get_phase_at_time(time_s: float) -> str | None:
        """Determine which phase a timestamp falls into."""
        if 0 <= time_s < 15:
            return "auto"
        elif 15 <= time_s < 135:
            return "teleop"
        elif 135 <= time_s <= 150:
            return "endgame"
        return None

    @staticmethod
    def _compute_distance(coordinates: List[Tuple[float, float]]) -> float:
        """
        Compute total distance traveled from coordinate list.
        
        Args:
            coordinates: List of (x, y) tuples
            
        Returns:
            Total distance in feet
        """
        if len(coordinates) < 2:
            return 0.0

        total_distance = 0.0
        for i in range(len(coordinates) - 1):
            x1, y1 = coordinates[i]
            x2, y2 = coordinates[i + 1]
            
            # Euclidean distance
            distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            total_distance += distance

        return total_distance

    @staticmethod
    def interpolate_trajectory(
        coordinates: List[Tuple[float, float]],
        num_points: int = 100,
    ) -> List[Tuple[float, float]]:
        """
        Interpolate trajectory to fixed number of points.
        
        Useful for animation/playback with consistent speed.
        
        Args:
            coordinates: Original coordinates
            num_points: Target number of points
            
        Returns:
            Interpolated coordinate list
        """
        if len(coordinates) <= 1:
            return coordinates

        if len(coordinates) >= num_points:
            # Downsample
            step = len(coordinates) / num_points
            return [
                coordinates[int(i * step)]
                for i in range(num_points)
            ]

        # Upsample with linear interpolation
        import numpy as np
        
        xs = np.array([c[0] for c in coordinates])
        ys = np.array([c[1] for c in coordinates])
        
        # Parameter t along the path
        t = np.linspace(0, 1, len(coordinates))
        t_interp = np.linspace(0, 1, num_points)
        
        xs_interp = np.interp(t_interp, t, xs)
        ys_interp = np.interp(t_interp, t, ys)
        
        return list(zip(xs_interp, ys_interp))
