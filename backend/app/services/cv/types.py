"""Shared dataclasses used across all CV service modules."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Detection:
    """Raw output from YOLOv8 for a single object."""
    bbox: np.ndarray          # [x1, y1, x2, y2] in pixel coordinates
    confidence: float
    class_id: int
    class_name: str           # "robot_red" | "robot_blue" | "game_piece" | "field_element"

    @property
    def center_x(self) -> float:
        return float((self.bbox[0] + self.bbox[2]) / 2)

    @property
    def center_y(self) -> float:
        return float((self.bbox[1] + self.bbox[3]) / 2)

    @property
    def width(self) -> float:
        return float(self.bbox[2] - self.bbox[0])

    @property
    def height(self) -> float:
        return float(self.bbox[3] - self.bbox[1])

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def alliance(self) -> str | None:
        if self.class_name == "robot_red":
            return "red"
        if self.class_name == "robot_blue":
            return "blue"
        return None


@dataclass
class TeamIdentification:
    """Result of the cascaded team identification pipeline."""
    team_number: int | None
    method: str               # IdentificationMethod value
    confidence: float
    flagged: bool = False
    flag_reason: str | None = None


@dataclass
class TrackedRobot:
    """Output of the tracker for a single confirmed robot in a frame."""
    track_id: int
    bbox: np.ndarray          # [x1, y1, x2, y2]
    team_number: int | None
    identification_method: str
    confidence: float
    bbox_size_change: float = 0.0
    configuration_changed: bool = False
    is_predicted: bool = False   # True = Kalman gap-fill, no real detection
    team_number_visible: bool = False
    flagged: bool = False
    flag_reason: str | None = None
    field_x: float | None = None
    field_y: float | None = None

    @property
    def bbox_center_x(self) -> float:
        return float((self.bbox[0] + self.bbox[2]) / 2)

    @property
    def bbox_center_y(self) -> float:
        return float((self.bbox[1] + self.bbox[3]) / 2)

    @property
    def bbox_width(self) -> float:
        return float(self.bbox[2] - self.bbox[0])

    @property
    def bbox_height(self) -> float:
        return float(self.bbox[3] - self.bbox[1])