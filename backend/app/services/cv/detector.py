"""
YOLOv8 robot detection wrapper for FRC robots.

Uses a fine-tuned YOLOv8 model to detect FRC robots in video frames.
Falls back to yolov8n.pt (COCO) if no fine-tuned model is available.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from .types import Detection

logger = logging.getLogger(__name__)

DUAL_CLASS_MAP: dict[int, str] = {
    0: "robot_red",
    1: "robot_blue",
}

SINGLE_CLASS_MAP: dict[int, str] = {
    0: "robot",
}

COCO_FALLBACK_MAP: dict[int, str] = {
    0: "robot_blue",
}

CONFIDENCE_THRESHOLD = 0.20
IOU_THRESHOLD = 0.45

# Minimum bounding box size in pixels to filter out small game pieces.
# FRC robots are large (28"x28") and appear as big boxes in video.
# 2026 FUEL balls are ~6" diameter — much smaller than robots in frame.
# At 1920x1080 with typical camera distance, robots are at least 60x60px.
# Balls appear as ~15-30px circles and should be filtered out.
MIN_BBOX_WIDTH_PX  = 100   # pixels
MIN_BBOX_HEIGHT_PX = 100   # pixels
MAX_DETECTIONS_PER_FRAME = 8  # FRC has 6 robots max, allow 2 extra for tracking

_RED_LOW1  = np.array([0,   120, 70],  dtype=np.uint8)
_RED_HIGH1 = np.array([10,  255, 255], dtype=np.uint8)
_RED_LOW2  = np.array([170, 120, 70],  dtype=np.uint8)
_RED_HIGH2 = np.array([180, 255, 255], dtype=np.uint8)
_BLUE_LOW  = np.array([100, 100, 70],  dtype=np.uint8)
_BLUE_HIGH = np.array([130, 255, 255], dtype=np.uint8)


def _alliance_from_bumper(frame: np.ndarray, bbox: np.ndarray) -> str:
    """Determine alliance by analysing bumper color in the bottom third of the bbox."""
    x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
    h = y2 - y1
    crop_y1 = max(0, y2 - h // 3)
    crop: np.ndarray = frame[crop_y1:y2, x1:x2]
    if crop.size == 0:
        return "robot_unknown"

    hsv: np.ndarray = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    red1: np.ndarray = cv2.inRange(hsv, _RED_LOW1, _RED_HIGH1)
    red2: np.ndarray = cv2.inRange(hsv, _RED_LOW2, _RED_HIGH2)
    red_mask: np.ndarray = cv2.bitwise_or(red1, red2)
    blue_mask: np.ndarray = cv2.inRange(hsv, _BLUE_LOW, _BLUE_HIGH)

    red_px  = int(cv2.countNonZero(red_mask))
    blue_px = int(cv2.countNonZero(blue_mask))
    total   = crop.shape[0] * crop.shape[1]
    threshold = total * 0.03

    if red_px > blue_px and red_px > threshold:
        return "robot_red"
    if blue_px > red_px and blue_px > threshold:
        return "robot_blue"
    return "robot_unknown"


class RobotDetector:
    """
    Wraps a YOLOv8 model for FRC robot detection.

    Parameters
    ----------
    model_path : path to fine-tuned .pt weights file.
                 If missing, falls back to yolov8n.pt (COCO placeholder).
    device     : 'auto' | 'cuda' | 'cpu'
    confidence_threshold : minimum detection confidence (0–1).
    """

    def __init__(
        self,
        model_path: str | Path = "yolov8n.pt",
        device: str = "auto",
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
    ) -> None:
        try:
            import torch
            from ultralytics import YOLO as _YOLO
        except ImportError as exc:
            raise ImportError(
                "ultralytics and torch are required. "
                "Install with: pip install ultralytics torch"
            ) from exc

        if device == "auto":
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = device
        self.confidence_threshold = confidence_threshold

        model_path = Path(model_path)
        self._fine_tuned = model_path.exists() and model_path.name != "yolov8n.pt"

        if not self._fine_tuned:
            logger.warning(
                "Model '%s' not found — using COCO placeholder yolov8n.pt. "
                "Set YOLO_MODEL_PATH to a fine-tuned FRC model for accurate results.",
                model_path,
            )
            load_path = "yolov8n.pt"
        else:
            load_path = str(model_path)

        logger.info("Loading YOLO model from '%s' on device '%s'", load_path, device)
        from ultralytics import YOLO as _YOLO
        self.model = _YOLO(load_path)
        self.model.to(device)

        if self._fine_tuned:
            names: dict[int, str] = self.model.names  # type: ignore[assignment]
            logger.info("Model classes: %s", names)

            if names.get(0) in ("robot_red", "robot_blue"):
                # Dual-class model with alliance labels
                self._class_map = DUAL_CLASS_MAP
                self._single_class = False
                logger.info("Dual-class model detected (robot_red / robot_blue)")
            elif "robot_red" in names.values() or "robot_blue" in names.values():
                self._class_map = {k: v for k, v in names.items() if v in ("robot_red", "robot_blue")}
                self._single_class = False
                logger.info("Dual-class model (reordered): %s", self._class_map)
            else:
                # Single-class or remapped model (e.g. trained with classes=[1] which
                # remaps robot→0 but may keep original name like 'note').
                # Treat ALL detections from a fine-tuned single-class model as robots
                # and use bumper color to assign alliance.
                self._class_map = {k: "robot" for k in names}
                self._single_class = True
                logger.info("Fine-tuned single-class model — treating all detections as robots, alliance via bumper color")
        else:
            self._class_map = COCO_FALLBACK_MAP
            self._single_class = False

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Run inference on a single BGR frame."""
        results = self.model(
            frame,
            conf=self.confidence_threshold,
            iou=IOU_THRESHOLD,
            verbose=False,
        )[0]

        detections: list[Detection] = []
        for box in results.boxes:
            class_id = int(box.cls)
            class_name = self._class_map.get(class_id)
            if class_name is None:
                continue

            bbox: np.ndarray = box.xyxy[0].cpu().numpy()
            w = float(bbox[2] - bbox[0])
            h = float(bbox[3] - bbox[1])

            # Filter out small detections (game balls, noise).
            # Robots are large objects; 2026 FUEL balls are tiny in frame.
            if w < MIN_BBOX_WIDTH_PX or h < MIN_BBOX_HEIGHT_PX:
                continue

            if self._single_class:
                class_name = _alliance_from_bumper(frame, bbox)

            detections.append(Detection(
                bbox=bbox,
                confidence=float(box.conf),
                class_id=class_id,
                class_name=class_name,
            ))

        # Cap at MAX_DETECTIONS_PER_FRAME — take highest confidence ones.
        # FRC has exactly 6 robots; anything beyond 8 is certainly noise.
        detections.sort(key=lambda d: d.confidence, reverse=True)
        return detections[:MAX_DETECTIONS_PER_FRAME]

    @property
    def is_fine_tuned(self) -> bool:
        return self._fine_tuned