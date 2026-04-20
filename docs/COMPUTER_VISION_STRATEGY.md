# ScouterFRC — Computer Vision Strategy

> **Version:** 1.0  
> **Status:** Planning  
> **Scope:** End-to-end robot tracking strategy including detection, identification, re-identification under configuration changes, and team number recovery

---

## Table of Contents

1. [Overview](#1-overview)
2. [Pipeline Architecture](#2-pipeline-architecture)
3. [YOLOv8 Detection](#3-yolov8-detection)
4. [DeepSORT Multi-Object Tracking](#4-deepsort-multi-object-tracking)
5. [Team Number Identification via OCR](#5-team-number-identification-via-ocr)
6. [Color-Based Robot Identification](#6-color-based-robot-identification)
7. [Robot Re-Identification After Configuration Changes](#7-robot-re-identification-after-configuration-changes)
8. [Team Number Recovery After Rotation / Occlusion](#8-team-number-recovery-after-rotation--occlusion)
9. [Kalman Filter Prediction & Track Continuity](#9-kalman-filter-prediction--track-continuity)
10. [Perspective Transform & Field Coordinate Mapping](#10-perspective-transform--field-coordinate-mapping)
11. [MovementTrack Data Model](#11-movementtrack-data-model)
12. [Video Processor Implementation](#12-video-processor-implementation)
13. [Celery Task Integration](#13-celery-task-integration)
14. [Confidence Scoring & Flagging for Review](#14-confidence-scoring--flagging-for-review)
15. [Manual Review Dashboard](#15-manual-review-dashboard)
16. [Accuracy Metrics & Validation](#16-accuracy-metrics--validation)
17. [Model Training & Fine-Tuning](#17-model-training--fine-tuning)
18. [GPU Infrastructure](#18-gpu-infrastructure)
19. [Performance Benchmarks](#19-performance-benchmarks)
20. [Testing Strategy](#20-testing-strategy)

---

## 1. Overview

ScouterFRC analyzes official FRC match videos to produce objective, per-robot performance data. The computer vision pipeline must reliably track up to six robots simultaneously across a 150-second match while handling the unique challenges of FRC competition footage:

| Challenge | Cause | Solution |
|-----------|-------|---------|
| Team number unreadable | Robot rotation, occlusion, camera angle | Multi-method identification (OCR → color → Kalman) |
| Robot height/shape changes | Mechanism deployment (arms, elevators, intakes) | Size-change detection + re-identification check |
| Robot occlusion | Robots overlapping in frame | Kalman prediction during gaps; re-confirmation after |
| Camera shake | Arena handheld/fixed cameras | Frame stabilization preprocessing |
| Field glare / lighting variation | Arena lighting, LEDs | YOLOv8 fine-tuned on diverse lighting conditions |
| Multiple similar-looking robots | Common bumper designs | Alliance color + position as disambiguation |

### Identification Method Priority

The pipeline uses a **cascaded identification** strategy — each method is attempted in order and the first high-confidence match is used:

```
1. OCR (team number directly read)          → highest confidence
2. DeepSORT track continuity                → high confidence (continuous track)
3. Color profile matching                   → medium confidence
4. Alliance + position spatial constraint   → medium confidence (eliminates options)
5. Kalman position prediction               → lower confidence (temporal only)
6. UNKNOWN (flag for manual review)         → no confident match
```

---

## 2. Pipeline Architecture

### End-to-End Processing Flow

```
Video File (S3)
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 1: Preprocessing                                         │
│  - FFmpeg decode to frames at configurable FPS (default: 10)    │
│  - Frame stabilization (optional, for shaky footage)            │
│  - Resize to 640×640 for YOLO input                             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 2: Object Detection (YOLOv8)                             │
│  Input:  640×640 normalized frame                               │
│  Output: [{bbox, confidence, class}]                            │
│  Classes: robot_red, robot_blue, game_piece, field_element      │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 3: Team Identification (per detection)                   │
│  3a. OCR — attempt to read team number from bumper region       │
│  3b. Color matching — compare to calibrated team color profiles │
│  3c. Alliance + position — spatial constraint filtering         │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 4: Multi-Object Tracking (DeepSORT)                      │
│  Input:  detections with team_id candidates + frame             │
│  Output: [{track_id, bbox, team_id, confidence}]                │
│  - Maintains appearance embeddings per robot                    │
│  - Kalman filter predicts positions during occlusion            │
│  - Re-identifies after configuration changes                    │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 5: Perspective Transform                                  │
│  Pixel (x, y) → Field coordinates (feet from corner)           │
│  Calibrated once per season per camera angle                    │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 6: Persist to Database                                   │
│  Batch-write MovementTrack rows                                 │
│  Trigger analytics task on completion                           │
└─────────────────────────────────────────────────────────────────┘
```

### Module Structure

```
backend/app/services/
  ├── video_processor.py        — Main pipeline orchestrator
  ├── cv/
  │     ├── __init__.py
  │     ├── detector.py         — YOLOv8 wrapper
  │     ├── tracker.py          — DeepSORT wrapper + re-ID logic
  │     ├── team_identifier.py  — Cascaded identification (OCR, color, spatial)
  │     ├── ocr_reader.py       — EasyOCR team number extraction
  │     ├── color_matcher.py    — Color histogram matching per team
  │     ├── kalman_predictor.py — Standalone Kalman filter for gap filling
  │     └── perspective.py      — Perspective transform calibration + application
  └── cv/models/                — Trained YOLOv8 .pt weight files
```

---

## 3. YOLOv8 Detection

### Model Configuration

```python
# backend/app/services/cv/detector.py
from ultralytics import YOLO
import torch

class RobotDetector:
    SUPPORTED_CLASSES = {
        0: "robot_red",
        1: "robot_blue",
        2: "game_piece",
        3: "field_element",
    }
    CONFIDENCE_THRESHOLD = 0.45
    IOU_THRESHOLD = 0.5

    def __init__(self, model_path: str, device: str = "auto"):
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.model = YOLO(model_path)
        self.model.to(device)

    def detect(self, frame: np.ndarray) -> list[Detection]:
        results = self.model(
            frame,
            conf=self.CONFIDENCE_THRESHOLD,
            iou=self.IOU_THRESHOLD,
            verbose=False,
        )[0]

        detections = []
        for box in results.boxes:
            detections.append(Detection(
                bbox=box.xyxy[0].cpu().numpy(),
                confidence=float(box.conf),
                class_id=int(box.cls),
                class_name=self.SUPPORTED_CLASSES[int(box.cls)],
            ))
        return detections
```

### FRC-Specific Considerations

- **Input resolution:** 640×640 (YOLOv8n through YOLOv8x — larger model = better accuracy, more compute)
- **Recommended model:** `YOLOv8m` — good balance of mAP and speed on T4 GPU (~25 ms/frame)
- **Classes to detect:**
  - `robot_red` — bumpers are red (alliance identification built into class)
  - `robot_blue` — bumpers are blue
  - `game_piece` — game-specific object (changes each season)
  - `field_element` — static field structures (used as perspective calibration anchors)

### Fine-Tuning Requirements

Pre-trained COCO weights are insufficient for FRC robots; fine-tuning is required:

```yaml
# training/yolov8_frc.yaml
path: datasets/frc_2024
train: images/train
val: images/val
test: images/test

nc: 4
names: ["robot_red", "robot_blue", "game_piece", "field_element"]
```

```bash
# Fine-tune YOLOv8m on FRC dataset
yolo train \
  model=yolov8m.pt \
  data=training/yolov8_frc.yaml \
  epochs=100 \
  imgsz=640 \
  batch=16 \
  device=0 \
  project=runs/train \
  name=frc_2024_v1

# Export to ONNX for production inference
yolo export model=runs/train/frc_2024_v1/weights/best.pt format=onnx
```

---

## 4. DeepSORT Multi-Object Tracking

### What DeepSORT Provides

DeepSORT extends the SORT tracker with:
1. **Appearance embeddings** — deep CNN features extracted from each detected object
2. **Mahalanobis distance** — combines appearance similarity with Kalman-predicted position
3. **Hungarian algorithm** — globally optimal assignment of detections to existing tracks
4. **Age-based pruning** — tracks without detections for `max_age` frames are removed

### Configuration

```python
# backend/app/services/cv/tracker.py
from deep_sort_realtime.deepsort_tracker import DeepSort

class RobotTracker:
    def __init__(self):
        self.tracker = DeepSort(
            max_age=30,           # Frames before track is deleted (3 sec at 10 FPS)
            n_init=3,             # Frames needed to confirm a new track
            max_cosine_distance=0.4,
            nn_budget=100,
            embedder="mobilenet", # Appearance embedding model
            half=True,            # FP16 on GPU for speed
            embedder_gpu=True,
        )
        # Maps DeepSORT internal track_id → confirmed team_id
        self.track_to_team: dict[int, int] = {}
        # Historical bounding box sizes per track_id for change detection
        self.track_bbox_history: dict[int, deque] = defaultdict(lambda: deque(maxlen=10))

    def update(
        self,
        frame: np.ndarray,
        detections: list[Detection],
        team_identifications: list[TeamIdentification],
    ) -> list[TrackedRobot]:
        # Convert to DeepSORT format: [[x1, y1, x2, y2, conf], ...]
        raw_detections = [
            [*d.bbox, d.confidence, d.class_id]
            for d in detections
        ]
        tracks = self.tracker.update_tracks(raw_detections, frame=frame)

        results = []
        for track in tracks:
            if not track.is_confirmed():
                continue

            track_id = track.track_id
            bbox = track.to_ltrb()
            self.track_bbox_history[track_id].append(bbox)

            # Update team assignment if we have a confident identification
            matched_id = self._match_detection_to_track(
                track, team_identifications
            )
            if matched_id and matched_id.confidence > 0.8:
                self.track_to_team[track_id] = matched_id.team_number

            results.append(TrackedRobot(
                track_id=track_id,
                bbox=bbox,
                team_number=self.track_to_team.get(track_id),
                identification_method=matched_id.method if matched_id else "DeepSORT",
                confidence=matched_id.confidence if matched_id else 0.85,
                bbox_size_change=self._compute_size_change(track_id),
            ))
        return results

    def _compute_size_change(self, track_id: int) -> float:
        """Returns fractional change in bounding box area vs 10-frame average."""
        history = self.track_bbox_history[track_id]
        if len(history) < 2:
            return 0.0
        areas = [(b[2]-b[0]) * (b[3]-b[1]) for b in history]
        avg_area = sum(areas[:-1]) / len(areas[:-1])
        current_area = areas[-1]
        return abs(current_area - avg_area) / max(avg_area, 1)
```

---

## 5. Team Number Identification via OCR

### Approach

FRC robots display their 4-digit team number prominently on their bumpers. When the camera angle is favorable, OCR can directly read the team number with high confidence.

```python
# backend/app/services/cv/ocr_reader.py
import easyocr
import cv2
import numpy as np
import re
from dataclasses import dataclass

@dataclass
class OCRResult:
    team_number: int | None
    confidence: float
    raw_text: str

class TeamNumberOCR:
    VALID_TEAM_RANGE = (1, 9999)
    MARGIN_RATIO = 0.25       # Expand bounding box by 25% to capture full bumper

    def __init__(self):
        # EasyOCR: faster than Tesseract; better digit recognition
        self.reader = easyocr.Reader(["en"], gpu=True, verbose=False)

    def read_team_number(
        self, frame: np.ndarray, bbox: np.ndarray
    ) -> OCRResult:
        region = self._extract_bumper_region(frame, bbox)
        preprocessed = self._preprocess_for_ocr(region)

        try:
            results = self.reader.readtext(preprocessed, allowlist="0123456789")
        except Exception:
            return OCRResult(team_number=None, confidence=0.0, raw_text="")

        # Find best digit sequence matching FRC team number format
        best = self._select_best_match(results)
        return best

    def _extract_bumper_region(
        self, frame: np.ndarray, bbox: np.ndarray
    ) -> np.ndarray:
        x1, y1, x2, y2 = bbox.astype(int)
        h, w = frame.shape[:2]
        margin_x = int((x2 - x1) * self.MARGIN_RATIO)
        margin_y = int((y2 - y1) * self.MARGIN_RATIO)
        # Expand region (clamped to frame boundaries)
        rx1 = max(0, x1 - margin_x)
        ry1 = max(0, y1 - margin_y)
        rx2 = min(w, x2 + margin_x)
        ry2 = min(h, y2 + margin_y)
        return frame[ry1:ry2, rx1:rx2]

    def _preprocess_for_ocr(self, region: np.ndarray) -> np.ndarray:
        # Upscale small regions for better OCR accuracy
        min_dim = 64
        h, w = region.shape[:2]
        if h < min_dim or w < min_dim:
            scale = min_dim / min(h, w)
            region = cv2.resize(region, None, fx=scale, fy=scale,
                                interpolation=cv2.INTER_CUBIC)
        # Convert to grayscale and enhance contrast
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        enhanced = cv2.equalizeHist(gray)
        # Adaptive thresholding for varying lighting conditions
        thresh = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )
        return thresh

    def _select_best_match(self, results: list) -> OCRResult:
        for (bbox, text, confidence) in sorted(results, key=lambda r: -r[2]):
            digits = re.sub(r"[^0-9]", "", text)
            if len(digits) >= 1:
                try:
                    team_num = int(digits)
                    if self.VALID_TEAM_RANGE[0] <= team_num <= self.VALID_TEAM_RANGE[1]:
                        return OCRResult(
                            team_number=team_num,
                            confidence=float(confidence),
                            raw_text=text,
                        )
                except ValueError:
                    continue
        return OCRResult(team_number=None, confidence=0.0, raw_text="")
```

### Known Limitations

| Limitation | Mitigation |
|------------|-----------|
| Numbers obscured by robot mechanisms | Fall back to color matching |
| Motion blur at high speed | Process at higher FPS during fast movement; OCR on sharpest frame in a 3-frame window |
| Small frame size at distance | Upscale region before OCR; limit OCR to robots within 70% of frame height |
| Similar-looking numbers under harsh lighting | Run OCR on 3 consecutive frames; take majority vote |

---

## 6. Color-Based Robot Identification

### Strategy

Each FRC team has distinct bumper colors and often distinctive body colors. A per-event calibration pass captures color profiles for each team, enabling identification when the team number is unreadable.

```python
# backend/app/services/cv/color_matcher.py
import cv2
import numpy as np
import pickle
from pathlib import Path

class TeamColorMatcher:
    HISTOGRAM_SIZE = [30, 32]   # Hue × Saturation bins
    HISTOGRAM_RANGES = [0, 180, 0, 256]
    MATCH_THRESHOLD = 0.45      # Bhattacharyya distance (lower = more similar)

    def __init__(self, profiles_path: Path):
        self.profiles: dict[int, np.ndarray] = {}  # team_number → histogram
        if profiles_path.exists():
            with open(profiles_path, "rb") as f:
                self.profiles = pickle.load(f)

    def calibrate_team(
        self, team_number: int, frame: np.ndarray, bbox: np.ndarray
    ) -> None:
        """Call once per team at match start when team number is confirmed via OCR."""
        region = self._extract_robot_region(frame, bbox)
        histogram = self._compute_histogram(region)
        self.profiles[team_number] = histogram

    def match(
        self,
        frame: np.ndarray,
        bbox: np.ndarray,
        candidate_teams: list[int],
    ) -> tuple[int | None, float]:
        """Return (team_number, confidence) for best color match among candidates."""
        region = self._extract_robot_region(frame, bbox)
        query_hist = self._compute_histogram(region)

        best_team = None
        best_score = float("inf")

        for team_num in candidate_teams:
            if team_num not in self.profiles:
                continue
            dist = cv2.compareHist(
                query_hist,
                self.profiles[team_num],
                cv2.HISTCMP_BHATTACHARYYA,
            )
            if dist < best_score:
                best_score = dist
                best_team = team_num

        if best_team is None or best_score > self.MATCH_THRESHOLD:
            return None, 0.0

        # Convert Bhattacharyya distance to confidence (0–1)
        confidence = max(0.0, 1.0 - (best_score / self.MATCH_THRESHOLD))
        return best_team, confidence

    def _extract_robot_region(
        self, frame: np.ndarray, bbox: np.ndarray
    ) -> np.ndarray:
        x1, y1, x2, y2 = bbox.astype(int)
        # Use bottom 30% of bounding box (bumper region)
        bumper_y1 = y1 + int((y2 - y1) * 0.7)
        return frame[bumper_y1:y2, x1:x2]

    def _compute_histogram(self, region: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist(
            [hsv], [0, 1], None,
            self.HISTOGRAM_SIZE,
            self.HISTOGRAM_RANGES,
        )
        cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        return hist
```

### Calibration Procedure

At the start of each match (first 30 frames), the pipeline attempts to confirm all 6 robots via OCR. When a robot is confirmed, its color profile is stored. This profile is then used for the rest of the match when the number becomes unreadable.

```python
def calibration_pass(
    self,
    frame: np.ndarray,
    tracked_robots: list[TrackedRobot],
) -> None:
    for robot in tracked_robots:
        if (
            robot.identification_method == "OCR"
            and robot.confidence > 0.85
            and robot.team_number is not None
            and robot.team_number not in self.color_matcher.profiles
        ):
            self.color_matcher.calibrate_team(
                robot.team_number, frame, robot.bbox
            )
            logger.info(
                "Calibrated color profile for team %s", robot.team_number
            )
```

---

## 7. Robot Re-Identification After Configuration Changes

### The Problem

FRC robots deploy mechanisms (arms, elevators, intakes, climbers) during a match, which can dramatically change their:
- **Bounding box size** — a robot with a deployed arm can be 3× taller
- **Appearance features** — DeepSORT's embedding changes when the robot looks different
- **Shape** — rectangular robot becomes L-shaped or T-shaped with mechanisms

If not handled, DeepSORT may:
1. Lose the existing track and create a new track (fragmented track)
2. Incorrectly merge two nearby robots into one track

### Detection Strategy

```python
# backend/app/services/cv/tracker.py

CONFIGURATION_CHANGE_THRESHOLD = 0.35  # 35% change in bounding box area

def _detect_configuration_change(
    self, track_id: int, current_bbox: np.ndarray
) -> bool:
    history = self.track_bbox_history[track_id]
    if len(history) < 5:
        return False

    # Compute rolling average area over last 5 frames
    recent_areas = [
        (b[2]-b[0]) * (b[3]-b[1]) for b in list(history)[-5:]
    ]
    avg_area = sum(recent_areas[:-1]) / len(recent_areas[:-1])
    current_area = (current_bbox[2]-current_bbox[0]) * (current_bbox[3]-current_bbox[1])

    return abs(current_area - avg_area) / max(avg_area, 1) > CONFIGURATION_CHANGE_THRESHOLD
```

### Re-Identification Protocol

When a configuration change is detected on a track:

```python
def _handle_configuration_change(
    self,
    frame: np.ndarray,
    track: Track,
    candidate_teams: list[int],
) -> TeamIdentification | None:
    """
    Multi-step re-identification when a robot changes configuration.

    Priority:
    1. OCR — try to directly read team number from the (now-visible) bumper
    2. Spatial constraint — robot should still be near its last known position
    3. Color matching — color profile should remain consistent
    4. Existing track assignment — assume same team unless contradicted
    """
    bbox = track.to_ltrb()
    last_known_team = self.track_to_team.get(track.track_id)

    # Step 1: Try OCR first (configuration changes sometimes expose bumper)
    ocr_result = self.ocr_reader.read_team_number(frame, bbox)
    if ocr_result.team_number is not None and ocr_result.confidence > 0.80:
        if (last_known_team is not None
                and ocr_result.team_number != last_known_team):
            logger.warning(
                "Track %d: OCR says team %d but previously was %d — "
                "flagging for review",
                track.track_id, ocr_result.team_number, last_known_team,
            )
            return TeamIdentification(
                team_number=ocr_result.team_number,
                method="OCR_post_config_change",
                confidence=ocr_result.confidence,
                flagged=True,
                flag_reason="team_number_conflict_after_config_change",
            )
        return TeamIdentification(
            team_number=ocr_result.team_number,
            method="OCR_post_config_change",
            confidence=ocr_result.confidence,
        )

    # Step 2: Spatial constraint — robot must be within plausible movement range
    # (max 6 ft/sec → 0.6 ft/frame at 10 FPS → ~15 pixels at field scale)
    spatially_plausible = self._filter_by_spatial_proximity(
        bbox, last_known_team, candidate_teams
    )

    # Step 3: Color matching among spatially plausible candidates
    if spatially_plausible:
        color_match_team, color_conf = self.color_matcher.match(
            frame, bbox, spatially_plausible
        )
        if color_match_team is not None and color_conf > 0.6:
            return TeamIdentification(
                team_number=color_match_team,
                method="Color_post_config_change",
                confidence=color_conf,
            )

    # Step 4: Fall back to existing track assignment (assume same team)
    if last_known_team is not None:
        return TeamIdentification(
            team_number=last_known_team,
            method="TrackContinuity_post_config_change",
            confidence=0.7,
            flagged=True,
            flag_reason="configuration_change_assumed_same_team",
        )

    return None
```

---

## 8. Team Number Recovery After Rotation / Occlusion

### Rotation Handling

When a robot rotates, its team number may be on the side facing away from the camera. The pipeline handles this via temporal consistency:

```
Frame N:   Team #254 confirmed via OCR (front-facing)     confidence = 0.95 ✓
Frame N+1: Robot rotates — number not visible             → use track_to_team[id]
Frame N+2: Robot still rotated                            → Kalman position prediction
Frame N+3: Robot faces camera again — confirm via OCR     confidence = 0.92 ✓
```

```python
def resolve_team_identity(
    self,
    frame: np.ndarray,
    track: Track,
    candidate_teams: list[int],
    frame_number: int,
) -> TeamIdentification:
    bbox = track.to_ltrb()

    # Check for configuration change first
    if self._detect_configuration_change(track.track_id, bbox):
        result = self._handle_configuration_change(frame, track, candidate_teams)
        if result:
            return result

    # Try OCR
    ocr = self.ocr_reader.read_team_number(frame, bbox)
    if ocr.team_number is not None and ocr.confidence > self.OCR_MIN_CONFIDENCE:
        # Validate against existing track assignment
        existing_team = self.track_to_team.get(track.track_id)
        if existing_team is not None and existing_team != ocr.team_number:
            # Conflict: OCR says different team than track history
            # Use multi-frame voting to resolve
            return self._resolve_identity_conflict(
                track, ocr, candidate_teams, frame_number
            )
        return TeamIdentification(
            team_number=ocr.team_number,
            method="OCR",
            confidence=ocr.confidence,
        )

    # OCR failed — use track continuity
    existing_team = self.track_to_team.get(track.track_id)
    if existing_team is not None:
        return TeamIdentification(
            team_number=existing_team,
            method="DeepSORT",
            confidence=0.85,
        )

    # No existing track assignment — try color
    color_team, color_conf = self.color_matcher.match(
        frame, bbox, candidate_teams
    )
    if color_team is not None and color_conf > 0.55:
        return TeamIdentification(
            team_number=color_team,
            method="Color",
            confidence=color_conf,
        )

    # Spatial constraint (alliance + position)
    spatial_team = self._identify_by_spatial_constraint(bbox, candidate_teams)
    if spatial_team is not None:
        return TeamIdentification(
            team_number=spatial_team,
            method="Spatial",
            confidence=0.65,
            flagged=True,
            flag_reason="low_confidence_spatial_only",
        )

    return TeamIdentification(
        team_number=None,
        method="UNKNOWN",
        confidence=0.0,
        flagged=True,
        flag_reason="all_identification_methods_failed",
    )
```

### Multi-Frame Voting for Conflict Resolution

When OCR produces a team number that conflicts with the tracked identity, a 5-frame window is used to determine the true team:

```python
def _resolve_identity_conflict(
    self,
    track: Track,
    ocr_result: OCRResult,
    candidate_teams: list[int],
    frame_number: int,
) -> TeamIdentification:
    track_id = track.track_id
    # Record this frame's OCR vote
    self.ocr_vote_history[track_id].append(
        (frame_number, ocr_result.team_number, ocr_result.confidence)
    )

    # Only resolve after 5 votes
    if len(self.ocr_vote_history[track_id]) < 5:
        # Keep existing assignment with reduced confidence
        return TeamIdentification(
            team_number=self.track_to_team.get(track_id),
            method="DeepSORT",
            confidence=0.6,
            flagged=True,
            flag_reason="identity_conflict_pending_resolution",
        )

    # Majority vote over last 5 OCR readings
    votes = [v[1] for v in self.ocr_vote_history[track_id][-5:]]
    vote_counts = Counter(votes)
    majority_team, count = vote_counts.most_common(1)[0]

    if count >= 3:  # At least 3/5 frames agree
        # Update track assignment to majority-vote winner
        self.track_to_team[track_id] = majority_team
        logger.info(
            "Track %d: identity updated to team %d via multi-frame voting (%d/5)",
            track_id, majority_team, count,
        )
        return TeamIdentification(
            team_number=majority_team,
            method="OCR_MultiFrameVote",
            confidence=count / 5.0,
        )

    # No majority — flag for manual review
    return TeamIdentification(
        team_number=self.track_to_team.get(track_id),
        method="DeepSORT",
        confidence=0.5,
        flagged=True,
        flag_reason="identity_conflict_no_majority",
    )
```

---

## 9. Kalman Filter Prediction & Track Continuity

### Purpose

The Kalman filter predicts a robot's position during frames where detection fails (occlusion, brief disappearance behind a field element). This ensures track continuity and prevents DeepSORT from creating new track IDs for the same robot.

### State Vector

DeepSORT's built-in Kalman filter tracks:

```
State: [cx, cy, a, h, vcx, vcy, va, vh]
  cx, cy — center x, y
  a      — aspect ratio (width / height)
  h      — height
  vcx, vcy, va, vh — velocities (derivatives)
```

### Gap Filling

When a track has no matching detection, DeepSORT uses the Kalman prediction and marks the track as "tentative" until a detection is matched within `max_age` frames:

```python
# Rows written for Kalman-predicted frames are flagged as interpolated
def write_movement_track_row(
    self, robot: TrackedRobot, frame_number: int, match_id: int
) -> MovementTrackCreate:
    return MovementTrackCreate(
        match_id=match_id,
        team_id=robot.team_number,
        frame_number=frame_number,
        timestamp_ms=frame_number * self.frame_interval_ms,
        pixel_x=robot.bbox_center_x,
        pixel_y=robot.bbox_center_y,
        field_x=robot.field_x,
        field_y=robot.field_y,
        track_id=robot.track_id,
        identification_method=robot.identification_method,
        confidence_score=robot.confidence,
        team_number_visible=robot.team_number_visible,
        interpolated=robot.is_predicted,      # True = Kalman prediction
        configuration_changed=robot.configuration_changed,
        bounding_box_size_change=robot.bbox_size_change,
        flagged_for_review=robot.flagged,
        review_reason=robot.flag_reason,
    )
```

---

## 10. Perspective Transform & Field Coordinate Mapping

### FRC Field Dimensions

- Full field: 54 ft × 27 ft (16.46 m × 8.23 m)
- Robot starting positions, scoring zones, and field elements are in fixed locations per season

### Calibration Procedure

```python
# backend/app/services/cv/perspective.py
import cv2
import numpy as np

class FieldPerspectiveTransform:
    """
    Calibrates the pixel-to-field transform once per camera angle per season.
    Uses fixed field elements (corner posts, alliance stations) as calibration anchors.
    """
    # FRC 2024 Crescendo field corners in real-world coordinates (ft)
    FIELD_ANCHOR_POINTS_FT = np.float32([
        [0.0,  0.0],   # Blue alliance corner, near side
        [54.0, 0.0],   # Red alliance corner, near side
        [54.0, 27.0],  # Red alliance corner, far side
        [0.0,  27.0],  # Blue alliance corner, far side
    ])

    def calibrate(self, frame: np.ndarray) -> np.ndarray:
        """
        Interactive calibration: user clicks 4 field corner points.
        Returns the perspective transformation matrix M.
        """
        print("Click the 4 field corners in order: BL, BR, TR, TL")
        pixel_points = self._get_user_clicks(frame, n=4)
        pixel_pts = np.float32(pixel_points)

        # Scale field coordinates to image-like scale for numerical stability
        SCALE = 20  # pixels per foot
        field_pts = self.FIELD_ANCHOR_POINTS_FT * SCALE

        M = cv2.getPerspectiveTransform(pixel_pts, field_pts)
        return M

    def apply(
        self, pixel_x: float, pixel_y: float, M: np.ndarray
    ) -> tuple[float, float]:
        """Transform a pixel (x, y) to field coordinates (ft)."""
        point = np.array([[[pixel_x, pixel_y]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(point, M)
        SCALE = 20
        field_x = float(transformed[0][0][0]) / SCALE
        field_y = float(transformed[0][0][1]) / SCALE
        return field_x, field_y

    def validate_field_bounds(
        self, field_x: float, field_y: float
    ) -> bool:
        """Verify transformed coordinates are within field boundaries."""
        # Add 2 ft margin for robots partially outside the field
        return -2.0 <= field_x <= 56.0 and -2.0 <= field_y <= 29.0
```

### Perspective Matrix Storage

The calibration matrix `M` is stored per event and camera angle:

```python
# Database: EventCameraCalibration model
class EventCameraCalibration(Base):
    __tablename__ = "event_camera_calibration"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("event.id"))
    camera_position: Mapped[str]      # e.g., "overhead_center", "red_alliance_wall"
    perspective_matrix: Mapped[list]  # 3×3 matrix stored as JSON
    calibrated_at: Mapped[datetime]
    calibrated_by: Mapped[str]        # Scout username
    active: Mapped[bool] = mapped_column(default=True)
```

---

## 11. MovementTrack Data Model

### Extended Schema

The `MovementTrack` model is extended beyond the basic coordinates to capture identification metadata:

```python
# backend/app/models/movement_track.py
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, String, Float, Boolean, Integer
from app.models.base import Base
import enum

class IdentificationMethod(str, enum.Enum):
    OCR = "OCR"
    OCR_POST_CONFIG_CHANGE = "OCR_post_config_change"
    OCR_MULTI_FRAME_VOTE = "OCR_MultiFrameVote"
    DEEPSORT = "DeepSORT"
    COLOR = "Color"
    COLOR_POST_CONFIG_CHANGE = "Color_post_config_change"
    SPATIAL = "Spatial"
    TRACK_CONTINUITY_POST_CONFIG = "TrackContinuity_post_config_change"
    KALMAN = "Kalman"
    UNKNOWN = "UNKNOWN"

class MovementTrack(Base):
    __tablename__ = "movement_track"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("match.id"), index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("team.id"), nullable=True)
    track_id: Mapped[int]            # DeepSORT internal track ID (per video)

    # Position data
    frame_number: Mapped[int]
    timestamp_ms: Mapped[int]        # Milliseconds from match start
    pixel_x: Mapped[float]
    pixel_y: Mapped[float]
    field_x: Mapped[float | None]    # Field coordinates in feet (post-transform)
    field_y: Mapped[float | None]

    # Identification tracking
    identification_method: Mapped[str] = mapped_column(
        String(64), default=IdentificationMethod.UNKNOWN
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    team_number_visible: Mapped[bool] = mapped_column(Boolean, default=False)

    # Configuration change tracking
    bounding_box_width: Mapped[float | None]
    bounding_box_height: Mapped[float | None]
    bounding_box_size_change: Mapped[float] = mapped_column(Float, default=0.0)
    configuration_changed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Data quality flags
    interpolated: Mapped[bool] = mapped_column(Boolean, default=False)
    flagged_for_review: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    review_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manually_corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    corrected_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("team.id"), nullable=True
    )
```

---

## 12. Video Processor Implementation

### Main Orchestrator

```python
# backend/app/services/video_processor.py
import cv2
import numpy as np
from pathlib import Path
from typing import Generator
import logging

from app.services.cv.detector import RobotDetector
from app.services.cv.tracker import RobotTracker
from app.services.cv.team_identifier import TeamIdentifier
from app.services.cv.perspective import FieldPerspectiveTransform
from app.models.movement_track import MovementTrackCreate

logger = logging.getLogger(__name__)

class VideoProcessor:
    DEFAULT_FPS = 10       # Extract 10 frames per second
    BATCH_SIZE = 100       # Write MovementTrack rows in batches

    def __init__(
        self,
        model_path: str,
        calibration_matrix: np.ndarray | None = None,
        processing_fps: int = DEFAULT_FPS,
    ):
        self.detector = RobotDetector(model_path)
        self.tracker = RobotTracker()
        self.identifier = TeamIdentifier()
        self.transform = FieldPerspectiveTransform(calibration_matrix)
        self.processing_fps = processing_fps

    def process_video(
        self,
        video_path: Path,
        match_id: int,
        alliance_teams: dict[str, list[int]],  # {"red": [254, 1678, 118], "blue": [...]}
        progress_callback=None,
    ) -> list[MovementTrackCreate]:
        cap = cv2.VideoCapture(str(video_path))
        source_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_interval = max(1, int(source_fps / self.processing_fps))

        all_tracks: list[MovementTrackCreate] = []
        frame_number = 0
        processed_count = 0

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_number += 1

                # Skip frames to achieve target FPS
                if frame_number % frame_interval != 0:
                    continue

                # Stage 1: Detect robots
                detections = self.detector.detect(frame)
                robot_detections = [
                    d for d in detections
                    if d.class_name in ("robot_red", "robot_blue")
                ]

                if not robot_detections:
                    processed_count += 1
                    continue

                # Stage 2: Identify teams
                identifications = self.identifier.identify_all(
                    frame, robot_detections, alliance_teams, frame_number
                )

                # Stage 3: Track
                tracked_robots = self.tracker.update(
                    frame, robot_detections, identifications
                )

                # Stage 4: Transform coordinates
                for robot in tracked_robots:
                    robot.field_x, robot.field_y = self.transform.apply(
                        robot.bbox_center_x, robot.bbox_center_y
                    )

                # Stage 5: Create track records
                batch = [
                    self._to_movement_track(robot, frame_number, match_id)
                    for robot in tracked_robots
                ]
                all_tracks.extend(batch)

                processed_count += 1

                # Report progress every 50 processed frames
                if progress_callback and processed_count % 50 == 0:
                    progress_callback(
                        processed=processed_count,
                        total=total_frames // frame_interval,
                        stage="tracking",
                    )

        finally:
            cap.release()

        logger.info(
            "Video processing complete: %d frames processed, "
            "%d movement track rows created",
            processed_count, len(all_tracks),
        )
        return all_tracks

    def _to_movement_track(
        self, robot, frame_number: int, match_id: int
    ) -> MovementTrackCreate:
        return MovementTrackCreate(
            match_id=match_id,
            team_id=robot.team_number,
            track_id=robot.track_id,
            frame_number=frame_number,
            timestamp_ms=int(frame_number * (1000 / self.processing_fps)),
            pixel_x=robot.bbox_center_x,
            pixel_y=robot.bbox_center_y,
            field_x=robot.field_x,
            field_y=robot.field_y,
            bounding_box_width=robot.bbox_width,
            bounding_box_height=robot.bbox_height,
            bounding_box_size_change=robot.bbox_size_change,
            identification_method=robot.identification_method,
            confidence_score=robot.confidence,
            team_number_visible=robot.team_number_visible,
            configuration_changed=robot.configuration_changed,
            interpolated=robot.is_predicted,
            flagged_for_review=robot.flagged,
            review_reason=robot.flag_reason,
        )
```

---

## 13. Celery Task Integration

```python
# backend/app/tasks/video_tasks.py
from celery import current_task
import boto3
import tempfile
from pathlib import Path

from app.celery_app import celery_app
from app.services.video_processor import VideoProcessor
from app.database import get_sync_session
from app.crud.movement_track import bulk_create_movement_tracks
from app.crud.event_calibration import get_calibration_for_event

@celery_app.task(
    bind=True,
    name="video_tasks.process_video_file",
    queue="video",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    task_acks_late=True,
)
def process_video_file(
    self,
    match_id: int,
    s3_key: str,
    alliance_teams: dict[str, list[int]],
    event_id: int,
) -> dict:
    """
    Download match video from S3, run full CV pipeline,
    and persist MovementTrack rows to the database.
    """
    def update_progress(processed: int, total: int, stage: str) -> None:
        self.update_state(
            state="PROGRESS",
            meta={
                "processed_frames": processed,
                "total_frames": total,
                "stage": stage,
                "percent": int(processed / max(total, 1) * 100),
            },
        )

    update_progress(0, 100, "downloading")

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = Path(tmpdir) / "match_video.mp4"

        # Download from S3
        s3 = boto3.client("s3")
        s3.download_file(
            Bucket=settings.S3_BUCKET_VIDEOS,
            Key=s3_key,
            Filename=str(video_path),
        )

        update_progress(0, 100, "loading_calibration")

        # Load perspective calibration for this event
        with get_sync_session() as db:
            calibration = get_calibration_for_event(db, event_id)
            matrix = np.array(calibration.perspective_matrix) if calibration else None

        update_progress(0, 100, "processing")

        # Run the CV pipeline
        processor = VideoProcessor(
            model_path=settings.YOLO_MODEL_PATH,
            calibration_matrix=matrix,
        )
        movement_tracks = processor.process_video(
            video_path=video_path,
            match_id=match_id,
            alliance_teams=alliance_teams,
            progress_callback=update_progress,
        )

        update_progress(len(movement_tracks), len(movement_tracks), "saving")

        # Persist to database in batches
        with get_sync_session() as db:
            saved_count = bulk_create_movement_tracks(db, movement_tracks)

    # Trigger analytics computation
    from app.tasks.analytics_tasks import compute_robot_performance
    compute_robot_performance.delay(match_id)

    return {
        "match_id": match_id,
        "movement_tracks_saved": saved_count,
        "flagged_tracks": sum(1 for t in movement_tracks if t.flagged_for_review),
        "status": "complete",
    }
```

---

## 14. Confidence Scoring & Flagging for Review

### Confidence Thresholds

| Method | Min. Confidence to Use | Flag if Below |
|--------|----------------------|---------------|
| OCR | 0.80 | Flag if 0.65–0.80; discard if < 0.65 |
| OCR Multi-Frame Vote | 0.60 | Flag if < 0.80 |
| DeepSORT (existing track) | 0.85 (assumed) | Never flag unless conflict |
| Color matching | 0.55 | Flag if 0.55–0.70 |
| Spatial constraint | 0.65 | Always flag |
| Kalman prediction | 0.70 | Flag if gap > 3 frames |
| UNKNOWN | N/A | Always flag |

### Flag Reasons Reference

| Flag Reason | Description |
|------------|-------------|
| `low_confidence_ocr` | OCR read team number but confidence < 0.80 |
| `team_number_unreadable` | All identification methods except color/spatial failed |
| `identity_conflict_after_config_change` | OCR team number ≠ track history after mechanism deployment |
| `identity_conflict_no_majority` | Multi-frame voting failed to reach 3/5 majority |
| `configuration_change_assumed_same_team` | No OCR confirmation after configuration change |
| `low_confidence_spatial_only` | Only spatial constraint available; no color profile |
| `all_identification_methods_failed` | No method produced a match above thresholds |
| `track_gap_exceeded` | Robot not detected for > 3 frames (> 0.3 sec) |

---

## 15. Manual Review Dashboard

### Review Interface Specification

The review dashboard allows coaches and scouts to correct uncertain tracking data post-match:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Match #42 — Flagged Tracks Review                     [5 flagged]  │
├──────────────────────────────────────────────────────────────────────┤
│  Filters: [Team ▼] [Method ▼] [Confidence < 0.7 ▼] [Unreviewed ▼] │
├──────────────────────────────────────────────────────────────────────┤
│  Frame 312–325  │  Track #3  │  Team: 254? (conf: 0.62)             │
│  ─────────────────────────────────────────────────────────────────  │
│  [◀ Prev] [▶ Play] [▶ Next]    Reason: identity_conflict_no_majority│
│                                                                      │
│  ┌──────────────────────────────┐  Correct to:                      │
│  │  [Video Frame Preview]       │  ⊙ Team 254   ○ Team 1678        │
│  │  [Bounding box highlighted]  │  ○ Team 118   ○ Unknown           │
│  │  [Alliance colors shown]     │                                   │
│  └──────────────────────────────┘  [Apply Correction] [Skip]        │
├──────────────────────────────────────────────────────────────────────┤
│  Frame 445–448  │  Track #5  │  Team: Unknown (conf: 0.0)           │
│  Reason: all_identification_methods_failed                           │
│  [◀ Prev] [▶ Play] [▶ Next]                                         │
└──────────────────────────────────────────────────────────────────────┘
```

### API Endpoints for Review

```python
# GET /api/v1/matches/{match_id}/flagged-tracks
# Returns all MovementTrack rows with flagged_for_review=True for a match

# PATCH /api/v1/movement-tracks/{track_id}/correct
# Body: {"correct_team_id": 254}
# Sets manually_corrected=True, corrected_team_id=254 on the row
```

---

## 16. Accuracy Metrics & Validation

### Metrics Collected Per Processed Video

```python
# backend/app/services/cv/metrics.py
@dataclass
class PipelineMetrics:
    # Detection
    total_frames_processed: int
    total_detections: int
    avg_detections_per_frame: float

    # Identification
    identified_by_ocr: int
    identified_by_deepsort: int
    identified_by_color: int
    identified_by_spatial: int
    identified_by_kalman: int
    identified_unknown: int

    # Confidence
    avg_confidence_score: float
    low_confidence_rate: float    # % of rows with confidence < 0.7

    # Issues
    config_changes_detected: int
    interpolated_frames: int
    flagged_for_review: int
    flagged_rate: float           # flagged_for_review / total rows

    # Track quality
    track_fragmentation: int      # Unique track IDs per team (should be 1)
    coverage_rate: float          # % of match duration with all 6 robots tracked
```

### Ground-Truth Validation (Offline)

For model evaluation, a hand-annotated validation set is used:

```bash
# Annotate validation videos with known team assignments
python scripts/annotate_ground_truth.py \
  --video validation_data/2024necmp_qm12.mp4 \
  --output validation_data/2024necmp_qm12_gt.json

# Run pipeline and compare to ground truth
python scripts/evaluate_pipeline.py \
  --video validation_data/2024necmp_qm12.mp4 \
  --ground_truth validation_data/2024necmp_qm12_gt.json \
  --model runs/train/frc_2024_v1/weights/best.pt

# Output:
# Team ID accuracy:          94.2%
# Track fragmentation rate:   2.1%  (should be < 5%)
# Coverage rate:             97.8%  (should be > 95%)
# Flagged rate:               8.3%  (acceptable: < 15%)
```

---

## 17. Model Training & Fine-Tuning

### Dataset Requirements

| Dataset | Size | Source |
|---------|------|--------|
| FRC robot images (2024) | 5,000+ images | TBA video frames, manually annotated |
| Robot configuration variety | 1,000+ images | Various mechanism states per top-25 teams |
| Poor lighting conditions | 500+ images | Arena-specific lighting compensation |
| Occlusion scenarios | 500+ images | Robots overlapping, partial views |

### Annotation Guidelines

```yaml
# Label format: YOLO format (class_id cx cy w h normalized)
# Classes:
#   0: robot_red   — Red alliance bumpers visible
#   1: robot_blue  — Blue alliance bumpers visible
#   2: game_piece  — Current season game piece (changes annually)
#   3: field_element — Permanent field structure

# Important annotation rules:
# - Annotate FULL robot extent including deployed mechanisms
# - Label class based on bumper color, not robot position
# - For partially occluded robots: annotate the visible portion + estimated full bbox
# - Minimum bounding box: 20×20 pixels
```

### Training Pipeline

```bash
# 1. Prepare dataset splits (80/10/10)
python scripts/split_dataset.py \
  --source datasets/frc_raw \
  --output datasets/frc_2024 \
  --split 0.8 0.1 0.1

# 2. Fine-tune from COCO pre-trained weights
yolo train \
  model=yolov8m.pt \
  data=datasets/frc_2024/dataset.yaml \
  epochs=100 \
  imgsz=640 \
  batch=16 \
  device=0 \
  patience=20 \
  save_period=10 \
  project=runs/train \
  name=frc_2024_v1

# 3. Validate on held-out test set
yolo val \
  model=runs/train/frc_2024_v1/weights/best.pt \
  data=datasets/frc_2024/dataset.yaml \
  split=test

# 4. Export to ONNX for production (faster CPU inference)
yolo export \
  model=runs/train/frc_2024_v1/weights/best.pt \
  format=onnx \
  opset=12
```

### Annual Retraining Schedule

FRC changes its game (and field elements, game pieces) every year. Model updates are required:

| Trigger | Action |
|---------|--------|
| New FRC season announced (January) | Collect annotation data from reveal video and CAD models |
| Kickoff + first events (January–February) | Fine-tune existing model on new season images |
| First regional events (February–March) | Validate on live event footage; retrain if mAP drops > 5% |
| Championship (April–May) | Final validation; freeze model for the season |

---

## 18. GPU Infrastructure

### Instance Selection

| Use Case | Instance Type | GPU | vRAM | Cost |
|----------|-------------|-----|------|------|
| Production CV processing | `g4dn.xlarge` (AWS) | NVIDIA T4 | 16 GB | ~$0.53/hr on-demand; ~$0.16/hr Spot |
| Development / testing | `g4dn.xlarge` Spot | NVIDIA T4 | 16 GB | ~$0.16/hr |
| High-volume (finals) | `g5.xlarge` | NVIDIA A10G | 24 GB | ~$1.01/hr Spot |

### Docker GPU Setup

```dockerfile
# Dockerfile.cv-worker
FROM nvidia/cuda:12.1-cudnn8-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y \
    python3.11 python3-pip ffmpeg libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["celery", "-A", "app.celery_app", "worker", \
     "-Q", "video", \
     "-c", "1", \
     "--loglevel=info"]
```

```yaml
# docker-compose.yml — GPU worker service
celery-gpu-worker:
  build:
    context: ./backend
    dockerfile: Dockerfile.cv-worker
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
  environment:
    - CUDA_VISIBLE_DEVICES=0
```

### CPU Fallback

```python
# Automatically detected in detector.py
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"

# If running on CPU: use YOLOv8n (nano) for speed; GPU: use YOLOv8m (medium)
model_variant = "yolov8m" if device == "cuda" else "yolov8n"
```

---

## 19. Performance Benchmarks

### Target Processing Times

| Configuration | Frames/sec | Time for 150s match (10 FPS = 1500 frames) |
|--------------|-----------|----------------------------------------------|
| NVIDIA T4 (g4dn.xlarge) | ~60 FPS | ~25 seconds |
| NVIDIA A10G (g5.xlarge) | ~120 FPS | ~12 seconds |
| CPU only (t3.medium) | ~5 FPS | ~5 minutes |

### Optimization Techniques

```python
# 1. FP16 inference (half precision — 2× speedup on modern GPUs)
model = YOLO("yolov8m.pt")
model.half()  # Convert to FP16

# 2. Batch inference (process multiple frames simultaneously)
results = model(frames_batch, batch=8)  # Process 8 frames in one pass

# 3. ONNX Runtime for CPU inference (3× faster than PyTorch CPU)
from ultralytics import YOLO
model = YOLO("best.onnx")  # ONNX model for CPU workers

# 4. Frame skip optimization — only run full detection every N frames
# Run tracking (DeepSORT only) on intermediate frames
```

---

## 20. Testing Strategy

### Unit Tests

```python
# backend/tests/cv/test_ocr_reader.py
import pytest
from app.services.cv.ocr_reader import TeamNumberOCR

class TestTeamNumberOCR:
    def test_reads_valid_team_number(self, sample_bumper_frame):
        ocr = TeamNumberOCR()
        result = ocr.read_team_number(sample_bumper_frame["frame"], sample_bumper_frame["bbox"])
        assert result.team_number == sample_bumper_frame["expected_team"]
        assert result.confidence > 0.8

    def test_returns_none_for_rotated_robot(self, rotated_robot_frame):
        ocr = TeamNumberOCR()
        result = ocr.read_team_number(rotated_robot_frame["frame"], rotated_robot_frame["bbox"])
        # Should fail gracefully, not raise
        assert result.team_number is None or result.confidence < 0.5

    def test_rejects_out_of_range_numbers(self, frame_with_text_10000):
        ocr = TeamNumberOCR()
        result = ocr.read_team_number(frame_with_text_10000["frame"], frame_with_text_10000["bbox"])
        assert result.team_number is None

# backend/tests/cv/test_color_matcher.py
class TestColorMatcher:
    def test_matches_calibrated_team(self, calibrated_matcher, sample_frame):
        team, conf = calibrated_matcher.match(
            sample_frame["frame"],
            sample_frame["bbox_team_254"],
            candidate_teams=[254, 1678, 118],
        )
        assert team == 254
        assert conf > 0.55

    def test_returns_none_when_uncalibrated(self, uncalibrated_matcher, sample_frame):
        team, conf = uncalibrated_matcher.match(
            sample_frame["frame"],
            sample_frame["bbox_team_254"],
            candidate_teams=[254],
        )
        assert team is None
```

### Integration Tests

```python
# backend/tests/test_video_pipeline.py
class TestVideoPipeline:
    def test_process_synthetic_video(self, synthetic_match_video, db_session):
        """
        Synthetic video: 30-second clip with 6 colored rectangles
        representing robots with known team number labels.
        """
        processor = VideoProcessor(model_path="tests/fixtures/test_model.pt")
        tracks = processor.process_video(
            video_path=synthetic_match_video,
            match_id=1,
            alliance_teams={"red": [254, 1678, 118], "blue": [148, 1114, 33]},
        )

        # Verify all 6 robots tracked
        unique_teams = {t.team_id for t in tracks if t.team_id is not None}
        assert len(unique_teams) == 6

        # Verify field coordinates within bounds
        for track in tracks:
            if track.field_x is not None:
                assert -2.0 <= track.field_x <= 56.0
                assert -2.0 <= track.field_y <= 29.0

        # Verify flagged rate is acceptable
        flagged_rate = sum(1 for t in tracks if t.flagged_for_review) / len(tracks)
        assert flagged_rate < 0.15  # Less than 15% of rows flagged

    def test_handles_corrupt_video_gracefully(self, corrupt_video_path):
        processor = VideoProcessor(model_path="tests/fixtures/test_model.pt")
        with pytest.raises(VideoProcessingError, match="corrupt"):
            processor.process_video(corrupt_video_path, match_id=1, alliance_teams={})
```

### Acceptance Criteria Summary

| Criterion | Target |
|-----------|--------|
| Team ID accuracy (confirmed via OCR) | ≥ 92% on validation set |
| Team ID accuracy (full pipeline) | ≥ 85% on validation set |
| Track fragmentation rate | < 5% (< 0.05 extra tracks per team per match) |
| Coverage rate (all 6 robots tracked) | > 95% of match frames |
| Flagged-for-review rate | < 15% of total MovementTrack rows |
| Processing speed (GPU) | 150-second match in < 60 seconds |
| Processing speed (CPU fallback) | 150-second match in < 10 minutes |
| Corrupt video handling | No worker crash; descriptive error returned |
