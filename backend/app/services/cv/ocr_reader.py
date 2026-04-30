"""
EasyOCR-based team number extraction from robot bumper regions.

Reads the 1–4 digit FRC team number from a cropped bumper image,
applying preprocessing to improve accuracy under arena lighting.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import cv2
import numpy as np

import easyocr  # type: ignore[import]

logger = logging.getLogger(__name__)

VALID_TEAM_MIN = 1
VALID_TEAM_MAX = 9999
MARGIN_RATIO = 0.25     # Expand bbox by 25% to capture full bumper text
MIN_DIM = 64            # Minimum crop dimension before upscaling


@dataclass
class OCRResult:
    team_number: int | None
    confidence: float
    raw_text: str


class TeamNumberOCR:
    """
    Wraps EasyOCR to read FRC team numbers from bumper regions.

    The reader is lazily initialised on first use so that importing
    this module does not trigger EasyOCR's model download.
    """

    def __init__(self, use_gpu: bool = False) -> None:
        self._use_gpu = use_gpu
        self._reader: "easyocr.Reader | None" = None  # lazy init

    # ── Public API ────────────────────────────────────────────────────────────

    def read_team_number(
        self, frame: np.ndarray, bbox: np.ndarray
    ) -> OCRResult:
        """
        Extract the team number from the bumper region of a robot.

        Parameters
        ----------
        frame : BGR image (full video frame)
        bbox  : [x1, y1, x2, y2] bounding box of the robot

        Returns
        -------
        OCRResult with team_number=None if no valid number was found.
        """
        reader = self._get_reader()
        region = self._extract_bumper_region(frame, bbox)
        preprocessed = self._preprocess(region)

        try:
            results = reader.readtext(preprocessed, allowlist="0123456789")
        except Exception as exc:
            logger.debug("EasyOCR failed: %s", exc)
            return OCRResult(team_number=None, confidence=0.0, raw_text="")

        return self._select_best(results)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_reader(self) -> "easyocr.Reader":
        if self._reader is None:
            try:
                import easyocr  # type: ignore[import]
            except ImportError as exc:
                raise ImportError(
                    "easyocr is required for OCR team number reading. "
                    "Install with: pip install easyocr"
                ) from exc
            logger.info("Initialising EasyOCR reader (gpu=%s)…", self._use_gpu)
            self._reader = easyocr.Reader(["en"], gpu=self._use_gpu, verbose=False)
        return self._reader

    def _extract_bumper_region(
        self, frame: np.ndarray, bbox: np.ndarray
    ) -> np.ndarray:
        x1, y1, x2, y2 = bbox.astype(int)
        h, w = frame.shape[:2]
        mx = int((x2 - x1) * MARGIN_RATIO)
        my = int((y2 - y1) * MARGIN_RATIO)
        rx1, ry1 = max(0, x1 - mx), max(0, y1 - my)
        rx2, ry2 = min(w, x2 + mx), min(h, y2 + my)
        return frame[ry1:ry2, rx1:rx2]

    def _preprocess(self, region: np.ndarray) -> np.ndarray:
        # Upscale tiny crops
        rh, rw = region.shape[:2]
        if rh < MIN_DIM or rw < MIN_DIM:
            scale = MIN_DIM / min(rh, rw)
            region = cv2.resize(
                region, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC
            )
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        enhanced = cv2.equalizeHist(gray)
        thresh = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2,
        )
        return thresh

    def _select_best(self, results: list) -> OCRResult:
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