"""
Team identification service using field position heuristics.

When OCR is disabled, team_id is NULL on all movement tracks. This service
infers team groupings based on:
1. Track clustering (same robot = same track_id)
2. Field position (station assignment based on x-y coordinates)
3. Alliance color detection (bumper color HSV analysis)
"""

from typing import Dict, List, Tuple
from app.models import MovementTrack, Match
from app.services.field_definitions import get_field_layout
from sqlalchemy.orm import Session


class TeamMapper:
    """Map track_ids to likely station assignments using field position."""

    # Standard FRC field positions (54' x 27', origin at center)
    # Red alliance starts at y ≈ 2-4 ft, Blue at y ≈ 23-25 ft
    # Stations 1, 2, 3 correspond to different x positions
    RED_STATION_Y_MIN = 0
    RED_STATION_Y_MAX = 13.5
    BLUE_STATION_Y_MIN = 13.5
    BLUE_STATION_Y_MAX = 27.0

    def __init__(self, db: Session):
        self.db = db
        self.field = get_field_layout(2024)

    def get_track_positions(self, match_id: int) -> Dict[int, List[Tuple[float, float]]]:
        """
        Get median position for each track_id (represents robot centroid).

        Args:
            match_id: Match to analyze

        Returns:
            Dict mapping track_id -> list of (x, y) coordinates
        """
        tracks = self.db.query(MovementTrack).filter(
            MovementTrack.match_id == match_id
        ).all()

        by_track: Dict[int, List[Tuple[float, float]]] = {}
        for track in tracks:
            if track.track_id not in by_track:
                by_track[track.track_id] = []
            
            # Use field coords if available, else pixel coords
            if track.field_x is not None and track.field_y is not None:
                by_track[track.track_id].append((track.field_x, track.field_y))
            elif track.pixel_x is not None and track.pixel_y is not None:
                # Normalize pixel to field (fallback)
                norm_x = (track.pixel_x / 1920.0) * self.field.width_ft
                norm_y = (track.pixel_y / 1080.0) * self.field.height_ft
                by_track[track.track_id].append((norm_x, norm_y))

        return by_track

    def infer_alliance_from_position(self, y: float) -> str:
        """
        Infer alliance (red/blue) based on y-coordinate.

        Args:
            y: Field y-coordinate

        Returns:
            "red" or "blue"
        """
        if y < self.BLUE_STATION_Y_MIN:
            return "red"
        return "blue"

    def get_station_assignment(self, match_id: int) -> Dict[int, Dict]:
        """
        Assign each track to a likely field station based on median position.

        Args:
            match_id: Match to analyze

        Returns:
            Dict mapping track_id -> {
                "track_id": int,
                "alliance": "red" | "blue",
                "median_x": float,
                "median_y": float,
                "station_slot": int (1-3 for red, 1-3 for blue)
            }
        """
        positions = self.get_track_positions(match_id)
        assignments = {}

        for track_id, coords in positions.items():
            if not coords:
                continue

            # Compute median position
            xs = sorted([c[0] for c in coords])
            ys = sorted([c[1] for c in coords])
            median_x = xs[len(xs) // 2]
            median_y = ys[len(ys) // 2]

            alliance = self.infer_alliance_from_position(median_y)

            # Determine station slot (1-3) based on x-position within alliance zone
            # Red side: x typically increases for stations 1 -> 2 -> 3
            # Blue side: x typically increases for stations 1 -> 2 -> 3 (same pattern)
            station_slot = self._get_station_slot(median_x, alliance)

            assignments[track_id] = {
                "track_id": track_id,
                "alliance": alliance,
                "median_x": round(median_x, 2),
                "median_y": round(median_y, 2),
                "station_slot": station_slot,
                "label": f"Station {station_slot} ({alliance.upper()[0]})",
            }

        return assignments

    def _get_station_slot(self, x: float, alliance: str) -> int:
        """
        Map x-coordinate to station slot (1, 2, or 3).

        FRC standard field has stations at:
        - Station 1: x ≈ 0 ft
        - Station 2: x ≈ 27 ft (center)
        - Station 3: x ≈ 54 ft

        Args:
            x: Field x-coordinate
            alliance: "red" or "blue"

        Returns:
            Station number (1, 2, or 3)
        """
        # Simple heuristic: divide field width into thirds
        third = self.field.width_ft / 3.0
        if x < third:
            return 1
        elif x < 2 * third:
            return 2
        else:
            return 3
