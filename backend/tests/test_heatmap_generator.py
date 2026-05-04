"""
Tests for heatmap generation algorithm.
"""

import pytest
import numpy as np
from app.services.heatmap_generator import HeatmapGenerator, HeatmapBin


class TestHeatmapBin:
    """Tests for HeatmapBin data class."""

    def test_bin_creation(self):
        """Test creating a heatmap bin."""
        bin = HeatmapBin(
            x_min=0, x_max=1, y_min=0, y_max=1, count=5
        )
        assert bin.x_min == 0
        assert bin.x_max == 1
        assert bin.y_min == 0
        assert bin.y_max == 1
        assert bin.center_x == 0.5
        assert bin.center_y == 0.5
        assert bin.count == 5


class TestHeatmapGenerator:
    """Tests for heatmap generation."""

    def test_initialization(self):
        """Test creating a heatmap generator."""
        gen = HeatmapGenerator(field_width=54, field_height=27, bin_size=1.0)
        assert gen.field_width == 54
        assert gen.field_height == 27
        assert gen.bin_size == 1.0

    def test_empty_coordinates(self):
        """Test heatmap generation with no coordinates."""
        gen = HeatmapGenerator(field_width=54, field_height=27, bin_size=1.0)
        bins = gen.generate_heatmap([])
        assert len(bins) == 0

    def test_single_point(self):
        """Test heatmap generation with single point."""
        gen = HeatmapGenerator(field_width=54, field_height=27, bin_size=1.0)
        bins = gen.generate_heatmap([(27, 13.5)])
        assert len(bins) == 1
        assert bins[0].count == 1

    def test_clustered_points(self):
        """Test heatmap generation with clustered points."""
        gen = HeatmapGenerator(field_width=54, field_height=27, bin_size=1.0)
        
        # Points close together
        coordinates = [(27.2, 13.5), (27.3, 13.5), (27.4, 13.6), (27.5, 13.7)]
        bins = gen.generate_heatmap(coordinates)
        
        # Should create 1 bin with 4 points (all within same 1-foot cell)
        assert len(bins) == 1
        assert bins[0].count == 4

    def test_dispersed_points(self):
        """Test heatmap generation with dispersed points."""
        gen = HeatmapGenerator(field_width=54, field_height=27, bin_size=1.0)
        
        # Points in different bins
        coordinates = [(5, 5), (10, 10), (20, 15), (30, 8)]
        bins = gen.generate_heatmap(coordinates)
        
        # Should create 4 bins with 1 point each
        assert len(bins) == 4
        for bin in bins:
            assert bin.count == 1

    def test_bin_size_effect(self):
        """Test that larger bin size produces fewer bins."""
        coordinates = [(i, i) for i in range(0, 30, 1)]
        
        gen_small = HeatmapGenerator(field_width=54, field_height=27, bin_size=1.0)
        bins_small = gen_small.generate_heatmap(coordinates)
        
        gen_large = HeatmapGenerator(field_width=54, field_height=27, bin_size=5.0)
        bins_large = gen_large.generate_heatmap(coordinates)
        
        # Larger bins should result in fewer bins
        assert len(bins_large) < len(bins_small)

    def test_normalized_heatmap(self):
        """Test normalized heatmap generation."""
        gen = HeatmapGenerator(field_width=54, field_height=27, bin_size=1.0)
        coordinates = [(5, 5)] * 10 + [(10, 10)] * 5
        
        bins, max_count = gen.generate_normalized_heatmap(coordinates)
        
        # Max count should be 10
        assert max_count == 10.0
        
        # Should have 2 bins
        assert len(bins) == 2
        
        # Find bins by count
        bin_10 = [b for b in bins if b.count == 10][0]
        bin_5 = [b for b in bins if b.count == 5][0]
        assert bin_10.count == 10
        assert bin_5.count == 5

    def test_heatmap_stats(self):
        """Test heatmap statistics calculation."""
        gen = HeatmapGenerator(field_width=54, field_height=27, bin_size=1.0)
        coordinates = [(10 + i, 10 + i) for i in range(10)]
        
        stats = gen.get_heatmap_stats(coordinates)
        
        assert "mean_x" in stats
        assert "mean_y" in stats
        assert "std_x" in stats
        assert "std_y" in stats
        assert "min_x" in stats
        assert "max_x" in stats
        assert "min_y" in stats
        assert "max_y" in stats
        assert "bounds" in stats
        assert "total_points" in stats
        
        # Verify bounds structure
        bounds = stats["bounds"]
        assert "x_min" in bounds
        assert "x_max" in bounds
        assert "y_min" in bounds
        assert "y_max" in bounds

    def test_trajectory_generation(self):
        """Test trajectory generation."""
        gen = HeatmapGenerator(field_width=54, field_height=27, bin_size=1.0)
        coordinates = [(0, 0), (10, 10), (20, 20), (30, 15)]
        
        trajectory = gen.generate_trajectory(coordinates)
        
        assert len(trajectory) == len(coordinates)
        # Each point should have index
        for i, point in enumerate(trajectory):
            assert point["index"] == i
            assert point["x"] == coordinates[i][0]
            assert point["y"] == coordinates[i][1]

    def test_out_of_bounds_points(self):
        """Test handling of out-of-bounds points."""
        gen = HeatmapGenerator(field_width=54, field_height=27, bin_size=1.0)
        
        # Points outside field
        coordinates = [
            (27, 13.5),  # Valid center
            (-5, -5),    # Out of bounds
            (60, 35),    # Out of bounds
        ]
        
        bins = gen.generate_heatmap(coordinates)
        
        # Should handle gracefully (NumPy histogram handles this)
        assert len(bins) >= 1
        
        # Valid point should be in bins
        center_bin = [b for b in bins if abs(b.center_x - 27) < 1]
        assert len(center_bin) > 0

    def test_dense_point_cloud(self):
        """Test performance with dense point cloud."""
        gen = HeatmapGenerator(field_width=54, field_height=27, bin_size=1.0)
        
        # Create dense grid
        coordinates = [
            (x + 0.1 * y, y + 0.1 * x)
            for x in np.linspace(5, 50, 50)
            for y in np.linspace(5, 25, 50)
        ]
        
        bins = gen.generate_heatmap(coordinates)
        
        # Should produce many bins
        assert len(bins) > 100
        
        # All should have positive counts
        for bin in bins:
            assert bin.count > 0

    def test_bin_center_coordinates(self):
        """Test that bin centers are correctly calculated."""
        gen = HeatmapGenerator(field_width=54, field_height=27, bin_size=1.0)
        bins = gen.generate_heatmap([(5.5, 10.5)])
        
        assert len(bins) == 1
        # Center should be within bin bounds
        assert bins[0].x_min <= bins[0].center_x <= bins[0].x_max
        assert bins[0].y_min <= bins[0].center_y <= bins[0].y_max


class TestHeatmapIntegration:
    """Integration tests for heatmap generation with realistic data."""

    def test_match_trajectory_heatmap(self):
        """Test generating heatmap from simulated match trajectory."""
        gen = HeatmapGenerator(field_width=54, field_height=27, bin_size=1.0)
        
        # Simulate robot movement: start → speaker → amp → stage
        trajectory = [
            # Start position
            (27, 10),
            # Move to speaker
            (5, 5),
            (4, 6),
            (3, 7),
            # Linger at speaker
            (3, 7),
            (3, 7),
            # Move to amp
            (25, 26),
            (26, 26),
            (27, 26),
            # Move to stage
            (27, 14),
            (27, 13),
        ]
        
        bins = gen.generate_heatmap(trajectory)
        
        assert len(bins) > 0
        
        # Find high-intensity bins (speaker and amp)
        speaker_bin = max(
            (b for b in bins if b.center_x < 10),
            key=lambda b: b.count,
            default=None
        )
        assert speaker_bin is not None
        assert speaker_bin.count >= 2
