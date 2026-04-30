"""
Perspective transform: pixel coordinates -> FRC field coordinates (feet).

The calibration matrix M is computed once per event/camera angle by
clicking 4 known field anchor points.  After calibration M is stored
in EventCameraCalibration and loaded for every subsequent video.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence

import cv2
import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# FRC 2024 Crescendo full field dimensions
FIELD_WIDTH_FT: float = 54.0
FIELD_HEIGHT_FT: float = 27.0

# Scale factor: field feet -> image-space pixels for numerical stability
_SCALE: float = 20.0  # 20 px per foot


def _field_anchors() -> NDArray[np.float32]:
    """Return the 4 real-world field corner points in scaled pixel space."""
    data: list[list[float]] = [
        [0.0,                             0.0                            ],
        [FIELD_WIDTH_FT  * _SCALE,        0.0                            ],
        [FIELD_WIDTH_FT  * _SCALE,        FIELD_HEIGHT_FT * _SCALE       ],
        [0.0,                             FIELD_HEIGHT_FT * _SCALE       ],
    ]
    return np.array(data, dtype=np.float32)


class FieldPerspectiveTransform:
    """
    Applies (or calibrates) the perspective transform between
    pixel space and FRC field coordinates.

    Parameters
    ----------
    matrix : optional pre-computed 3x3 numpy array.
             When None, apply() returns (None, None) until calibrate() is called.
    """

    def __init__(self, matrix: NDArray[Any] | None = None) -> None:
        self._M: NDArray[Any] | None = matrix

    # -- Calibration -----------------------------------------------------------

    @classmethod
    def from_pixel_points(
        cls, pixel_points: "Sequence[tuple[float | int, float | int]]"
    ) -> "FieldPerspectiveTransform":
        """
        Build transform from 4 pixel points clicked in order [BL, BR, TR, TL].
        pixel_points : list of 4 (x, y) pixel coordinate tuples.
        """
        if len(pixel_points) != 4:
            raise ValueError("Exactly 4 pixel anchor points are required.")

        pixel_data: list[list[float]] = [[p[0], p[1]] for p in pixel_points]
        pixel_pts: NDArray[np.float32] = np.array(pixel_data, dtype=np.float32)
        field_pts: NDArray[np.float32] = _field_anchors()

        M: NDArray[Any] = cv2.getPerspectiveTransform(pixel_pts, field_pts)  # type: ignore[assignment]
        logger.info("Perspective matrix computed from %d anchor points", len(pixel_points))
        return cls(matrix=M)

    @classmethod
    def from_json(cls, matrix_list: list[list[float]]) -> "FieldPerspectiveTransform":
        """Reconstruct from the JSON-serialised form stored in the database."""
        M: NDArray[np.float64] = np.array(matrix_list, dtype=np.float64)
        return cls(matrix=M)

    def to_json(self) -> list[list[float]]:
        """Serialise to a JSON-safe nested list for database storage."""
        if self._M is None:
            raise ValueError("No calibration matrix -- call from_pixel_points() first.")
        result: list[list[float]] = self._M.tolist()
        return result

    # -- Transform -------------------------------------------------------------

    def apply(
        self, pixel_x: float, pixel_y: float
    ) -> tuple[float | None, float | None]:
        """
        Map a single pixel point to field coordinates (feet).
        Returns (None, None) when no calibration matrix is available.
        """
        if self._M is None:
            return None, None

        point: NDArray[np.float32] = np.array(
            [[[pixel_x, pixel_y]]], dtype=np.float32
        )
        transformed: NDArray[Any] = cv2.perspectiveTransform(point, self._M)  # type: ignore[assignment]
        field_x = float(transformed[0][0][0]) / _SCALE
        field_y = float(transformed[0][0][1]) / _SCALE
        return field_x, field_y

    def is_within_bounds(self, field_x: float, field_y: float) -> bool:
        """True when field coordinates are within field boundary (+/- 2 ft margin)."""
        return (
            -2.0 <= field_x <= FIELD_WIDTH_FT + 2.0
            and -2.0 <= field_y <= FIELD_HEIGHT_FT + 2.0
        )

    @property
    def is_calibrated(self) -> bool:
        return self._M is not None