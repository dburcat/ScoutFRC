"""
Heatmap generation from movement trajectory data.

Converts raw MovementTrack coordinates into 2D binned heatmap data for visualization.
"""

from typing import List, Tuple
import numpy as np
from dataclasses import dataclass, field


@dataclass
class HeatmapBin:
    """A single cell in the heatmap grid."""
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    count: int  # Number of points in this bin
    center_x: float = field(init=False)
    center_y: float = field(init=False)

    def __post_init__(self):
        """Calculate bin center from bounds."""
        self.center_x = (self.x_min + self.x_max) / 2
        self.center_y = (self.y_min + self.y_max) / 2

    def to_dict(self) -> dict:
        return {
            "x_min": self.x_min,
            "x_max": self.x_max,
            "y_min": self.y_min,
            "y_max": self.y_max,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "count": self.count,
            "intensity": self.count,  # For visualization
        }


class HeatmapGenerator:
    """Generate 2D spatial heatmaps from movement trajectories."""

    def __init__(
        self,
        field_width: float = 54.0,
        field_height: float = 27.0,
        bin_size: float = 1.0,  # 1 foot bins
    ):
        """
        Initialize heatmap generator.
        
        Args:
            field_width: Field width in feet (default: 54)
            field_height: Field height in feet (default: 27)
            bin_size: Size of each grid cell in feet (default: 1)
        """
        self.field_width = field_width
        self.field_height = field_height
        self.bin_size = bin_size
        self.num_bins_x = int(np.ceil(field_width / bin_size))
        self.num_bins_y = int(np.ceil(field_height / bin_size))

    def generate_heatmap(
        self,
        coordinates: List[Tuple[float, float]],
    ) -> List[HeatmapBin]:
        """
        Generate heatmap from list of (x, y) coordinates.
        
        Args:
            coordinates: List of (x, y) tuples in field space
            
        Returns:
            List of HeatmapBin objects with counts
        """
        # Create 2D histogram
        heatmap = np.zeros((self.num_bins_y, self.num_bins_x), dtype=np.uint32)

        # Bin each coordinate
        for x, y in coordinates:
            # Handle out-of-bounds gracefully
            if not (0 <= x <= self.field_width and 0 <= y <= self.field_height):
                continue

            bin_x = int(min(x / self.bin_size, self.num_bins_x - 1))
            bin_y = int(min(y / self.bin_size, self.num_bins_y - 1))
            heatmap[bin_y, bin_x] += 1

        # Convert to HeatmapBin objects
        bins: List[HeatmapBin] = []
        for bin_y in range(self.num_bins_y):
            for bin_x in range(self.num_bins_x):
                count = int(heatmap[bin_y, bin_x])
                if count == 0:
                    continue  # Skip empty bins

                x_min = bin_x * self.bin_size
                x_max = x_min + self.bin_size
                y_min = bin_y * self.bin_size
                y_max = y_min + self.bin_size

                bin_obj = HeatmapBin(
                    x_min=x_min,
                    x_max=x_max,
                    y_min=y_min,
                    y_max=y_max,
                    count=count,
                )
                bins.append(bin_obj)

        return bins

    def generate_normalized_heatmap(
        self,
        coordinates: List[Tuple[float, float]],
    ) -> Tuple[List[HeatmapBin], float]:
        """
        Generate heatmap with normalized intensity values (0-1).
        
        Returns:
            Tuple of (heatmap_bins, max_intensity)
        """
        bins = self.generate_heatmap(coordinates)
        
        if not bins:
            return [], 0.0

        # Find max count for normalization
        max_count = max(bin.count for bin in bins)
        
        return bins, float(max_count)

    def get_heatmap_stats(
        self,
        coordinates: List[Tuple[float, float]],
    ) -> dict:
        """
        Get statistics about the heatmap.
        
        Args:
            coordinates: List of (x, y) tuples
            
        Returns:
            Dictionary with statistics
        """
        if not coordinates:
            return {
                "total_points": 0,
                "max_intensity": 0,
                "mean_intensity": 0,
                "occupied_bins": 0,
            }

        xs = [c[0] for c in coordinates]
        ys = [c[1] for c in coordinates]

        return {
            "total_points": len(coordinates),
            "mean_x": float(np.mean(xs)),
            "mean_y": float(np.mean(ys)),
            "min_x": float(np.min(xs)),
            "max_x": float(np.max(xs)),
            "min_y": float(np.min(ys)),
            "max_y": float(np.max(ys)),
            "std_x": float(np.std(xs)),
            "std_y": float(np.std(ys)),
            "bounds": {
                "x_min": float(np.min(xs)),
                "x_max": float(np.max(xs)),
                "y_min": float(np.min(ys)),
                "y_max": float(np.max(ys)),
            },
        }

    def generate_trajectory(
        self,
        coordinates: List[Tuple[float, float]],
    ) -> List[dict]:
        """
        Convert coordinates to trajectory points with indices.
        
        Args:
            coordinates: List of (x, y) tuples
            
        Returns:
            List of trajectory point dicts
        """
        return [
            {
                "index": i,
                "x": x,
                "y": y,
            }
            for i, (x, y) in enumerate(coordinates)
        ]
