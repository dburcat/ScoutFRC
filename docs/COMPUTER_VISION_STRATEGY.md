# Computer Vision Strategy

## ScouterFRC — Phase 2 Computer Vision Implementation Guide

---

## 1. Overview & Goals

### Purpose

The ScouterFRC computer vision system automatically analyzes FRC match videos to detect, track, and identify all six robots on the field. Raw pixel coordinates are converted to field-space coordinates and stored as `MovementTrack` records, enabling downstream analytics (heatmaps, phase statistics, performance metrics) without manual data entry.

### Key Challenges in FRC Tracking

| Challenge | Description |
|-----------|-------------|
| Visual similarity | Robots may look alike across different teams |
| Occlusions | Robots frequently block each other, especially near scoring zones |
| Configuration changes | Mechanisms deploy mid-match, changing a robot's silhouette |
| Team number visibility | Numbers may be small, angled, or obstructed |
| Camera angle | Single fixed overhead or side-angle camera limits 3-D information |
| Lighting variability | Field lighting differs between venues and changes during matches |

### Design Philosophy

- **Robust multi-method identification** — no single method is relied upon exclusively; four complementary techniques are fused
- **Graceful degradation** — if the best method fails, the system falls back rather than producing wrong data
- **Explainability** — every identification decision is logged with method and confidence score
- **Human-in-the-loop** — uncertain detections are flagged for manual review rather than silently producing bad data

### Performance Targets

| Metric | Target |
|--------|--------|
| Robot detection accuracy | > 95 % (mAP@0.5) |
| Tracking ID consistency | > 90 % over a full match |
| Team identification accuracy | > 95 % across all methods |
| Frame processing speed | ≥ 15 FPS (real-time capable) |
| Per-frame latency | < 100 ms |
| Memory per worker process | < 2 GB |

---

## 2. System Architecture

### High-Level Pipeline Diagram

```
┌──────────────────────────────────────────────────────┐
│                    Input Video                       │
└───────────────────────┬──────────────────────────────┘
                        ▼
┌──────────────────────────────────────────────────────┐
│              Frame Extraction (OpenCV)               │
│  Configurable sample rate (e.g., every frame or      │
│  every Nth frame for faster offline processing)      │
└───────────────────────┬──────────────────────────────┘
                        ▼
┌──────────────────────────────────────────────────────┐
│            Frame Preprocessing                       │
│  Resize → normalize → color-space conversion         │
└───────────────────────┬──────────────────────────────┘
                        ▼
┌──────────────────────────────────────────────────────┐
│           YOLOv8 Detection                           │
│  Output: robot bounding boxes + confidence scores    │
└───────────────────────┬──────────────────────────────┘
                        ▼
┌──────────────────────────────────────────────────────┐
│           DeepSORT Tracker Update                    │
│  Output: track IDs assigned to each bounding box     │
└───────────────────────┬──────────────────────────────┘
                        ▼
┌──────────────────────────────────────────────────────┐
│           Parallel Identification Layer              │
├─────────────────┬────────────────┬───────────────────┤
│   OCR           │  Color Match   │  Kalman Update    │
│  (team number)  │  (team color)  │  (pos/velocity)   │
└────────┬────────┴───────┬────────┴─────────┬─────────┘
         └────────────────┼──────────────────┘
                          ▼
┌──────────────────────────────────────────────────────┐
│           Multi-Method Fusion                        │
│  Select best identification; compute confidence      │
└───────────────────────┬──────────────────────────────┘
                        ▼
┌──────────────────────────────────────────────────────┐
│           Perspective Transform                      │
│  Pixel coordinates → field coordinates (ft/m)        │
└───────────────────────┬──────────────────────────────┘
                        ▼
┌──────────────────────────────────────────────────────┐
│           MOVEMENT_TRACK Storage (DB)                │
└──────────────────────────────────────────────────────┘
```

### Component Interactions

- **Celery task** (`process_video_file`) orchestrates the pipeline end-to-end
- **VideoProcessor service** encapsulates frame extraction, detection, and tracking
- **IdentificationService** runs OCR, color matching, and Kalman fusion in parallel
- **PerspectiveTransformer** applies a per-event calibration matrix
- **MovementTrackRepository** batches database inserts for efficiency

### Error Handling Flow

```
Exception in any stage
        │
        ▼
  Log full traceback with frame number and task ID
        │
        ├─ Recoverable (e.g., single corrupted frame)
        │         → skip frame, continue processing, increment error counter
        │
        └─ Fatal (e.g., unreadable video, DB connection lost)
                  → mark task FAILED, store error in Celery result backend
                  → send alert if configured
```

---

## 3. Robot Detection (YOLOv8)

### Model Selection Rationale

YOLOv8 (Ultralytics) is chosen over alternatives because:

| Criterion | YOLOv8 | Faster R-CNN | SSD | RT-DETR |
|-----------|--------|--------------|-----|---------|
| Real-time capable on CPU | ✅ | ❌ | ✅ | ⚠️ |
| Accuracy (mAP@0.5) | High | Higher | Medium | High |
| Transfer learning ease | ✅ | ✅ | ⚠️ | ✅ |
| Community / tooling | Excellent | Good | Good | Growing |
| Python API quality | Excellent | Fair | Fair | Good |

YOLOv8-nano or YOLOv8-small are sufficient for a 6-robot scene; larger variants are reserved for GPU environments.

### Training Data Requirements

- Minimum 2 000 annotated frames from FRC match footage
- At least 10 different FRC events represented
- Multiple camera angles (overhead, side, corner)
- Variety of lighting conditions and game years

### Model Variants

| Variant | Parameters | CPU FPS (1080p) | GPU FPS | Recommended Use |
|---------|-----------|-----------------|---------|-----------------|
| YOLOv8n (nano) | 3.2 M | 8–12 | 60+ | Raspberry Pi / edge |
| YOLOv8s (small) | 11.2 M | 12–20 | 100+ | Server CPU |
| YOLOv8m (medium) | 25.9 M | 6–10 | 60+ | GPU server |
| YOLOv8l (large) | 43.7 M | 2–5 | 40+ | High-accuracy offline |

**Default:** `YOLOv8s` balances accuracy and CPU-only performance.

### Performance Characteristics

- **mAP@0.5:** target ≥ 0.95 after fine-tuning on FRC data
- **False positive rate:** < 5 % (non-robot objects detected as robots)
- **False negative rate:** < 5 % (robots missed entirely)

### Confidence & NMS Thresholds

```python
YOLO_CONFIDENCE_THRESHOLD = 0.45   # reject low-confidence detections
YOLO_NMS_IOU_THRESHOLD    = 0.40   # non-maximum suppression overlap limit
```

Tune these per event if the field background produces many false positives.

### Hardware Requirements

| Environment | Requirement |
|-------------|-------------|
| CPU only | 4+ cores, 8 GB RAM |
| GPU accelerated | NVIDIA GPU with CUDA 11.8+, ≥ 4 GB VRAM |
| Minimum (testing) | 2 cores, 4 GB RAM (reduced FPS expected) |

---

### Training Strategy

#### Data Collection

1. Download match videos from The Blue Alliance or team uploads
   - **Usage rights:** Verify licensing and attribution requirements before using videos for training. The Blue Alliance streams are generally intended for team/scouting use; confirm terms of service before large-scale automated collection.
2. Sample one frame per second to build a diverse dataset
3. Cover at least 5 different FRC game years to maximize generalization

#### Annotation Guidelines

- Draw bounding boxes tightly around the robot chassis
- Include partially visible robots (near field boundaries)
- Label occluded robots only if ≥ 50 % of the robot is visible
- Use a single class: `robot`

#### Augmentation Strategy

```
Original frame
  ├─ Horizontal flip
  ├─ Random brightness ±20 %
  ├─ Random contrast ±20 %
  ├─ Gaussian blur (sigma 0–1)
  ├─ Random crop (±10 %)
  └─ Mosaic (combine 4 images)
```

#### Cross-Validation

- 5-fold cross-validation across events (not frames) to prevent data leakage
- Hold out one full event as final test set

#### Performance Metrics

- **mAP@0.5** — primary detection quality metric
- **mAP@0.5:0.95** — stricter overlap metric for localization quality
- **Precision / Recall** — balance false positives vs false negatives
- **Inference time (ms)** — measure on target hardware

---

### Inference

#### Real-Time Requirements

- Target: ≥ 15 FPS on a 4-core server CPU with `YOLOv8s`
- GPU acceleration optional; system must work on CPU only

#### Batch Processing

- For offline videos: process every frame or every Nth frame (configurable)
- Default: every frame for ≤ 30 FPS source; every other frame for > 30 FPS source

#### Frame Sampling

```python
FRAME_SAMPLE_RATE = 1   # process 1 out of every N frames
                         # 1 = every frame, 2 = every other, etc.
```

#### Variable Resolution Handling

- Resize all frames to 640 × 640 before inference (YOLOv8 default)
- Scale bounding box coordinates back to original resolution before downstream use

#### GPU Acceleration

```python
device = "cuda" if torch.cuda.is_available() else "cpu"
model = YOLO("yolov8s.pt")
model.to(device)
```

---

## 4. Robot Tracking (DeepSORT)

### Why DeepSORT

| Tracker | Re-ID Model Required | CPU Performance | Occlusion Handling | FRC Fit |
|---------|---------------------|-----------------|-------------------|---------|
| DeepSORT | Optional | Good | Good | ✅ |
| ByteTrack | No | Excellent | Moderate | ✅ |
| SORT (simple) | No | Excellent | Poor | ⚠️ |
| YOLO built-in | No | Good | Moderate | ✅ |
| StrongSORT | Yes | Moderate | Excellent | ⚠️ (complexity) |

**Decision:** DeepSORT without a custom re-ID model provides a good occlusion handling/complexity trade-off for the ≤ 6-robot FRC scenario.

### Feature Extraction

- Use the default DeepSORT appearance model (cosine distance on CNN features)
- Features extracted from each bounding box crop at each frame
- Appearance feature vectors stored per track for re-identification

### Track Lifecycle

```
NEW DETECTION
    │
    ▼
Track initialized (tentative)
    │
    ▼  (min_hits confirmations)
Track confirmed (assigned stable ID)
    │
    ├─ Detection matched   → update track
    ├─ Detection missing   → increment age (Kalman predict only)
    │
    └─ Age > max_age       → track deleted
```

### Track ID Assignment

- IDs are monotonically increasing integers per video session
- IDs are **not** reused after deletion within a single video
- Mapping from DeepSORT track ID → team ID maintained separately

### Tunable Parameters

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `max_age` | 15 | 5–30 | Frames to keep a track alive without a detection |
| `min_hits` | 2 | 1–3 | Detections needed before track is confirmed |
| `iou_threshold` | 0.30 | 0.1–0.5 | Minimum IoU to associate detection with track |
| `max_cosine_distance` | 0.4 | 0.2–0.6 | Appearance similarity threshold |

---

### Multi-Robot Constraints

- Maximum 3 robots per alliance, 6 total on field
- Red alliance robots expected on the red half of the field during autonomous
- Track count sanity check: alert if > 6 confirmed tracks exist simultaneously
- Alliance-based spatial priors can resolve ambiguous re-identification

### Robustness

#### Track Fragmentation

When a robot loses its track and re-enters, DeepSORT creates a new track. The system handles this by:

1. Checking alliance spatial constraints — was a robot at this position before?
2. Checking color profile similarity
3. Running OCR if team number is visible
4. Merging the new track ID with the historical team ID if confirmed

#### Re-Identification Logic

```
New track appears at position P
    ↓
Query recently deleted tracks whose last position ≤ D meters from P
    ↓
For each candidate track:
    - Color similarity check (Bhattacharyya distance)
    - OCR check (if team number visible)
    - Kalman-predicted position proximity
    ↓
If best candidate score > threshold → merge tracks
Else → treat as new robot appearance
```

#### Track Merging Detection

If two confirmed tracks overlap (IoU > 0.6) for > 5 frames, they likely represent the same robot. Merge the lower-confidence track into the higher-confidence one.

---

## 5. Team Number Identification (OCR)

### OCR Engine Selection

| Engine | Speed | Accuracy | Language Support | CPU Friendly |
|--------|-------|----------|-----------------|-------------|
| Tesseract | Medium | Good | 100+ | ✅ |
| EasyOCR | Slow | Very Good | 80+ | ✅ |
| PaddleOCR | Fast | Excellent | 80+ | ✅ |
| TrOCR (transformer) | Slow | Excellent | Limited | ❌ GPU needed |

**Default:** EasyOCR for accuracy; Tesseract as a lightweight fallback.

### Region Extraction

1. Take the bounding box from YOLOv8
2. Expand symmetrically by 20 % on each side: subtract 20 % of width from x1/add to x2, subtract 20 % of height from y1/add to y2 (team number often extends slightly outside the robot bbox)
3. Crop frame to this expanded region

### Preprocessing Pipeline

```
Raw crop
    ↓
Resize to 128 × 128 (or larger if source resolution allows)
    ↓
Convert to grayscale
    ↓
Histogram equalization (CLAHE, clip=2.0, tileGridSize=8×8)
    ↓
Gaussian blur (3×3, sigma=1) for noise reduction
    ↓
Adaptive threshold (blockSize=11, C=2)
    ↓
Morphological dilation (3×3 kernel, 1 iteration)
    ↓
Feed to OCR engine
```

### Confidence Scoring

- EasyOCR returns a confidence value per detected string; require ≥ 0.80
- Tesseract confidence mapped linearly from its internal integer score

### Character Set Optimization

- Restrict OCR character set to digits `[0-9]`
- Team numbers are 1–4 digits (valid range: 1–9999)

### Performance Benchmarking

Run on a held-out set of 500 robot crops with known team numbers:

- True positive rate (correct number read): target ≥ 90 %
- False positive rate (wrong number): target < 5 %
- No-detection rate (number not found): acceptable; handled by fallback

---

### Preprocessing Pipeline (Detail)

#### Bounding Box Expansion

```python
expansion = 0.20
x1 = max(0, x1 - w * expansion)
y1 = max(0, y1 - h * expansion)
x2 = min(frame_width,  x2 + w * expansion)
y2 = min(frame_height, y2 + h * expansion)
```

#### Perspective Correction

If the robot is viewed at an angle, use an affine/perspective warp to straighten the number panel before OCR. Estimate homography from the four corners of the number panel when visible.

---

### Validation

- **OCR confidence threshold:** ≥ 0.80 to accept result
- **Valid team list check:** cross-reference against event roster (from TBA sync)
- **Cross-frame validation:** require the same team number read in ≥ 3 of the last 10 frames before committing
- **Fallback:** if OCR fails or confidence < threshold, defer to color matching or DeepSORT

---

## 6. Color-Based Team Identification

### Color Space

HSV (Hue, Saturation, Value) is preferred over RGB or LAB because:
- Hue is rotation-invariant to lighting changes
- Saturation discriminates colorful robots from grey/silver ones
- Easy to define color ranges for common FRC team colors

### Dominant Color Extraction

1. Convert robot crop to HSV
2. Compute a 3D histogram (H: 36 bins, S: 8 bins, V: 8 bins)
3. Find the top-3 dominant hue clusters (excluding near-black and near-white)
4. Store the weighted average hue + saturation as the color signature

### Color Histogram Computation

```python
hist = cv2.calcHist(
    [hsv_crop],
    channels=[0, 1, 2],
    mask=None,
    histSize=[36, 8, 8],
    ranges=[0, 180, 0, 256, 0, 256]
)
cv2.normalize(hist, hist)
```

### Per-Event Team Color Registration

Each team's color profile is calibrated at the start of an event:

1. Identify a frame where the robot is clearly visible and unoccluded
2. Manually confirm team number ↔ color profile mapping
3. Store in `ROBOT_COLOR_PROFILE` table

### Alliance Color Constraints

- Red alliance robots should have red-dominant team colors (or neutral)
- Blue alliance robots should have blue-dominant team colors (or neutral)
- Use alliance assignment from TBA data to narrow candidate pool

---

### Calibration Procedure

1. **Initial capture:** from the first 10 seconds of the match, extract all confirmed robot tracks
2. **Manual confirmation:** display each robot crop and ask the operator to assign team numbers
3. **Profile storage:** persist the HSV histogram as a binary blob in `ROBOT_COLOR_PROFILE`
4. **Re-use:** profiles are reused across matches in the same event; updated if confidence drops
5. **Seasonal updates:** profiles may change between events (robot repaints); recalibrate at each event

---

### Matching Algorithm

#### Bhattacharyya Distance

```python
distance = cv2.compareHist(profile_hist, candidate_hist, cv2.HISTCMP_BHATTACHARYYA)
# distance: 0 = identical, 1 = completely different
similarity = 1.0 - distance
```

#### Confidence Thresholding

| Similarity | Confidence | Action |
|------------|-----------|--------|
| ≥ 0.75 | High | Accept match |
| 0.55–0.74 | Medium | Use as supporting evidence |
| < 0.55 | Low | Discard; use other methods |

#### Multi-Frame Confirmation

Require similarity ≥ 0.65 in ≥ 5 of the last 10 frames before committing a color-based identification.

#### Handling Similar Colors

If two teams have similar color profiles (Bhattacharyya distance < 0.15 between their profiles), flag both as "ambiguous color pair" and rely on OCR or DeepSORT tracking instead.

---

## 7. Kalman Filtering & Motion Prediction

### Kalman Filter Implementation

Standard linear Kalman filter tracking a 4-dimensional state vector:

```
State:       [x, y, vx, vy]
Measurement: [x, y]          (bounding box center)
```

Transition matrix (constant-velocity model, dt = frame period):

```
F = [[1, 0, dt,  0],
     [0, 1,  0, dt],
     [0, 0,  1,  0],
     [0, 0,  0,  1]]
```

### Process & Measurement Noise

| Parameter | Value | Notes |
|-----------|-------|-------|
| Process noise Q | diag([1, 1, 2, 2]) | Higher noise on velocity (robots accelerate rapidly) |
| Measurement noise R | diag([5, 5]) | Pixel-level detection jitter |

These defaults should be tuned against real FRC footage; values in pixels² at 1280×720.

### Prediction During Detection Gaps

When no detection is associated with a track:

1. Run Kalman predict step (advance state estimate)
2. Record position as `interpolated = True`
3. Inflate uncertainty covariance by 10 % per gap frame
4. If gap exceeds `max_gap_frames` (default: 15), terminate track

### Velocity Smoothing

Apply exponential moving average to velocity estimates:

```python
alpha = 0.3   # smoothing factor
velocity_smooth = alpha * velocity_raw + (1 - alpha) * velocity_smooth_prev
```

---

### Motion Constraints

| Constraint | Value | Rationale |
|-----------|-------|-----------|
| Max velocity | 5 m/s (≈ 16.4 ft/s) | FRC robot speed limit |
| Max acceleration | 10 m/s² | Typical drivetrain limit |
| Field boundary | [0,0] – [16.46 m, 8.23 m] (54 × 27 ft) | 2025 season field |

If a predicted position violates a boundary, clamp to the nearest valid coordinate.

---

### Gap Handling

| Gap Duration | Action |
|-------------|--------|
| 1–5 frames | Kalman prediction; mark `interpolated = True` |
| 6–15 frames | Kalman prediction; reduce confidence score by 0.05 per frame |
| > 15 frames | Terminate track; create new track when robot reappears |

---

## 8. Configuration Change Detection

### Overview

FRC robots deploy mechanisms mid-match (arms, elevators, intake rollers) that significantly change their visual silhouette. These changes can confuse the tracker or invalidate color profiles.

### Detection Method

Track the bounding box area over a rolling 10-frame window. Compute the percentage change in area:

```python
area_now  = (x2 - x1) * (y2 - y1)
area_prev = rolling_avg_area[-10:]
pct_change = abs(area_now - area_prev) / area_prev * 100
```

Flag the track if `pct_change ≥ 30 %`.

### Handling

1. **Re-identification check:** when a configuration change is detected, re-run OCR and color matching on the new silhouette
2. **Tracking uncertainty window:** for the next 5 frames after detection, reduce identification confidence by 0.1
3. **Manual review flagging:** if re-identification fails, set `flagged_for_review = True` and `review_reason = "configuration_change"`
4. **Recovery:** after 10 stable frames (< 5 % area variation), confidence returns to normal

---

## 9. Handling Occlusions & Loss

### Robot-to-Robot Occlusion

When two robots overlap on the field, one or both bounding boxes may merge or disappear.

**Handling:**

- DeepSORT continues predicting both tracks via Kalman for up to `max_age` frames
- Alliance-based spatial constraints prevent assigning both tracks to the same alliance position
- When occlusion ends, the first detection within `iou_threshold` of each predicted position is re-associated

### Off-Field Robot

A robot that leaves the playing field (e.g., tips over, hangs) may exit the camera frame.

**Handling:**

- If predicted coordinates move outside the field boundary, mark track as `off_field = True`
- Suspend the track (stop Kalman prediction) after 5 consecutive off-field frames
- Resume when a detection appears near the last known in-bounds position

### Alliance-Based Spatial Constraints

During autonomous, alliance robots are expected to start in their alliance-colored starting tiles. Use this as a strong prior for initial identification assignment.

---

### Occlusion Strategies

1. **DeepSORT age management:** `max_age` controls how long an occluded track is kept alive
2. **Kalman prediction:** provides an estimated position even during occlusion
3. **Alliance zone check:** verifies that a re-associated detection is consistent with the team's expected zone
4. **Multi-frame confirmation:** require ≥ 3 consecutive frames of consistent re-association before finalizing

---

## 10. Multi-Method Identification Strategy

### Hierarchical Approach (Priority Order)

The system attempts identification methods in priority order, stopping as soon as sufficient confidence is achieved.

#### Priority 1 — OCR (Highest Priority)

- **Conditions:** team number visible and readable in the crop
- **Confidence range:** 0.85–1.0
- **Cross-frame requirement:** same number seen in ≥ 3 of last 10 frames
- **Fallback:** if OCR confidence < 0.80 or no number found, proceed to Priority 2

#### Priority 2 — DeepSORT Continuous Tracking

- **Conditions:** unbroken track from a previously identified robot
- **Confidence range:** 0.80–0.95
- **Confidence decay:** 0.02 per frame without a fresh OCR or color confirmation
- **Fallback:** if track was recently fragmented (gap > 15 frames), proceed to Priority 3

#### Priority 3 — Color Matching

- **Conditions:** team has a registered color profile; profile is distinctive (not ambiguous)
- **Confidence range:** 0.70–0.90
- **Fallback:** if color similarity < 0.55 or profile is ambiguous, proceed to Priority 4

#### Priority 4 — Kalman Prediction + Alliance Constraints

- **Conditions:** robot position is predictable; only one team is expected at that location
- **Confidence range:** 0.60–0.80
- **Fallback:** if multiple robots could be at the predicted position, flag for manual review

#### Priority 5 — Manual Review Required

- **Conditions:** all methods uncertain (confidence < 0.60)
- **Action:** set `flagged_for_review = True`; store best guess with its confidence score
- **Review:** a human operator resolves the identification via the review dashboard

---

### Decision Logic Flow

```
For each (track, frame):
    1. Run OCR on crop
       ├─ confidence ≥ 0.85 and number in event roster → IDENTIFIED (OCR)
       └─ else ↓

    2. Check DeepSORT continuous tracking
       ├─ track_id has confirmed team assignment and gap = 0 → IDENTIFIED (DeepSORT)
       └─ else ↓

    3. Run color matching against all registered profiles
       ├─ best match similarity ≥ 0.70 and not ambiguous → IDENTIFIED (Color)
       └─ else ↓

    4. Apply Kalman prediction + alliance constraint
       ├─ exactly one team expected at predicted position → IDENTIFIED (Kalman)
       └─ else ↓

    5. Flag for manual review
       → identification_method = UNKNOWN, flagged_for_review = True
```

---

## 11. Video Processing Pipeline

### Complete Pipeline Specification

```
Input Video (MP4 / MOV)
    ↓
[Frame Extraction]
  - OpenCV VideoCapture
  - Configurable sample rate (FRAME_SAMPLE_RATE)
  - Emit frame number + timestamp

    ↓
[Frame Preprocessing]
  - Resize to 640×640 for YOLO input
  - Retain original frame for crop extraction

    ↓
[YOLOv8 Detection]
  - Batch size 1 (per frame)
  - Output: list of (x1, y1, x2, y2, confidence) bounding boxes
  - Filter by YOLO_CONFIDENCE_THRESHOLD

    ↓
[DeepSORT Update]
  - Feed detections + frame to tracker
  - Output: list of (track_id, x1, y1, x2, y2)

    ↓
[Parallel Processing per track]:
  ├─ [OCR]
  │    crop → preprocess → EasyOCR → validate team number
  │
  ├─ [Color Match]
  │    crop → HSV histogram → Bhattacharyya compare profiles
  │
  ├─ [Kalman Update]
  │    detection → Kalman correct → velocity/heading estimate
  │
  └─ [Configuration Change Detection]
       bbox area delta → flag if ≥ 30 % change

    ↓
[Multi-Method Fusion]
  - Priority-ordered selection (OCR → DeepSORT → Color → Kalman)
  - Compute final confidence score
  - Set identification_method, flagged_for_review

    ↓
[Perspective Transform]
  - Apply per-event calibration matrix
  - Output: (x_field, y_field) in meters

    ↓
[MOVEMENT_TRACK Storage]
  - Batch insert every 30 frames to reduce DB round trips
  - Full record per (track_id, frame_number)

    ↓
Output: MovementTrack rows with team IDs, field positions, metadata
```

---

## 12. Data Models & Storage

### MOVEMENT_TRACK Extended Fields

| Column | Type | Description |
|--------|------|-------------|
| `track_id` | PK (int) | Surrogate key |
| `match_id` | FK → MATCH | Match this track belongs to |
| `team_id` | FK → TEAM (nullable) | Identified team; null if unknown |
| `frame_number` | int | Source video frame |
| `timestamp_ms` | int | Milliseconds from match start |
| `x_pixel` | float | Bounding box center X (pixels) |
| `y_pixel` | float | Bounding box center Y (pixels) |
| `x_field` | float | Field coordinate X (meters) |
| `y_field` | float | Field coordinate Y (meters) |
| `velocity` | float | Speed in m/s |
| `heading` | float | Direction of travel (degrees, 0 = +X axis) |
| `team_number_visible` | bool | Was team number visible this frame? |
| `identification_method` | enum | OCR / DEEPSORT / COLOR / KALMAN / UNKNOWN |
| `confidence_score` | float | 0.0–1.0 identification confidence |
| `interpolated` | bool | True if position was Kalman-predicted (no detection) |
| `bbox_size_change_pct` | float | % change vs rolling average |
| `configuration_changed` | bool | True if size change ≥ threshold |
| `flagged_for_review` | bool | True if confidence < 0.60 |
| `review_reason` | str (nullable) | Human-readable flag reason |
| `created_at` | datetime | Record creation timestamp |
| `updated_at` | datetime | Last update timestamp |

### ROBOT_COLOR_PROFILE Table

| Column | Type | Description |
|--------|------|-------------|
| `profile_id` | PK (int) | Surrogate key |
| `event_id` | FK → EVENT | Event this profile was calibrated for |
| `team_id` | FK → TEAM | Team whose robot was profiled |
| `color_histogram` | bytes | Serialized OpenCV histogram (numpy array) |
| `dominant_hue` | float | Primary hue value (0–180 HSV) |
| `dominant_saturation` | float | Primary saturation value (0–255) |
| `dominant_value` | float | Primary brightness value (0–255) |
| `calibration_date` | datetime | When profile was created |
| `confidence_level` | float | Quality of the calibration (0.0–1.0) |
| `created_at` | datetime | Record creation timestamp |

---

## 13. Performance Targets & Benchmarking

### Target Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Detection mAP@0.5 | > 95 % | YOLOv8 validation set |
| Tracking ID consistency | > 90 % | MOTA / IDF1 on annotated clips |
| Team identification accuracy | > 95 % | Ground truth video annotation |
| Frame processing speed (CPU) | ≥ 15 FPS | `time.perf_counter()` per frame |
| Frame processing speed (GPU) | ≥ 60 FPS | Same measurement |
| Per-frame latency | < 100 ms | Wall-clock time |
| Memory per worker | < 2 GB | `psutil` resident memory |

### Benchmarking Procedure

1. Curate a benchmark video set: 5 different FRC events, 3 matches each
2. Annotate ground truth: team position per frame, correct team ID per track
3. Run pipeline on benchmark set with metrics instrumentation
4. Compare per-method accuracy breakdown (OCR-only, color-only, tracking-only)
5. Run under varied conditions:
   - Different lighting (bright arena vs. dim practice field)
   - Fast robot movement (≥ 4 m/s)
   - Heavily occluded periods (autonomous near scoring zones)
   - Low team number visibility (robot rotated away from camera)

---

## 14. Error Handling & Recovery

### Error Scenarios & Solutions

#### 1. Detection Failure (no robots found in frame)

- **Cause:** YOLO confidence below threshold; frame blur; unusual lighting
- **Action:** Kalman-predict all active tracks; mark all as `interpolated = True`
- **Escalation:** if detection failure persists > 30 frames, flag all tracks for review

#### 2. OCR Failure

- **Cause:** team number not visible, low resolution, motion blur
- **Action:** fall back to color matching → DeepSORT tracking → Kalman prediction
- **Logging:** record OCR attempt result with confidence in task log

#### 3. Track Fragmentation

- **Cause:** DeepSORT drops a track due to prolonged occlusion
- **Action:** run re-identification algorithm on new track appearance; attempt to merge with historical team assignment
- **Fallback:** if re-identification fails, assign `team_id = None` until confirmed

#### 4. Configuration Change

- **Cause:** robot deploys/retracts a mechanism (elevator, arm, intake)
- **Action:** re-run OCR + color identification; maintain track ID
- **Fallback:** if re-identification fails, flag for review with `review_reason = "configuration_change"`

#### 5. Off-Field Robot

- **Cause:** robot tips over, is penalized and removed, or goes out of camera view
- **Action:** mark track as `off_field = True`; suspend Kalman prediction
- **Resume:** when detection reappears near last in-bounds position

### Logging & Debugging

- Every identification decision is logged: `(frame_number, track_id, method, confidence, team_id)`
- Frame-by-frame debug mode: write annotated frames to a temporary directory
- Visualization: bounding boxes with team IDs, method indicator, and confidence score overlaid
- Performance metrics: collected per-frame and summarized at task completion

---

## 15. Testing & Validation

### Unit Tests

| Test | What to Verify |
|------|---------------|
| `test_detection_accuracy` | YOLOv8 detects all 6 robots in a synthetic frame |
| `test_ocr_known_numbers` | OCR correctly reads team numbers from 50 labeled crops |
| `test_color_matching` | Color profiles match correct teams in 20 profile pairs |
| `test_kalman_prediction` | Predicted position within 0.5 m of true position after 5-frame gap |
| `test_perspective_transform` | Field coordinates within 0.1 m of ground truth for 10 corner points |
| `test_configuration_change` | 30 % area change triggers `configuration_changed = True` |

### Integration Tests

| Test | What to Verify |
|------|---------------|
| `test_pipeline_short_video` | 30-second synthetic video produces correct MovementTrack rows |
| `test_multi_method_fusion` | When OCR fails, system falls back to color matching correctly |
| `test_track_fragmentation` | Track re-identification works after a 10-frame gap |
| `test_db_batch_insert` | 1 000 MovementTrack rows inserted without errors |
| `test_error_recovery` | Corrupted frame does not crash the pipeline |

### Validation Tests

| Test | What to Verify |
|------|---------------|
| `validate_ground_truth_match` | ≥ 95 % team ID accuracy on 3 annotated matches |
| `validate_flagged_cases` | Flagged cases are all genuinely ambiguous |
| `validate_accuracy_stats` | Accuracy statistics report generates correctly |
| `validate_performance_profile` | Processing speed ≥ 15 FPS on standard hardware |

### Test Data Requirements

- 5+ different FRC game years
- Various lighting conditions (bright, dim, mixed)
- Various robot configurations (pre-deploy, mid-deploy, fully deployed)
- Team number visibility coverage (0 %, 30 %, 60 %, 100 % frames visible)

---

## 16. Configuration & Tuning

### Tunable Parameters

| Parameter | Default | Allowed Range | Effect |
|-----------|---------|---------------|--------|
| `YOLO_CONFIDENCE_THRESHOLD` | 0.45 | 0.3–0.7 | Detection sensitivity |
| `YOLO_NMS_IOU_THRESHOLD` | 0.40 | 0.3–0.5 | Duplicate suppression |
| `DEEPSORT_MAX_AGE` | 15 | 5–30 | Track survival without detection |
| `DEEPSORT_MIN_HITS` | 2 | 1–3 | Confirmations before track accepted |
| `OCR_CONFIDENCE_THRESHOLD` | 0.80 | 0.7–0.95 | OCR acceptance cutoff |
| `COLOR_MATCH_THRESHOLD` | 0.65 | 0.4–0.8 | Bhattacharyya similarity cutoff |
| `SIZE_CHANGE_THRESHOLD_PCT` | 30 | 20–50 | Bounding box change to flag config change |
| `MAX_GAP_FRAMES` | 15 | 5–30 | Frames before track is terminated |
| `FRAME_SAMPLE_RATE` | 1 | 1–5 | 1 = every frame; N = every Nth frame |

All parameters are configurable via environment variables or a YAML config file per event.

### Per-Event Calibration

| Step | Description |
|------|-------------|
| Color profile registration | Operator confirms robot → team assignment in first 10 s of match |
| Perspective matrix calibration | Four field corner points mapped from video to field coordinates |
| Game-specific constraints | Field boundary coordinates for the current FRC season |
| Team number validation list | Event team roster loaded from TBA; used to validate OCR output |

---

## 17. Hardware & Software Requirements

### Software Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Python | 3.9+ | Runtime |
| OpenCV | 4.5+ | Frame extraction, image processing |
| PyTorch | 2.0+ | YOLOv8 inference backend |
| ultralytics | 8.0+ | YOLOv8 model API |
| deep-sort-realtime | 1.3+ | DeepSORT tracker |
| EasyOCR | 1.6+ | Primary OCR engine |
| Tesseract / pytesseract | 5.0+ / 0.3+ | Fallback OCR engine |
| SQLAlchemy | 2.0+ | Database ORM |
| Celery | 5.3+ | Background task execution |
| NumPy | 1.24+ | Numerical operations |
| Pillow | 9.0+ | Image utility |

### Hardware — CPU Only

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16 GB |
| Storage | 50 GB | 200 GB (video files) |
| Estimated processing time | 2–5 min / match | 1–2 min / match |

### Hardware — GPU Accelerated (Optional)

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | NVIDIA GTX 1060 (CUDA 11.8) | NVIDIA RTX 3060 or better |
| VRAM | 4 GB | 8 GB |
| Estimated processing time | 30–60 s / match | 15–30 s / match |

GPU acceleration provides an estimated 5–10× speedup over CPU-only processing.

---

## 18. Phase 2 Integration

### Tier 2 Implementation

This strategy document directly informs the following Tier 2 implementation components:

| Component | File | Strategy Section |
|-----------|------|-----------------|
| YOLOv8 detection | `backend/app/services/video_processor.py` | §3 |
| DeepSORT tracker | `backend/app/services/video_processor.py` | §4 |
| OCR identification | `backend/app/services/identification_service.py` | §5 |
| Color matching | `backend/app/services/identification_service.py` | §6 |
| Kalman filter | `backend/app/services/kalman_tracker.py` | §7 |
| Configuration change detection | `backend/app/services/video_processor.py` | §8 |
| Multi-method fusion | `backend/app/services/identification_service.py` | §10 |
| Perspective transform | `backend/app/services/perspective_transform.py` | §11 |
| MovementTrack model | `backend/app/models/movement_track.py` | §12 |
| RobotColorProfile model | `backend/app/models/robot_color_profile.py` | §12 |
| Celery task | `backend/app/tasks/video_tasks.py` | §11 |

### Tier 3 Integration

- Phase statistics computed from `MovementTrack.x_field` / `y_field` / `velocity`
- Only records with `confidence_score ≥ 0.70` contribute to phase stats by default

### Tier 4 Integration

- Pre-computed heatmaps use `x_field` / `y_field` aggregated from `MovementTrack`
- Heatmap cache invalidated when new `MovementTrack` rows are inserted for a match

---

## 19. Future Enhancements & Scalability

### Post-Phase 2 Improvements

| Enhancement | Description |
|------------|-------------|
| Custom YOLOv8 fine-tuning | Transfer learning on FRC-specific dataset for higher mAP |
| Ensemble tracking | Consensus between DeepSORT and ByteTrack for higher ID stability |
| 3-D pose estimation | Estimate robot orientation from monocular video |
| Real-time field visualization | Live robot positions streamed during matches |
| Trajectory smoothing | Spline smoothing on recorded paths for cleaner heatmaps |
| Active learning | Route hard cases to human annotators to iteratively improve the model |

### Performance Optimization

| Technique | Expected Gain |
|-----------|-------------|
| H.264/H.265 hardware decode | Faster frame extraction |
| Batch GPU inference (N frames at once) | 2–4× throughput improvement |
| INT8 model quantization | 2× speedup, < 1 % accuracy loss |
| Model pruning | Smaller model size, faster loading |
| Frame skipping (FRAME_SAMPLE_RATE > 1) | Linear reduction in processing time |

---

## 20. Decision Records & Rationale

| Decision | Alternatives Considered | Rationale |
|----------|------------------------|-----------|
| **YOLOv8** for detection | Faster R-CNN, SSD, RT-DETR | Best balance of speed, accuracy, and Python tooling; pretrained weights fine-tune quickly |
| **DeepSORT** for tracking | ByteTrack, SORT, StrongSORT | Handles FRC robot count well; appearance features reduce ID switches during occlusion |
| **Multi-method identification** | Single-method (OCR only) | No single method works in all conditions; fusion dramatically improves overall accuracy |
| **Kalman filter** for prediction | Particle filter, MLP predictor | Simple, deterministic, efficient on CPU; constant-velocity model sufficient for FRC robots |
| **EasyOCR** as primary OCR | Tesseract, PaddleOCR, TrOCR | Best accuracy without GPU; clean Python API; supports digit-only restriction |
| **HSV + Bhattacharyya** for color | RGB histogram, CNN embeddings | HSV is lighting-invariant; Bhattacharyya distance is fast and well-understood |
| **OCR confidence threshold = 0.80** | 0.70, 0.90 | 0.70 produces too many false positives; 0.90 rejects too many correct readings; 0.80 balances precision/recall |
| **DeepSORT max_age = 15 frames** | 5, 30 | 5 frames too short for brief occlusions; 30 creates ghost tracks; 15 covers typical robot-to-robot occlusion duration |
| **CPU-first design** | GPU-required | Most FRC teams do not have GPU servers; CPU-only must work; GPU is an optional speedup |
