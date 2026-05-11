"""
EasyOCR-based team number extraction from robot bumper regions.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

import cv2
import numpy as np

import easyocr  # type: ignore[import]

logger = logging.getLogger(__name__)

VALID_TEAM_MIN = 1
VALID_TEAM_MAX = 9999
MARGIN_RATIO = 0.25
MIN_DIM = 64


@dataclass
class OCRResult:
    team_number: int | None
    confidence: float
    raw_text: str


class TeamNumberOCR:
    """
    Wraps EasyOCR to read FRC team numbers from bumper regions.
    Reader is lazily initialised on first use.
    """

    def __init__(self, use_gpu: bool = False) -> None:
        self._use_gpu = use_gpu
        self._reader: easyocr.Reader | None = None

    def read_team_number(self, frame: np.ndarray, bbox: np.ndarray) -> OCRResult:
        reader = self._get_reader()
        region = self._extract_bumper_region(frame, bbox)
        preprocessed = self._preprocess(region)

        try:
            results = reader.readtext(preprocessed, allowlist="0123456789")
        except Exception as exc:
            logger.debug("EasyOCR failed: %s", exc)
            return OCRResult(team_number=None, confidence=0.0, raw_text="")

        return self._select_best(results)

    def _get_reader(self) -> easyocr.Reader:
        if self._reader is None:
            import fcntl

            # Use pre-baked model dir when available (set in Dockerfile)
            model_dir: str | None = os.environ.get("EASYOCR_MODULE_PATH")

            logger.info("Initialising EasyOCR reader (gpu=%s)…", self._use_gpu)
            lock_path = "/tmp/easyocr_init.lock"
            with open(lock_path, "w") as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                try:
                    if model_dir:
                        self._reader = easyocr.Reader(
                            ["en"],
                            gpu=self._use_gpu,
                            verbose=False,
                            model_storage_directory=model_dir,
                        )
                    else:
                        self._reader = easyocr.Reader(
                            ["en"],
                            gpu=self._use_gpu,
                            verbose=False,
                        )
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
        return self._reader

    def _extract_bumper_region(self, frame: np.ndarray, bbox: np.ndarray) -> np.ndarray:
        x1, y1, x2, y2 = bbox.astype(int)
        h, w = frame.shape[:2]
        mx = int((x2 - x1) * MARGIN_RATIO)
        my = int((y2 - y1) * MARGIN_RATIO)
        rx1 = max(0, x1 - mx)
        ry1 = max(0, y1 - my)
        rx2 = min(w, x2 + mx)
        ry2 = min(h, y2 + my)
        return frame[ry1:ry2, rx1:rx2]

    def _preprocess(self, region: np.ndarray) -> np.ndarray:
        rh, rw = region.shape[:2]
        if rh < MIN_DIM or rw < MIN_DIM:
            scale = MIN_DIM / min(rh, rw)
            region = cv2.resize(region, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        enhanced = cv2.equalizeHist(gray)
        thresh = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2,
        )
        return thresh

    def _select_best(self, results: list) -> OCRResult:  # type: ignore[type-arg]
        for _bbox, text, confidence in sorted(results, key=lambda r: -r[2]):
            digits = re.sub(r"[^0-9]", "", text)
            if not digits:
                continue
            try:
                team_num = int(digits)
                if VALID_TEAM_MIN <= team_num <= VALID_TEAM_MAX:
                    return OCRResult(
                        team_number=team_num,
                        confidence=float(confidence),
                        raw_text=text,
                    )
            except ValueError:
                continue
        return OCRResult(team_number=None, confidence=0.0, raw_text="")