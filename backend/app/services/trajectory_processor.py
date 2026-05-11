"""
Trajectory computation from movement track data.

Extracts and organizes movement traces for visualization and analysis.
"""

from typing import List, Dict, Tuple
from datetime import timedelta
from sqlalchemy.orm import Session

from app.models import MovementTrack, Match
from app.services.field_definitions import get_field_layout
from app.services.team_mapper import TeamMapper


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
        # Query all movement tracks for this match — prefer field coords but
        # fall back to pixel coords so visualization works without calibration
        tracks = self.db.query(MovementTrack).filter(
            MovementTrack.match_id == match_id,
        ).order_by(MovementTrack.timestamp_ms).all()

        if not tracks:
            return {}

        # Determine if we have field coordinates or need to use pixel fallback
        has_field_coords = any(
            t.field_x is not None and t.field_y is not None for t in tracks
        )

        # When no calibration matrix was used, normalize pixel coords to field dims
        field = get_field_layout(2024)
        pixel_xs = [t.pixel_x for t in tracks if t.pixel_x is not None]
        pixel_ys = [t.pixel_y for t in tracks if t.pixel_y is not None]
        px_min = min(pixel_xs, default=0)
        px_max = max(pixel_xs, default=1920)
        py_min = min(pixel_ys, default=0)
        py_max = max(pixel_ys, default=1080)

        def _coords(track: MovementTrack) -> tuple[float, float]:
            if track.field_x is not None and track.field_y is not None:
                return (track.field_x, track.field_y)
            # Normalize pixel -> field feet
            nx = (track.pixel_x - px_min) / max(px_max - px_min, 1)
            ny = (track.pixel_y - py_min) / max(py_max - py_min, 1)
            return (round(nx * field.width_ft, 2), round(ny * field.height_ft, 2))

        # FRC matches are always 150s (15s auto + 135s teleop/endgame)

        # Group by team_id when available; fall back to negative track_id as a
        # synthetic key so unidentified robots still appear in the visualization
        # instead of being silently dropped.
        trajectories_by_team: Dict[int, Dict] = {}

        for track in tracks:
            if track.team_id is not None:
                group_key: int = track.team_id
            else:
                # Negative track_id never collides with a real team PK
                group_key = -(track.track_id)

            if group_key not in trajectories_by_team:
                trajectories_by_team[group_key] = {
                    "team_id": group_key,
                    "alliance": "red",  # unknown; router overwrites from Alliance table
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
            team_id = group_key

            # Determine phase
            phase_name = self._get_phase_at_time(track.timestamp_ms / 1000.0)

            coord = _coords(track)
            trajectories_by_team[team_id]["all_coordinates"].append(coord)

            if include_all_phases and phase_name:
                trajectories_by_team[team_id]["phases"][phase_name].append(coord)

        # Compute stats
        for team_id, traj in trajectories_by_team.items():
            traj["stats"]["total_points"] = len(traj["all_coordinates"])
            traj["stats"]["distance_traveled"] = self._compute_distance(
                traj["all_coordinates"]
            )

        # Enrich with field-position assignments for team identification
        # when team_id is not available (OCR disabled)
        self._enrich_with_station_assignments(match_id, trajectories_by_team)

        return trajectories_by_team

    def _enrich_with_station_assignments(
        self,
        match_id: int,
        trajectories: Dict[int, Dict],
    ) -> None:
        """
        Add field-position-based team and station info when team_ids are negative
        (indicating missing OCR data).

        Modifies trajectories in-place to add:
        - "station_slot": Station number (1-3) based on x-position
        - "inferred_alliance": Alliance color (red/blue) based on y-position

        Args:
            match_id: Match ID
            trajectories: Dictionary of trajectories to enrich
        """
        mapper = TeamMapper(self.db)
        assignments = mapper.get_station_assignment(match_id)

        for team_id, traj in trajectories.items():
            # Only apply heuristics for synthetic team IDs (negative = unidentified tracks)
            if team_id >= 0:
                continue

            track_id = -team_id  # Extract original track_id
            if track_id in assignments:
                assignment = assignments[track_id]
                # Update alliance from position-based detection
                traj["alliance"] = assignment["alliance"]
                # Add station info for reference
                traj["station"] = {
                    "slot": assignment["station_slot"],
                    "label": assignment["label"],
                    "median_x": assignment["median_x"],
                    "median_y": assignment["median_y"],
                }

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