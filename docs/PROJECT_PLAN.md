# ScoutFRC — Project Implementation Plan

> **Version:** 1.0  
> **Status:** Planning  
> **Scope:** Automated video-based analytics system for the FIRST Robotics Competition

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack Recommendations](#2-tech-stack-recommendations)
3. [System Architecture](#3-system-architecture)
4. [Database Schema](#4-database-schema)
5. [Analytics Engine Design](#5-analytics-engine-design)
6. [Phased Development Roadmap](#6-phased-development-roadmap)
7. [Risk Assessment](#7-risk-assessment)

---

## 1. Project Overview

**ScoutFRC** automates robot performance tracking by analyzing official FRC match videos using computer vision. It replaces manual student scouting with objective, repeatable data and assists alliance captains in making data-driven picks during the elimination rounds.

| Attribute | Detail |
|---|---|
| **Primary Input** | Official FRC match video (YouTube / The Blue Alliance stream) |
| **Core AI Tools** | YOLOv8 (detection) + DeepSORT (multi-object tracking) |
| **Key Outputs** | Per-robot performance profiles, projected alliance scores, coverage-gap analysis |
| **Primary Users** | Drive coaches, alliance captains, scouting leads |

---

## 2. Tech Stack Recommendations

### 2.1 Computer Vision (CV) Backend

| Component | Recommended Tool | Rationale |
|---|---|---|
| Object Detection Model | **YOLOv8** (Ultralytics) | State-of-the-art real-time detection; pre-trained COCO weights fine-tunable on FRC bumper/game-piece images |
| Multi-Object Tracking | **DeepSORT** | Combines Kalman filtering with deep appearance embeddings; robust to brief occlusions between robots |
| Perspective Transform | **OpenCV `getPerspectiveTransform`** | Maps angled match-camera footage to a flat top-down field coordinate system (x, y) in metres |
| Video I/O | **FFmpeg + OpenCV VideoCapture** | Hardware-accelerated decoding; supports local files, RTSP streams, and YouTube via `yt-dlp` |
| CV Runtime | **Python 3.11** on **CUDA-capable GPU** (NVIDIA T4 / A10G recommended) | YOLOv8 and DeepSORT both have first-class PyTorch/CUDA support |
| Task Queue | **Celery + Redis** | Decouples video ingestion from analysis; enables parallel processing of multiple matches |

### 2.2 Database

| Component | Recommended Tool | Rationale |
|---|---|---|
| Primary RDBMS | **PostgreSQL 16** | Strong JSON support (for raw tracking data), window functions for analytics, mature ecosystem |
| ORM / Migrations | **SQLAlchemy 2 + Alembic** | Type-safe queries; Alembic handles schema evolution across phases |
| Time-Series Extension | **TimescaleDB** (optional) | Efficient hypertable storage for `MOVEMENT_TRACK` rows if tracking data volume is high |
| Cache Layer | **Redis** | Stores pre-computed analytics results and session data for the dashboard |

### 2.3 Application API

| Component | Recommended Tool | Rationale |
|---|---|---|
| API Framework | **FastAPI** | Async-native, auto-generates OpenAPI docs, integrates cleanly with SQLAlchemy |
| Background Workers | **Celery** (shared with CV backend) | Long-running video processing jobs triggered via API |
| Authentication | **JWT (python-jose)** | Stateless tokens; suitable for team-level access control |

### 2.4 Frontend Dashboard

The UX flows through four interconnected views:

```
Event Dashboard → Team List → Robot Profile → Alliance Builder
```

| Component | Recommended Tool | Rationale |
|---|---|---|
| UI Framework | **React 18 + TypeScript** | Component reuse across the four views; strong typing prevents data-shape mismatches |
| Build Tooling | **Vite** | Fast hot-module replacement; smaller bundle than CRA |
| State Management | **Zustand** | Lightweight; sufficient for cross-view shared state (selected event, alliance slots) |
| Data Fetching | **TanStack Query (React Query)** | Automatic caching, background refetching of match results |
| Charting & Heatmaps | **Recharts** + **D3.js** | Recharts for standard bar/line charts; D3 for the custom field heatmap overlay |
| Field Map Visualization | **Konva.js (React-Konva)** | Canvas-based rendering of the FRC field with robot trajectory overlays |
| Styling | **Tailwind CSS** | Utility-first; consistent design tokens across all four views |
| Hosting | **Vercel** or **Netlify** | Zero-config CI/CD for the React frontend |

### 2.5 Infrastructure & DevOps

| Component | Recommended Tool |
|---|---|
| Containerization | Docker + Docker Compose (dev); Kubernetes (prod) |
| CI/CD | GitHub Actions |
| GPU Compute | AWS EC2 `g4dn.xlarge` or GCP `n1-standard-4 + T4` for CV jobs |
| Object Storage | AWS S3 / GCS for processed video clips and exported heatmaps |
| Monitoring | Prometheus + Grafana for CV pipeline latency; Sentry for frontend errors |

---

## 3. System Architecture

### 3.1 High-Level Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION                            │
│                                                                  │
│  Official Match Video  ──►  yt-dlp / TBA API  ──►  S3 Raw Store │
└──────────────────────────────────┬───────────────────────────────┘
                                   │ Celery Job Trigger
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                   COMPUTER VISION PIPELINE                       │
│                                                                  │
│  1. Video Decode (FFmpeg)                                        │
│  2. Frame Extraction (configurable FPS, default 10 fps)          │
│  3. YOLOv8 Inference  ──► Bounding Boxes + Class Labels          │
│     (robots, game pieces, field elements)                        │
│  4. DeepSORT Tracking ──► Stable Robot IDs across frames         │
│  5. Perspective Transform ──► (pixel x,y) → field (x,y) metres  │
│  6. Event Classifier  ──► Scoring events, climb detect, penalty  │
└──────────────────────────────────┬───────────────────────────────┘
                                   │ Structured Records
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                       PERSISTENCE LAYER                          │
│                                                                  │
│  PostgreSQL ──► MATCH, ROBOT_PERFORMANCE, SCORING_EVENT,         │
│                 PHASE_STAT, MOVEMENT_TRACK                       │
│  Redis      ──► Cached analytics results (TTL = 1 match cycle)  │
└──────────────────────────────────┬───────────────────────────────┘
                                   │ SQL / ORM Queries
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                      ANALYTICS ENGINE                            │
│                                                                  │
│  • Scoring Breakdown Calculator (per phase success rates)        │
│  • Heatmap Aggregator (spatial density from MOVEMENT_TRACK)      │
│  • Cycle Time Calculator (average scoring loop duration)         │
│  • Alliance Fit Scorer (role profile matching)                   │
└──────────────────────────────────┬───────────────────────────────┘
                                   │ FastAPI REST / WebSocket
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                     FRONTEND DASHBOARD                           │
│                                                                  │
│  Event Dashboard ──► Team List ──► Robot Profile ──► Alliance    │
│                                                                  │
│  React + TypeScript + TanStack Query + Recharts + Konva          │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 CV Pipeline — Internal Module Detail

```
Frame Buffer
     │
     ▼
┌─────────────────────────────────────────┐
│  YOLOv8 Detector                        │
│  Input:  640×640 normalized frame       │
│  Output: [{bbox, confidence, class}]    │
│  Classes: robot_red, robot_blue,        │
│           game_piece, field_element     │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  DeepSORT Tracker                       │
│  Input:  YOLOv8 detections + frame      │
│  Output: [{track_id, bbox, class}]      │
│  Note:   track_id maps to team number   │
│          after first-frame calibration  │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Perspective Transform Module           │
│  Input:  bbox centre (px_x, px_y)       │
│  Config: 4 calibration corner points    │
│          (manually set per venue/cam)   │
│  Output: (field_x, field_y) in metres   │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Event Classifier                       │
│  Rules-based + lightweight CNN          │
│  Detects: score_attempt, score_success, │
│           pickup, climb_start,          │
│           climb_success, penalty        │
└─────────────────────────────────────────┘
```

### 3.3 Perspective Transform — Calibration Workflow

1. **Corner Selection:** An operator selects the four corners of the FRC field in one reference frame per venue/camera angle.
2. **Homography Matrix Computation:** `cv2.getPerspectiveTransform(src_pts, dst_pts)` computes a 3×3 homography matrix `H`.
3. **Per-Frame Warping:** Every robot centroid `(px, py)` is transformed via `cv2.perspectiveTransform` to yield field coordinates `(fx, fy)` in metres, normalised to the 2025 FRC field dimensions (16.46 m × 8.23 m).
4. **Matrix Persistence:** `H` is stored per `EVENT` record so that all matches at the same venue reuse the same calibration.

---

## 4. Database Schema

### 4.1 Entity-Relationship Summary

```
EVENT ──< MATCH ──< ALLIANCE ──< ROBOT_PERFORMANCE
                                        │
                                        ├──< PHASE_STAT
                                        ├──< SCORING_EVENT
                                        └──< MOVEMENT_TRACK

TEAM ──< ROBOT_PERFORMANCE (via team_id FK)
```

### 4.2 Table Definitions (DDL-style)

---

#### `EVENT`

Represents a single FRC regional, district, or championship event.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `event_id` | `SERIAL` | `PRIMARY KEY` | Internal surrogate key |
| `tba_event_key` | `VARCHAR(20)` | `UNIQUE NOT NULL` | The Blue Alliance event key (e.g., `2025calb`) |
| `name` | `VARCHAR(120)` | `NOT NULL` | Human-readable event name |
| `location` | `VARCHAR(200)` | | Venue name and city |
| `start_date` | `DATE` | `NOT NULL` | First day of competition |
| `end_date` | `DATE` | `NOT NULL` | Last day of competition |
| `season_year` | `SMALLINT` | `NOT NULL` | FRC season year |
| `perspective_matrix` | `JSONB` | | Serialised 3×3 homography matrix for this venue's camera |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT now()` | |

---

#### `TEAM`

Represents an FRC team (persistent across seasons).

| Column | Type | Constraints | Description |
|---|---|---|---|
| `team_id` | `SERIAL` | `PRIMARY KEY` | Internal surrogate key |
| `team_number` | `SMALLINT` | `UNIQUE NOT NULL` | Official FRC team number |
| `team_name` | `VARCHAR(120)` | | Team nickname |
| `school_name` | `VARCHAR(200)` | | Sponsoring school/organisation |
| `city` | `VARCHAR(100)` | | |
| `state_prov` | `VARCHAR(60)` | | |
| `country` | `VARCHAR(60)` | | |
| `rookie_year` | `SMALLINT` | | Year first competed |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT now()` | |

---

#### `MATCH`

Represents a single qualification or elimination match at an event.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `match_id` | `SERIAL` | `PRIMARY KEY` | Internal surrogate key |
| `event_id` | `INTEGER` | `FK → EVENT(event_id) NOT NULL` | Parent event |
| `tba_match_key` | `VARCHAR(30)` | `UNIQUE NOT NULL` | The Blue Alliance match key (e.g., `2025calb_qm14`) |
| `match_type` | `VARCHAR(15)` | `NOT NULL` | One of: `qualification`, `semifinal`, `final` |
| `match_number` | `SMALLINT` | `NOT NULL` | Match number within its type |
| `video_url` | `TEXT` | | Source video URL |
| `video_s3_key` | `TEXT` | | S3 object key for processed video |
| `processing_status` | `VARCHAR(20)` | `DEFAULT 'pending'` | One of: `pending`, `processing`, `complete`, `failed` |
| `played_at` | `TIMESTAMPTZ` | | Scheduled or actual match time |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT now()` | |

**Index:** `(event_id, match_type, match_number)` — supports event schedule queries.

---

#### `ALLIANCE`

Represents one of the two alliances (red or blue) in a match.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `alliance_id` | `SERIAL` | `PRIMARY KEY` | Internal surrogate key |
| `match_id` | `INTEGER` | `FK → MATCH(match_id) NOT NULL` | Parent match |
| `color` | `VARCHAR(4)` | `NOT NULL CHECK (color IN ('red','blue'))` | Alliance colour |
| `total_score` | `SMALLINT` | | Official final score |
| `rp_earned` | `SMALLINT` | | Ranking points earned |
| `won` | `BOOLEAN` | | True if this alliance won |

**Unique constraint:** `(match_id, color)` — one red alliance and one blue alliance per match.

---

#### `ROBOT_PERFORMANCE`

The central fact table linking a specific team to a specific match slot.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `perf_id` | `SERIAL` | `PRIMARY KEY` | Internal surrogate key |
| `match_id` | `INTEGER` | `FK → MATCH(match_id) NOT NULL` | Parent match |
| `team_id` | `INTEGER` | `FK → TEAM(team_id) NOT NULL` | Team that played |
| `alliance_id` | `INTEGER` | `FK → ALLIANCE(alliance_id) NOT NULL` | Which alliance |
| `alliance_position` | `SMALLINT` | `NOT NULL CHECK (alliance_position IN (1,2,3))` | Robot 1/2/3 in alliance |
| `track_id` | `SMALLINT` | | DeepSORT track ID assigned during CV processing |
| `auto_score` | `SMALLINT` | `DEFAULT 0` | Points scored in Autonomous phase |
| `teleop_score` | `SMALLINT` | `DEFAULT 0` | Points scored in Tele-op phase |
| `endgame_score` | `SMALLINT` | `DEFAULT 0` | Points scored in Endgame phase |
| `total_score_contribution` | `SMALLINT` | `GENERATED ALWAYS AS (auto_score + teleop_score + endgame_score) STORED` | |
| `fouls_drawn` | `SMALLINT` | `DEFAULT 0` | Fouls drawn against opponents |
| `fouls_committed` | `SMALLINT` | `DEFAULT 0` | Fouls committed against alliance |
| `no_show` | `BOOLEAN` | `DEFAULT false` | Robot did not appear on field |
| `disabled` | `BOOLEAN` | `DEFAULT false` | Robot was disabled mid-match |

**Unique constraint:** `(match_id, team_id)` — a team plays once per match.

---

#### `PHASE_STAT`

Aggregated statistics for a robot broken down by game phase.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `stat_id` | `SERIAL` | `PRIMARY KEY` | Internal surrogate key |
| `perf_id` | `INTEGER` | `FK → ROBOT_PERFORMANCE(perf_id) NOT NULL` | Parent performance record |
| `phase` | `VARCHAR(15)` | `NOT NULL CHECK (phase IN ('auto','teleop','endgame'))` | Game phase |
| `attempts` | `SMALLINT` | `DEFAULT 0` | Scoring attempts in this phase |
| `successes` | `SMALLINT` | `DEFAULT 0` | Successful scores in this phase |
| `success_rate` | `NUMERIC(5,4)` | `GENERATED ALWAYS AS (CASE WHEN attempts = 0 THEN NULL ELSE successes::numeric / attempts END) STORED` | Computed success percentage |
| `avg_cycle_time_s` | `NUMERIC(6,2)` | | Mean cycle time (seconds) |
| `min_cycle_time_s` | `NUMERIC(6,2)` | | Fastest cycle observed |
| `max_cycle_time_s` | `NUMERIC(6,2)` | | Slowest cycle observed |
| `distance_travelled_m` | `NUMERIC(8,2)` | | Total distance from movement track |

**Unique constraint:** `(perf_id, phase)` — one row per phase per performance.

---

#### `SCORING_EVENT`

Individual scoring moments detected by the CV event classifier.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `event_id` | `SERIAL` | `PRIMARY KEY` | Internal surrogate key |
| `perf_id` | `INTEGER` | `FK → ROBOT_PERFORMANCE(perf_id) NOT NULL` | Robot this event belongs to |
| `event_type` | `VARCHAR(30)` | `NOT NULL` | e.g., `score_attempt`, `score_success`, `pickup`, `climb_start`, `climb_success`, `penalty` |
| `phase` | `VARCHAR(15)` | `NOT NULL CHECK (phase IN ('auto','teleop','endgame'))` | Game phase when event occurred |
| `frame_number` | `INTEGER` | `NOT NULL` | Frame index in source video |
| `timestamp_s` | `NUMERIC(7,3)` | `NOT NULL` | Seconds from match start |
| `field_x_m` | `NUMERIC(6,3)` | | Robot x-position on field (metres) |
| `field_y_m` | `NUMERIC(6,3)` | | Robot y-position on field (metres) |
| `confidence` | `NUMERIC(4,3)` | | CV classifier confidence score (0–1) |
| `notes` | `TEXT` | | Optional manual annotation override |

**Index:** `(perf_id, phase, event_type)` — supports fast phase-breakdown queries.

---

#### `MOVEMENT_TRACK`

Raw positional samples for a robot throughout a match, emitted by the CV pipeline.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `track_id` | `BIGSERIAL` | `PRIMARY KEY` | Internal surrogate key |
| `perf_id` | `INTEGER` | `FK → ROBOT_PERFORMANCE(perf_id) NOT NULL` | Robot this sample belongs to |
| `frame_number` | `INTEGER` | `NOT NULL` | Source video frame index |
| `timestamp_s` | `NUMERIC(7,3)` | `NOT NULL` | Seconds from match start |
| `field_x_m` | `NUMERIC(6,3)` | `NOT NULL` | Robot x-position on field (metres) |
| `field_y_m` | `NUMERIC(6,3)` | `NOT NULL` | Robot y-position on field (metres) |
| `pixel_x` | `SMALLINT` | | Original pixel x (pre-transform) |
| `pixel_y` | `SMALLINT` | | Original pixel y (pre-transform) |
| `track_confidence` | `NUMERIC(4,3)` | | DeepSORT track confidence |
| `phase` | `VARCHAR(15)` | `NOT NULL CHECK (phase IN ('auto','teleop','endgame'))` | Game phase |

**Index:** `(perf_id, timestamp_s)` — primary time-ordered traversal for cycle detection.  
**Note:** For high-volume deployments, partition this table by `match_id` or convert to a TimescaleDB hypertable.

---

### 4.3 Relationship Summary

```
EVENT          (1) ──── (M) MATCH
MATCH          (1) ──── (2) ALLIANCE        [red, blue]
MATCH          (1) ──── (6) ROBOT_PERFORMANCE
ALLIANCE       (1) ──── (3) ROBOT_PERFORMANCE
TEAM           (1) ──── (M) ROBOT_PERFORMANCE
ROBOT_PERFORMANCE (1) ──── (3) PHASE_STAT   [auto, teleop, endgame]
ROBOT_PERFORMANCE (1) ──── (M) SCORING_EVENT
ROBOT_PERFORMANCE (1) ──── (M) MOVEMENT_TRACK
```

---

## 5. Analytics Engine Design

### 5.1 Scoring Breakdown Calculator

**Input:** `SCORING_EVENT` rows for a given `perf_id` (or aggregated across multiple matches).  
**Logic:**
1. Group events by `phase` (auto / teleop / endgame).
2. For each phase, compute:
   - `success_rate = COUNT(event_type='score_success') / NULLIF(COUNT(event_type='score_attempt'), 0)`
   - `points_per_match = SUM(points_value)` (joined from a game-year scoring table)
3. Store per-match results into `PHASE_STAT`; cross-match averages are computed on-the-fly via SQL window functions.

### 5.2 Cycle Time Calculator

**Input:** `MOVEMENT_TRACK` + `SCORING_EVENT` rows.  
**Logic:**
1. Identify cycles: a cycle begins at a `pickup` event and ends at the next `score_success` event for the same `perf_id`.
2. `cycle_time_s = score_success.timestamp_s − pickup.timestamp_s`
3. Outlier removal: drop cycles > 2 standard deviations from the per-robot mean (handles disabled periods).
4. Write `avg_cycle_time_s`, `min_cycle_time_s`, `max_cycle_time_s` back to the corresponding `PHASE_STAT` row.

### 5.3 Heatmap Generation

**Input:** All `MOVEMENT_TRACK` rows for a team across N matches.  
**Logic:**
1. Bin field positions into a configurable grid (default: 0.25 m × 0.25 m cells).
2. Count dwell time (frames × 1/fps) per cell.
3. Normalise to a 0–1 density scale.
4. Serialise the 2D density array as JSON; cache in Redis with a 5-minute TTL.
5. The frontend D3/Konva layer renders the heatmap by colouring each cell on the field SVG.

### 5.4 Alliance Fit Profiler

**Input:** Aggregated `PHASE_STAT` + `SCORING_EVENT` data for all teams at an event.  
**Logic:**
1. **Role Classifier:** Assign each team to one or more strategic roles based on weighted scoring:
   - **High-Cycle Driver:** low `avg_cycle_time_s` (fast cycles) + high `teleop` success rate.
   - **Auto Specialist:** high `auto` success rate + high `auto_score`.
   - **Climber / Endgame Anchor:** high `endgame` success rate.
   - **Defense Bot:** low personal scoring but high opponent `foul_drawn` contribution (inferred from low movement range).
2. **Alliance Gap Analysis:** Given the first captain's profile, identify the top-N teams that fill the missing roles.
3. **Projected Score:** Sum expected score contributions per alliance slot using per-match average scores, adjusted by a confidence weight (inverse of CV confidence variance).

---

## 6. Phased Development Roadmap

### Phase 1 — MVP: Detection, Tracking & Coordinate Mapping
**Goal:** Produce reliable (x, y, timestamp) positional records for every robot in every match video.

| Milestone | Description | Estimated Duration |
|---|---|---|
| 1.1 Data Ingestion | Implement video downloader (yt-dlp wrapper), S3 upload, and Celery job dispatch | 2 weeks |
| 1.2 YOLOv8 Fine-Tuning | Collect 500–1,000 labelled FRC frames; fine-tune YOLOv8n on robot/bumper classes | 3 weeks |
| 1.3 DeepSORT Integration | Integrate DeepSORT; implement track-to-team-number assignment via bumper-colour heuristic | 2 weeks |
| 1.4 Perspective Transform | Build calibration UI (4-point field corner picker); implement homography per event | 1 week |
| 1.5 Database Bootstrap | Deploy PostgreSQL schema (DDL from §4); implement Alembic migrations for all 7 tables | 1 week |
| 1.6 CV → DB Writer | Write `MOVEMENT_TRACK` and basic `ROBOT_PERFORMANCE` rows after each processed match | 1 week |
| 1.7 Basic API | FastAPI endpoints: `GET /events`, `GET /events/{id}/matches`, `GET /matches/{id}/robots` | 1 week |
| **Phase 1 Total** | | **~11 weeks** |

**Exit Criteria:**
- Robot positions tracked at ≥ 10 fps with < 5% ID-switch rate across a 2:30 match.
- Field coordinates within ± 0.3 m of ground truth for ≥ 90% of frames.

---

### Phase 2 — Analytics: Scoring Classification & Cycle Intelligence
**Goal:** Produce per-robot scoring breakdowns and cycle time statistics.

| Milestone | Description | Estimated Duration |
|---|---|---|
| 2.1 Event Classifier | Train lightweight CNN to classify scoring events from cropped robot ROIs; rules-based fallback | 3 weeks |
| 2.2 Scoring Event Writer | Populate `SCORING_EVENT` table; link to correct `phase` based on match timestamp | 1 week |
| 2.3 Phase Stat Calculator | Implement SQL + Python analytics for `PHASE_STAT` (success rates, cycle times) | 2 weeks |
| 2.4 Heatmap Service | Build heatmap aggregation service; Redis cache; REST endpoint `GET /teams/{id}/heatmap` | 1 week |
| 2.5 Alliance Fit Engine | Implement role classifier and gap-analysis algorithm from §5.4 | 2 weeks |
| 2.6 Extended API | Add endpoints: scoring breakdowns, phase stats, alliance fit suggestions | 1 week |
| **Phase 2 Total** | | **~10 weeks** |

**Exit Criteria:**
- Scoring event detection accuracy ≥ 85% F1 on a held-out match set.
- Cycle times within ± 1 second of manually annotated ground truth.

---

### Phase 3 — UX/UI: Dashboard, Robot Profiles & Alliance Builder
**Goal:** Deliver a polished, usable dashboard for alliance captains and scouting leads.

| Milestone | Description | Estimated Duration |
|---|---|---|
| 3.1 Event Dashboard | React view: event selector, match schedule, processing status indicators | 2 weeks |
| 3.2 Team List View | Sortable/filterable table of all teams; summary stats; role badges | 1 week |
| 3.3 Robot Profile View | Per-team detail: scoring charts (Recharts), phase breakdown, field heatmap (D3 + Konva) | 3 weeks |
| 3.4 Alliance Builder | Drag-and-drop 3-slot builder; real-time projected score; coverage gap visualisation | 3 weeks |
| 3.5 Authentication & Multi-Tenancy | JWT login; team-scoped data isolation | 1 week |
| 3.6 Export & Sharing | PDF/CSV export of scouting reports; shareable alliance links | 1 week |
| 3.7 Mobile Responsive Polish | Ensure core views are usable on tablets at pit/field | 1 week |
| **Phase 3 Total** | | **~12 weeks** |

**Exit Criteria:**
- Event Dashboard to Alliance Builder flow completes in ≤ 4 user interactions.
- Alliance projected score within ± 10% of actual final score for held-out elimination matches.

---

## 7. Risk Assessment

### 7.1 Lighting Variability

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| Overhead arena lighting causes inconsistent robot/bumper colour detection | High | High | Augment training data with brightness/contrast jitter; train separate YOLOv8 models per lighting condition; implement auto-exposure normalisation via OpenCV CLAHE before inference |

### 7.2 Bumper Visibility & Occlusion

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| Robots overlap, hiding bumper numbers from camera angle | High | Medium | DeepSORT appearance embedding maintains track IDs through short occlusions (< 2 s); add a secondary bumper-number OCR (Tesseract / PaddleOCR) as a confidence boost when robots separate |
| Bumper colour fades or is non-standard | Medium | Low | Fall back to team-number OCR; allow manual track-to-team override in the UI |

### 7.3 Real-Time / Throughput Requirements

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| Processing a 2:30 match faster than match pace (e.g., for live commentary) | High | Medium | Phases 1–3 focus on post-match analysis; real-time processing is a future enhancement beyond this plan. GPU batch inference at 30 fps is achievable on a T4 with YOLOv8n at 640px |
| Multiple matches submitted simultaneously during eliminations | Medium | High | Celery priority queue; scale GPU workers horizontally via Kubernetes |

### 7.4 Track Identity Errors (ID Switches)

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| DeepSORT assigns the wrong track ID to a robot after a collision | High | Medium | Post-process tracks with a bumper-colour consistency check; flag low-confidence track segments for manual review in the UI |

### 7.5 Camera Angle & Calibration Drift

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| The broadcast camera pans or zooms mid-match, invalidating the homography | High | Low (FRC broadcasts are mostly static) | Detect significant homography deviation frame-to-frame; trigger re-calibration or flag match for manual review |

### 7.6 Data Licensing & Privacy

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| The Blue Alliance / FIRST restricts programmatic video access | Medium | Medium | Obtain necessary API keys and comply with TBA terms of service; support manual video upload as a fallback |

### 7.7 Model Generalisation Across Seasons

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| Robot designs, bumper styles, and game pieces change every season | Medium | High | Modular YOLOv8 model registry per season; plan for 2–3 week annual re-labelling sprint before each season kickoff |

---

*End of ScoutFRC Project Implementation Plan v1.0*
