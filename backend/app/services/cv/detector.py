"""
YOLOv8 robot detection wrapper.

Uses a fine-tuned YOLOv8 model to detect FRC robots in video frames.
Falls back to YOLOv8n (general) if no fine-tuned model is available.
GPU is used automatically when available; CPU fallback is transparent.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from .types import Detection

logger = logging.getLogger(__name__)

# Classes the fine-tuned model is trained to detect
SUPPORTED_CLASSES: dict[int, str] = {
    0: "robot_red",
    1: "robot_blue",
    2: "game_piece",
    3: "field_element",
}

# When using pretrained COCO weights as placeholder, remap 'person' → robot
# (useful for smoke-testing without a fine-tuned model)
COCO_FALLBACK_CLASSES: dict[int, str] = {
    0: "robot_blue",   # person class → treat as blue robot for testing
}

CONFIDENCE_THRESHOLD = 0.45
IOU_THRESHOLD = 0.50


class RobotDetector:
    """
    Wraps a YOLOv8 model for FRC robot detection.

    Parameters
    ----------
    model_path:
        Path to a fine-tuned .pt or .onnx weights file.
        If the path does not exist, downloads YOLOv8n (pretrained COCO)
        as a placeholder — useful in development before fine-tuning.
    device:
        "auto" | "cuda" | "cpu"
    confidence_threshold:
        Minimum detection confidence (0–1).
    """

    def __init__(
        self,
        model_path: str | Path = "yolov8n.pt",
        device: str = "auto",
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
    ) -> None:
        try:
            import torch
            from ultralytics import YOLO
        except ImportError as exc:
            raise ImportError(
                "ultralytics and torch are required for video processing. "
                "Install them with: pip install ultralytics torch"
            ) from exc

        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = device
        self.confidence_threshold = confidence_threshold
        self._fine_tuned = Path(model_path).exists()

        if not self._fine_tuned:
            logger.warning(
                "Model file '%s' not found — loading pretrained YOLOv8n as placeholder. "
                "Detection results will be inaccurate until a fine-tuned model is provided.",
                model_path,
            )
            model_path = "yolov8n.pt"

        logger.info("Loading YOLO model from '%s' on device '%s'", model_path, device)
        self.model = YOLO(str(model_path))
        self.model.to(device)

        # Choose class map based on whether we have a fine-tuned model
        self._class_map = SUPPORTED_CLASSES if self._fine_tuned else COCO_FALLBACK_CLASSES

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """
        Run inference on a single BGR frame.

        Returns a list of Detection objects for all supported classes.
        """
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
                continue  # Ignore unsupported classes

            detections.append(
                Detection(
                    bbox=box.xyxy[0].cpu().numpy(),
                    confidence=float(box.conf),
                    class_id=class_id,
                    class_name=class_name,
                )
            )

        return detections

    @property
    def is_fine_tuned(self) -> bool:
        """True if using a fine-tuned FRC model; False if using COCO placeholder."""
        return self._fine_tuned