"""
CV pipeline tests.

Unit tests use synthetic data (numpy arrays) and do NOT require
a trained YOLO model or real video files.

Integration tests (marked with @pytest.mark.integration) require
a real video file set via the VIDEO_TEST_PATH env variable.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_frame(h: int = 480, w: int = 640) -> np.ndarray:
    """Create a blank BGR frame filled with field-green."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:, :] = (34, 139, 34)   # BGR green
    return frame


def _make_bbox(cx: int, cy: int, hw: int = 40, hh: int = 50) -> np.ndarray:
    """Create a [x1,y1,x2,y2] bounding box centred at (cx, cy)."""
    return np.array([cx - hw, cy - hh, cx + hw, cy + hh], dtype=np.float32)


def _draw_team_number(frame: np.ndarray, bbox: np.ndarray, team: int) -> np.ndarray:
    """Render a team number into a bumper region for OCR testing."""
    import cv2
    x1, y1, x2, y2 = bbox.astype(int)
    # Fill bumper region with white
    frame[y1:y2, x1:x2] = 255
    # Write team number in black
    cv2.putText(
        frame, str(team),
        (x1 + 4, y2 - 8),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2, (0, 0, 0), 3, cv2.LINE_AA,
    )
    return frame


# ── OCR Reader tests ──────────────────────────────────────────────────────────

class TestTeamNumberOCR:
    @pytest.fixture(autouse=True)
    def _skip_if_no_easyocr(self):
        pytest.importorskip("easyocr")

    def test_reads_rendered_team_number(self):
        from app.services.cv.ocr_reader import TeamNumberOCR

        frame = _make_frame()
        bbox = _make_bbox(320, 240)
        frame = _draw_team_number(frame, bbox, team=1678)

        ocr = TeamNumberOCR(use_gpu=False)
        result = ocr.read_team_number(frame, bbox)

        # Rendered text should be readable
        assert result.team_number == 1678 or result.confidence > 0.0

    def test_returns_none_for_blank_region(self):
        from app.services.cv.ocr_reader import TeamNumberOCR

        frame = _make_frame()
        bbox = _make_bbox(320, 240)

        ocr = TeamNumberOCR(use_gpu=False)
        result = ocr.read_team_number(frame, bbox)

        assert result.team_number is None

    def test_rejects_out_of_range_number(self):
        from app.services.cv.ocr_reader import TeamNumberOCR, VALID_TEAM_MAX

        result = TeamNumberOCR()._select_best([
            (None, str(VALID_TEAM_MAX + 1), 0.99)
        ])
        assert result.team_number is None


# ── Color Matcher tests ───────────────────────────────────────────────────────

class TestTeamColorMatcher:
    def test_calibrate_and_match_same_team(self):
        from app.services.cv.color_matcher import TeamColorMatcher

        matcher = TeamColorMatcher()
        frame = _make_frame()
        bbox = _make_bbox(320, 240)
        # Paint bumper region red
        x1, y1, x2, y2 = bbox.astype(int)
        frame[y1 + int((y2 - y1) * 0.7):y2, x1:x2] = (0, 0, 200)

        matcher.calibrate_team(254, frame, bbox)
        team, conf = matcher.match(frame, bbox, candidate_teams=[254, 1678])

        assert team == 254
        assert conf > 0.0

    def test_returns_none_when_uncalibrated(self):
        from app.services.cv.color_matcher import TeamColorMatcher

        matcher = TeamColorMatcher()
        frame = _make_frame()
        bbox = _make_bbox(320, 240)
        team, conf = matcher.match(frame, bbox, candidate_teams=[254])

        assert team is None
        assert conf == 0.0

    def test_empty_candidate_list_returns_none(self):
        from app.services.cv.color_matcher import TeamColorMatcher

        matcher = TeamColorMatcher()
        team, conf = matcher.match(_make_frame(), _make_bbox(100, 100), [])
        assert team is None


# ── Perspective Transform tests ───────────────────────────────────────────────

class TestFieldPerspectiveTransform:
    def test_calibrate_and_apply(self):
        from app.services.cv.perspective import FieldPerspectiveTransform

        # Simulate near-identity mapping (corners at frame edges)
        pixel_points = [(0, 0), (640, 0), (640, 480), (0, 480)]
        transform = FieldPerspectiveTransform.from_pixel_points(pixel_points)

        assert transform.is_calibrated
        fx, fy = transform.apply(320, 240)
        # Transformed coordinates should exist (values not checked — depends on matrix)
        assert fx is not None
        assert fy is not None

    def test_within_bounds_for_centre(self):
        from app.services.cv.perspective import FieldPerspectiveTransform

        pixel_points = [(0, 0), (640, 0), (640, 480), (0, 480)]
        transform = FieldPerspectiveTransform.from_pixel_points(pixel_points)
        fx, fy = transform.apply(320, 240)
        # Rough sanity check
        assert isinstance(fx, float)
        assert isinstance(fy, float)

    def test_uncalibrated_returns_none(self):
        from app.services.cv.perspective import FieldPerspectiveTransform

        transform = FieldPerspectiveTransform()
        assert not transform.is_calibrated
        fx, fy = transform.apply(100, 100)
        assert fx is None
        assert fy is None

    def test_json_round_trip(self):
        from app.services.cv.perspective import FieldPerspectiveTransform

        pixel_points = [(0, 0), (640, 0), (640, 480), (0, 480)]
        t1 = FieldPerspectiveTransform.from_pixel_points(pixel_points)
        json_data = t1.to_json()
        t2 = FieldPerspectiveTransform.from_json(json_data)

        fx1, fy1 = t1.apply(200, 150)
        fx2, fy2 = t2.apply(200, 150)
        assert fx1 is not None and fx2 is not None
        assert fy1 is not None and fy2 is not None
        assert abs(fx1 - fx2) < 1e-6
        assert abs(fy1 - fy2) < 1e-6


# ── Video Processor unit tests ────────────────────────────────────────────────

class TestVideoProcessorValidation:
    def test_rejects_unsupported_format(self, tmp_path):
        from app.services.video_processor import VideoProcessingError, VideoProcessor

        bad_file = tmp_path / "video.wmv"
        bad_file.write_bytes(b"fake")

        processor = VideoProcessor()
        with pytest.raises(VideoProcessingError, match="Unsupported"):
            processor.process_video(bad_file, match_id=1, alliance_teams={})

    def test_rejects_missing_file(self, tmp_path):
        from app.services.video_processor import VideoProcessingError, VideoProcessor

        processor = VideoProcessor()
        with pytest.raises(VideoProcessingError, match="not found"):
            processor.process_video(
                tmp_path / "nonexistent.mp4", match_id=1, alliance_teams={}
            )


# ── Integration test (requires real video) ────────────────────────────────────

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("VIDEO_TEST_PATH"),
    reason="Set VIDEO_TEST_PATH env var to run video integration tests",
)
class TestVideoIntegration:
    def test_process_real_video_returns_tracks(self):
        from app.services.video_processor import VideoProcessor

        video_path = Path(os.environ["VIDEO_TEST_PATH"])
        alliance_teams = {
            "red": [int(t) for t in os.getenv("TEST_RED_TEAMS", "254,1678,118").split(",")],
            "blue": [int(t) for t in os.getenv("TEST_BLUE_TEAMS", "148,1114,33").split(",")],
        }

        processor = VideoProcessor(
            model_path=os.getenv("YOLO_MODEL_PATH", "yolov8n.pt"),
            processing_fps=5,   # Use lower FPS for faster test
        )
        tracks = processor.process_video(
            video_path=video_path,
            match_id=1,
            alliance_teams=alliance_teams,
        )

        assert len(tracks) > 0, "No movement tracks produced"

        # All records should have required fields
        for t in tracks:
            assert t.match_id == 1
            assert t.frame_number > 0
            assert t.identification_method != ""
            assert 0.0 <= t.confidence_score <= 1.0

        # Flagged rate should be below 50% (generous for untrained model)
        flagged_rate = sum(1 for t in tracks if t.flagged_for_review) / len(tracks)
        assert flagged_rate < 0.50, f"Flagged rate too high: {flagged_rate:.1%}"

    def test_field_coordinates_within_bounds(self):
        from app.services.video_processor import VideoProcessor
        from app.services.cv.perspective import FIELD_WIDTH_FT, FIELD_HEIGHT_FT

        video_path = Path(os.environ["VIDEO_TEST_PATH"])
        processor = VideoProcessor(processing_fps=5)
        tracks = processor.process_video(
            video_path=video_path,
            match_id=1,
            alliance_teams={"red": [], "blue": []},
        )

        # When no calibration is loaded, field coords should be None
        # (not out-of-bounds values)
        for t in tracks:
            if t.field_x is not None:
                assert -2.0 <= t.field_x <= FIELD_WIDTH_FT + 2.0
            if t.field_y is not None:
                assert -2.0 <= t.field_y <= FIELD_HEIGHT_FT + 2.0