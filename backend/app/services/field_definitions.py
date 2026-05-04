"""
Field geometry and layout definitions for FRC games.

Supports multi-season field layouts with accurate dimensions and game elements.
Currently configured for 2024 Crescendo season.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Point:
    """2D point in field coordinates (feet)."""
    x: float
    y: float

    def to_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)


@dataclass
class Zone:
    """A rectangular zone on the field (e.g., scoring area)."""
    name: str
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    scoring_points: int = 0
    color: str = "#cccccc"

    def contains(self, x: float, y: float) -> bool:
        """Check if point is within this zone."""
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "min_x": self.min_x,
            "max_x": self.max_x,
            "min_y": self.min_y,
            "max_y": self.max_y,
            "scoring_points": self.scoring_points,
            "color": self.color,
        }


class FieldLayout:
    """
    FRC field layout definition for a specific game year.
    
    Coordinates are in feet, with origin at the center of the field.
    Field dimensions are typically 54' × 27'.
    """

    def __init__(self, year: int, width_ft: float, height_ft: float):
        self.year = year
        self.width_ft = width_ft
        self.height_ft = height_ft
        self.zones: Dict[str, Zone] = {}

    def add_zone(self, zone: Zone) -> None:
        """Register a scoring or game zone."""
        self.zones[zone.name] = zone

    def normalize_coordinates(self, x: float, y: float) -> tuple[float, float]:
        """Normalize coordinates to field space (0-54, 0-27)."""
        # Assuming input is already in field space; identity transform
        return (x, y)

    def get_zone_at(self, x: float, y: float) -> Zone | None:
        """Get the zone containing the given coordinates."""
        for zone in self.zones.values():
            if zone.contains(x, y):
                return zone
        return None

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "width_ft": self.width_ft,
            "height_ft": self.height_ft,
            "zones": {name: zone.to_dict() for name, zone in self.zones.items()},
        }


# ── 2024 Crescendo Field Layout ────────────────────────────────────────────

def create_2024_crescendo_field() -> FieldLayout:
    """
    Create 2024 Crescendo field layout.
    
    Field dimensions: 54' × 27'
    Game elements:
    - Speakers (blue & red, 2 pts each)
    - Amps (blue & red, 1 pt each)
    - Stage (center, endgame zone)
    - Source zones (for note intake)
    """
    field = FieldLayout(2024, 54.0, 27.0)

    # Scoring zones
    # Blue speaker: x: 0-8, y: 4-8.5
    field.add_zone(Zone(
        name="blue_speaker",
        min_x=0, max_x=8,
        min_y=4, max_y=8.5,
        scoring_points=2,
        color="#4169E1",  # Royal blue
    ))

    # Red speaker: x: 46-54, y: 4-8.5
    field.add_zone(Zone(
        name="red_speaker",
        min_x=46, max_x=54,
        min_y=4, max_y=8.5,
        scoring_points=2,
        color="#DC143C",  # Crimson
    ))

    # Blue amp: x: 0-4, y: 21.5-27
    field.add_zone(Zone(
        name="blue_amp",
        min_x=0, max_x=4,
        min_y=21.5, max_y=27,
        scoring_points=1,
        color="#1E90FF",  # Dodger blue
    ))

    # Red amp: x: 50-54, y: 21.5-27
    field.add_zone(Zone(
        name="red_amp",
        min_x=50, max_x=54,
        min_y=21.5, max_y=27,
        scoring_points=1,
        color="#FF4500",  # Orange red
    ))

    # Center stage (endgame zone): x: 17-37, y: 8-19
    field.add_zone(Zone(
        name="stage",
        min_x=17, max_x=37,
        min_y=8, max_y=19,
        scoring_points=0,
        color="#FFD700",  # Gold
    ))

    # Blue source: x: 0-8, y: 0-4
    field.add_zone(Zone(
        name="blue_source",
        min_x=0, max_x=8,
        min_y=0, max_y=4,
        scoring_points=0,
        color="#E0FFFF",  # Cyan
    ))

    # Red source: x: 46-54, y: 0-4
    field.add_zone(Zone(
        name="red_source",
        min_x=46, max_x=54,
        min_y=0, max_y=4,
        scoring_points=0,
        color="#FFE4B5",  # Moccasin
    ))

    return field


# ── Field registry ────────────────────────────────────────────────────────

_FIELDS: Dict[int, FieldLayout] = {
    2024: create_2024_crescendo_field(),
}


def get_field_layout(year: int) -> FieldLayout:
    """Get field layout for a specific game year."""
    if year not in _FIELDS:
        raise ValueError(f"Field layout not available for year {year}")
    return _FIELDS[year]


def get_available_years() -> List[int]:
    """Get list of available field layout years."""
    return sorted(_FIELDS.keys())
