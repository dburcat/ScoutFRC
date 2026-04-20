# Phase 2 Tiered Development Plan

## Overview

This document outlines the comprehensive development plan for **Phase 2 of ScouterFRC** — a background daemon system with computer vision, real-time analytics, and AI-powered insights. The plan builds entirely on the Phase 1 foundation and is broken into **12 tiers** with detailed tasks, acceptance criteria, deliverables, and dependencies for each tier.

**Phase 2 Goal:** Transform ScouterFRC from a manual data collection tool into an AI-powered scouting intelligence system with automated video analysis, background daemons, real-time updates, field heatmaps, ML predictions, and mobile PWA capability.

**Prerequisite:** All 12 tiers of Phase 1 must be complete before starting Phase 2.

---

## Tier Breakdown

---

### Tier 1: Celery & Redis Setup

**Purpose:** Establish the background task processing infrastructure that all subsequent daemon tiers depend upon.

#### Tasks

1.1. Install and configure **Redis** (local and Docker-based)  
1.2. Install and configure **Celery** with Redis as the message broker  
1.3. Configure **Celery Beat** for periodic/scheduled tasks  
1.4. Create **Celery app factory** and integrate with FastAPI application lifecycle  
1.5. Configure **Flower** task monitoring UI  
1.6. Set up **retry logic** (exponential backoff) and dead-letter queue handling  
1.7. Configure **task routing** (separate queues for video, analytics, sync, reports)  
1.8. Set up **structured logging** for all Celery tasks  
1.9. Create **health-check endpoint** to verify broker connectivity  
1.10. Write unit and integration tests for task dispatch and result retrieval  

#### Acceptance Criteria

- ✅ Redis broker running and reachable from FastAPI and Celery workers
- ✅ Celery worker starts with `celery -A app.celery worker` without errors
- ✅ Celery Beat scheduler starts and logs scheduled task registration
- ✅ Flower UI accessible and displays running workers and task history
- ✅ A sample test task dispatched via API completes and returns a result
- ✅ Failed tasks retry with backoff and are logged with full tracebacks
- ✅ Health-check endpoint returns broker status
- ✅ All tests pass

#### Deliverables

- `backend/app/celery_app.py` — Celery application and configuration
- `backend/app/tasks/__init__.py` — task package initialization
- `backend/docker-compose.yml` — Redis and Flower service definitions
- `backend/tests/test_celery.py` — task dispatch tests

#### Dependencies

- Phase 1 complete (FastAPI backend, PostgreSQL, all models)

#### Key Decisions to Document

- Redis chosen as broker for simplicity and dual-use as cache store (Tier 4)
- Separate queues per task category to allow independent worker scaling
- Flower chosen for zero-config task monitoring in development

---

### Tier 2: Video Processing Pipeline

**Purpose:** Process uploaded match videos in the background, detect robots with YOLOv8, track them with DeepSORT, and persist movement trajectories to the database.

#### Tasks

2.1. Install **YOLOv8** (`ultralytics`) and **DeepSORT** libraries  
2.2. Create **video upload endpoint** (`POST /matches/{id}/video`) with file validation  
2.3. Implement `process_video_file` Celery task:
   - Extract frames at configurable FPS
   - Run YOLOv8 inference for robot bounding boxes
   - Apply DeepSORT for multi-object tracking across frames  
2.4. Implement **perspective matrix transformation** to convert pixel coordinates to field coordinates (feet/meters)  
2.5. Persist per-frame tracking data into `MovementTrack` model  
2.6. Implement **progress tracking** (task state updates at each phase: upload → extract → detect → track → save)  
2.7. Expose `GET /tasks/{task_id}/status` for frontend polling  
2.8. Handle corrupt/unsupported video files gracefully with user-friendly errors  
2.9. Add **GPU detection** with CPU fallback for inference  
2.10. Write integration tests using a short synthetic test video  

#### Acceptance Criteria

- ✅ Video upload endpoint accepts MP4/MOV, rejects unsupported formats with `422`
- ✅ Processing task appears in Flower with correct state transitions
- ✅ `MovementTrack` rows created for each detected robot per frame
- ✅ Field coordinates are within expected field boundary (0–54 ft × 0–27 ft)
- ✅ Progress updates visible at `GET /tasks/{id}/status` in real time
- ✅ Corrupt video files return a descriptive error without crashing the worker
- ✅ All integration tests pass on CPU (no GPU required)

#### Deliverables

- `backend/app/services/video_processor.py` — YOLOv8 + DeepSORT integration
- `backend/app/tasks/video_tasks.py` — Celery task definition
- `backend/app/models/movement_track.py` — `MovementTrack` ORM model
- `backend/alembic/versions/0002_add_movement_track.py` — migration
- `backend/tests/test_video_pipeline.py`

#### Dependencies

- Tier 1 (Celery & Redis)
- Phase 1 `Match` model (FK target for `MovementTrack`)

#### Key Decisions to Document

- YOLOv8 chosen for best accuracy/speed trade-off on FRC robot detection
- DeepSORT chosen for reliable multi-robot tracking without re-ID model
- Perspective transform matrix calibrated once per field layout per season

---

### Tier 3: Robot Performance Analytics

**Purpose:** Aggregate raw movement tracks into structured phase-level performance statistics (autonomous, teleop, endgame) and persist them as `PhaseStat` records.

#### Tasks

3.1. Create `PhaseStat` ORM model with fields:
   - `phase` (auto / teleop / endgame)
   - `distance_traveled`, `avg_velocity`, `max_velocity`
   - `time_in_scoring_zone`, `estimated_score`
   - `actions_detected` (JSON array of detected game actions)  
3.2. Implement `compute_robot_performance` Celery task:
   - Query `MovementTrack` rows for a match
   - Segment by game phase (0–15 s auto, 15–135 s teleop, 135–150 s endgame)
   - Compute velocity, acceleration, distance from coordinate deltas
   - Estimate scoring events using zone proximity heuristics  
3.3. Chain task automatically after `process_video_file` completes (Celery `chain`)  
3.4. Expose `GET /teams/{id}/performance` and `GET /matches/{id}/performance` endpoints  
3.5. Handle missing or sparse movement data gracefully (partial stats with confidence flag)  
3.6. Write unit tests for calculation functions (pure functions, no DB)  
3.7. Write integration tests that run analytics on pre-seeded `MovementTrack` data  

#### Acceptance Criteria

- ✅ `PhaseStat` rows created for every (team, match, phase) combination after processing
- ✅ Distance, velocity, and zone-time values are physically plausible
- ✅ Analytics task auto-triggered after video processing chain completes
- ✅ `GET /matches/{id}/performance` returns stats for all teams in the match
- ✅ Partial data returns stats with `"confidence": "low"` flag rather than erroring
- ✅ All unit and integration tests pass

#### Deliverables

- `backend/app/models/phase_stat.py` — `PhaseStat` ORM model
- `backend/alembic/versions/0003_add_phase_stat.py`
- `backend/app/tasks/analytics_tasks.py`
- `backend/app/services/performance_calculator.py`
- `backend/app/routers/performance.py`
- `backend/tests/test_analytics.py`

#### Dependencies

- Tier 2 (movement data must exist)

#### Key Decisions to Document

- Phase time boundaries match official FRC game timing (season-configurable constants)
- `actions_detected` stored as JSON to accommodate different game action sets per season

---

### Tier 4: Data Caching System

**Purpose:** Pre-compute expensive queries and cache results in Redis so that dashboard API responses are near-instant regardless of database size.

#### Tasks

4.1. Create `CacheService` wrapping Redis with typed get/set/invalidate helpers  
4.2. Implement `refresh_dashboard_cache` Celery Beat task (configurable interval, default 10 min):
   - Pre-compute and cache team rankings per event
   - Pre-compute and cache event summary statistics
   - Pre-compute and cache alliance projection data  
4.3. Add cache-aside pattern to hot read endpoints (`/events/{id}/rankings`, `/teams/{id}`, `/alliances`)  
4.4. Configure **TTL policies** per data type (rankings: 10 min, team profiles: 30 min, raw stats: 5 min)  
4.5. Implement **cache invalidation** hooks triggered on write operations (new match result, new scouting observation)  
4.6. Add **cache warm-up** task that runs on application startup  
4.7. Expose `GET /admin/cache/stats` endpoint (cache hit rate, key count, memory usage)  
4.8. Write tests for cache hit/miss behavior and invalidation logic  

#### Acceptance Criteria

- ✅ Hot endpoints respond in < 50 ms on warm cache
- ✅ Cache miss falls through to database without error
- ✅ TTL expiry causes automatic refresh on next request
- ✅ Write operations invalidate relevant cache keys within 1 second
- ✅ Warm-up task populates cache before first request after restart
- ✅ Cache stats endpoint returns meaningful metrics
- ✅ All tests pass

#### Deliverables

- `backend/app/services/cache_service.py`
- `backend/app/tasks/cache_tasks.py`
- `backend/app/routers/admin.py` (cache stats endpoint)
- `backend/tests/test_cache.py`

#### Dependencies

- Tier 1 (Redis running)
- Tier 3 (analytics data to cache)

#### Key Decisions to Document

- Cache-aside chosen over write-through for simplicity and eventual consistency tolerance
- Redis chosen over in-process cache to share state across multiple API workers

---

### Tier 5: Blue Alliance Continuous Sync

**Purpose:** Keep event, match, and team data automatically synchronized with The Blue Alliance API so the database reflects live competition results without manual intervention.

#### Tasks

5.1. Create `sync_tba_data` Celery Beat periodic task (configurable interval, default 5 min)  
5.2. Implement incremental sync logic:
   - Fetch events for configured year(s)
   - Fetch match results for active events
   - Update team rankings
   - Detect and flag newly posted match scores  
5.3. Handle **TBA API rate limits** (429 responses with backoff and retry)  
5.4. Record each sync run in `SyncLog` model (timestamp, entity type, records updated, status, error message)  
5.5. Expose `GET /admin/sync/status` and `POST /admin/sync/trigger` endpoints  
5.6. Send **failure alerts** (log error + optional webhook) when sync fails 3× consecutively  
5.7. Support **manual full-resync** to rebuild database from TBA from scratch  
5.8. Write integration tests using mocked TBA API responses  

#### Acceptance Criteria

- ✅ Sync task runs on schedule and updates changed records
- ✅ Unchanged records are not rewritten (upsert with change detection)
- ✅ Rate-limit responses trigger backoff and do not crash the worker
- ✅ `SyncLog` entries created for every sync run
- ✅ `GET /admin/sync/status` returns last sync time and status
- ✅ Manual trigger endpoint fires sync immediately
- ✅ All integration tests pass against mocked TBA responses

#### Deliverables

- `backend/app/tasks/tba_tasks.py`
- `backend/app/models/sync_log.py` — `SyncLog` ORM model
- `backend/alembic/versions/0004_add_sync_log.py`
- `backend/app/routers/admin.py` (sync endpoints, merged with Tier 4 admin router)
- `backend/tests/test_tba_sync.py`

#### Dependencies

- Tier 1 (Celery & Redis)
- Phase 1 TBA integration (existing HTTP client)

#### Key Decisions to Document

- Incremental sync preferred over full-resync to minimize TBA API quota usage
- `SyncLog` provides audit trail for debugging stale data reports

---

### Tier 6: Report Generation & Distribution

**Purpose:** Automatically generate PDF, CSV, and JSON scouting reports and distribute them to coaches and scouts via email or on-demand download.

#### Tasks

6.1. Install report generation libraries (`weasyprint` or `reportlab` for PDF, `pandas` for CSV)  
6.2. Implement `export_reports` Celery task with configurable output formats  
6.3. Create **PDF report template** including:
   - Event summary and rankings table
   - Per-team performance charts (bar/radar)
   - Alliance recommendation section  
6.4. Create **CSV export** (flat table: team, match, phase, metric columns)  
6.5. Create **JSON export** (structured hierarchy: event → teams → matches → stats)  
6.6. Implement **email distribution** using SMTP (configurable sender, recipient list)  
6.7. Store generated reports in **object storage** (local filesystem by default, S3-compatible via env config)  
6.8. Expose `POST /reports/generate` (trigger) and `GET /reports` (list) and `GET /reports/{id}/download` endpoints  
6.9. Implement **report versioning** (new report per trigger, old reports retained)  
6.10. Write tests for each output format with snapshot comparison  

#### Acceptance Criteria

- ✅ PDF report generated with correct data matches snapshot
- ✅ CSV export contains correct column headers and row count
- ✅ JSON export validates against defined schema
- ✅ Email sent successfully in test SMTP mode
- ✅ Reports accessible via download endpoint after generation
- ✅ Versioned reports list shows history
- ✅ All format tests pass

#### Deliverables

- `backend/app/tasks/report_tasks.py`
- `backend/app/services/report_generator.py`
- `backend/app/templates/reports/` — PDF Jinja2 template files
- `backend/app/routers/reports.py`
- `backend/tests/test_reports.py`

#### Dependencies

- Tier 3 (analytics computed)
- Tier 4 (cached rankings available for fast report build)

#### Key Decisions to Document

- WeasyPrint chosen for HTML-to-PDF so reports share CSS with frontend design system
- Object storage abstraction layer allows switching S3 providers without code changes

---

### Tier 7: Real-Time Dashboard Updates

**Purpose:** Stream live data to the frontend via WebSockets so the dashboard reflects match results and analytics updates without manual page refreshes.

#### Tasks

7.1. Create **FastAPI WebSocket router** (`/ws/events/{event_id}`, `/ws/matches/{match_id}`)  
7.2. Implement **connection manager** supporting multiple concurrent clients per channel  
7.3. Publish update events to Redis Pub/Sub from Celery tasks (on match update, analytics complete)  
7.4. Create **Redis subscriber** background thread in FastAPI to bridge Pub/Sub → WebSocket broadcast  
7.5. Define **event message schema** (JSON: `{ "type": "match_updated" | "analytics_ready", "payload": {...} }`)  
7.6. Handle client disconnects, reconnects, and authentication  
7.7. Create React `useWebSocket` hook with auto-reconnect and exponential backoff  
7.8. Update dashboard components to consume WebSocket events and merge with local state  
7.9. Add **connection status indicator** to UI (connected / reconnecting / offline)  
7.10. Load test with 50 concurrent WebSocket connections  

#### Acceptance Criteria

- ✅ Match score update triggers WebSocket broadcast to all connected clients within 1 second
- ✅ Analytics-ready event updates the relevant team card without page reload
- ✅ Client auto-reconnects within 5 seconds after network interruption
- ✅ 50 concurrent connections handled without memory leak or dropped messages
- ✅ `useWebSocket` hook exported and documented
- ✅ Connection status indicator visible in UI
- ✅ All tests pass

#### Deliverables

- `backend/app/api/websockets.py`
- `backend/app/services/broadcast_service.py` — Redis Pub/Sub bridge
- `frontend/src/hooks/useWebSocket.ts`
- `frontend/src/components/ConnectionStatus/` — connection indicator
- `backend/tests/test_websockets.py`

#### Dependencies

- Tier 1 (Redis Pub/Sub)
- Phase 1 (dashboard, React frontend)

#### Key Decisions to Document

- Redis Pub/Sub chosen over polling to keep Celery workers decoupled from WebSocket layer
- Message schema versioned to support backward-compatible dashboard updates

---

### Tier 8: Field Heatmaps & Visualizations

**Purpose:** Render robot movement trajectories and spatial heatmaps overlaid on the FRC field diagram so scouts can visually analyze team positioning and hot zones.

#### Tasks

8.1. Create **field diagram SVG component** (`FieldDiagram`) with accurate season field layout  
8.2. Implement `GET /matches/{id}/trajectories` endpoint returning `MovementTrack` coordinate arrays per team  
8.3. Render **trajectory lines** on field diagram, color-coded by team alliance (red/blue)  
8.4. Generate **spatial heatmap** from coordinate frequency using a 2D binning algorithm  
8.5. Render heatmap as SVG/Canvas gradient overlay on field diagram  
8.6. Add **playback controls** (play, pause, scrub, speed) to replay robot movement over time  
8.7. Implement **zoom and pan** on the field diagram  
8.8. Add **phase filter** toggle (auto / teleop / endgame overlays independently)  
8.9. Add **export heatmap** button (PNG download)  
8.10. Make trajectory points interactive (click to see timestamp, robot ID, coordinates)  

#### Acceptance Criteria

- ✅ Field diagram renders at correct aspect ratio for current FRC season field
- ✅ Trajectory lines drawn for all tracked robots in a match
- ✅ Heatmap visible with color gradient proportional to time-in-zone
- ✅ Playback scrub updates robot positions in real time
- ✅ Phase filter correctly isolates auto/teleop/endgame segments
- ✅ PNG export produces a valid image file
- ✅ Zoom/pan does not degrade at 60 fps for a full match dataset

#### Deliverables

- `frontend/src/components/FieldDiagram/FieldDiagram.tsx`
- `frontend/src/components/Heatmap/Heatmap.tsx`
- `frontend/src/components/PlaybackControls/PlaybackControls.tsx`
- `backend/app/routers/trajectories.py`
- `frontend/src/tests/FieldDiagram.test.tsx`

#### Dependencies

- Tier 2 (movement track data)
- Phase 1 (React frontend)

#### Key Decisions to Document

- SVG chosen for field diagram so it scales without rasterization artifacts
- Canvas chosen for heatmap layer to handle dense coordinate datasets at 60 fps
- Field layout constants versioned per FRC game year for multi-season reuse

---

### Tier 9: Performance Prediction & Ranking

**Purpose:** Use historical performance data to predict match outcomes, estimate team strength scores, generate AI-powered alliance recommendations, and track prediction accuracy.

#### Tasks

9.1. Define **team strength score** formula (weighted average of phase stats, win rate, OPR)  
9.2. Implement `predict_match_outcome` function:
   - Input: Red alliance team list, Blue alliance team list
   - Output: win probability per alliance, predicted score range, confidence level  
9.3. Train **lightweight ML model** (gradient boosting or logistic regression) on historical phase stats  
9.4. Create model **training script** and persist trained model artifact (`models/predictor.pkl`)  
9.5. Implement `update_predictions` Celery Beat task (runs after each new match result)  
9.6. Create `GET /events/{id}/rankings/predicted` endpoint with strength scores and predicted placements  
9.7. Generate **alliance selection recommendations** (`GET /events/{id}/draft/recommendations`)  
9.8. Track **prediction accuracy** over the event: log predicted vs. actual outcomes  
9.9. Expose **confidence levels** alongside all predictions in API responses  
9.10. Write unit tests for strength score formula and integration tests for prediction endpoint  

#### Acceptance Criteria

- ✅ Prediction endpoint returns win probability and confidence level
- ✅ Strength scores correlate positively with actual win rates on test data
- ✅ `update_predictions` task triggers after every match result update
- ✅ Alliance recommendations rank valid pick combinations
- ✅ Prediction accuracy log queryable at `GET /admin/predictions/accuracy`
- ✅ All tests pass

#### Deliverables

- `backend/app/services/predictor.py`
- `backend/scripts/train_predictor.py`
- `backend/models/predictor.pkl` (generated artifact, gitignored)
- `backend/app/tasks/prediction_tasks.py`
- `backend/app/routers/predictions.py`
- `backend/tests/test_predictor.py`

#### Dependencies

- Tier 3 (phase stat data required for training and inference)

#### Key Decisions to Document

- Gradient boosting chosen for interpretability and small-dataset performance
- Model artifact stored outside version control; training script reproducible from data
- Confidence level derived from model calibration curve

---

### Tier 10: Mobile App / Progressive Web App

**Purpose:** Make ScouterFRC fully functional on smartphones used by scouts on the competition field, with offline capability for environments with poor connectivity.

#### Tasks

10.1. Add **PWA manifest** (`manifest.json`) with app name, icons, theme, and display mode  
10.2. Implement **service worker** with offline caching strategy (cache-first for static assets, network-first for API)  
10.3. Create **mobile-optimized layout** with responsive breakpoints for 360 px–768 px screens  
10.4. Build **quick scouting form** optimized for one-handed touch input (large targets, minimal typing)  
10.5. Implement **local storage sync queue**: offline form submissions queued and auto-synced when online  
10.6. Add **photo capture** integration (`<input type="file" capture="environment">`) for attaching robot photos  
10.7. Add **voice note** recording (`MediaRecorder API`) for quick verbal observations  
10.8. Implement **home screen install prompt** (beforeinstallprompt event)  
10.9. Optimize **Lighthouse scores**: Performance ≥ 90, Accessibility ≥ 90, PWA ✅  
10.10. Test on real Android and iOS devices (or BrowserStack)  

#### Acceptance Criteria

- ✅ App installable to home screen on Android Chrome and iOS Safari
- ✅ Scouting form works fully offline and syncs on reconnection
- ✅ All offline-queued submissions reach the server without data loss
- ✅ Photo attachment uploads correctly after sync
- ✅ Lighthouse PWA audit passes all checks
- ✅ Lighthouse Performance score ≥ 90 on mobile preset
- ✅ No layout overflow on 360 px screen width

#### Deliverables

- `frontend/public/manifest.json`
- `frontend/src/service-worker.ts`
- `frontend/src/components/MobileScoutingForm/`
- `frontend/src/services/offlineQueue.ts`
- `frontend/src/tests/offlineQueue.test.ts`

#### Dependencies

- Phase 1 (React frontend, scouting form API endpoints)

#### Key Decisions to Document

- Service worker uses Workbox to reduce boilerplate and avoid cache-busting bugs
- Offline queue uses IndexedDB via `idb` for reliable storage across browser restarts

---

### Tier 11: Advanced Analytics & Machine Learning

**Purpose:** Apply machine learning to uncover deeper strategic insights: cluster teams by capability, detect anomalies, analyze movement strategies, and support what-if alliance simulations.

#### Tasks

11.1. Implement **team clustering** (k-means on phase stat feature vectors) to group teams by capability profile  
11.2. Implement **anomaly detection** (isolation forest) to flag unexpectedly high or low performances  
11.3. Create **team similarity scoring** (cosine similarity on feature vectors) for draft comparison  
11.4. Implement **time series trend analysis** (per-team metric trajectory over the event)  
11.5. Detect **team strategies** from movement patterns (e.g., corner camper, center scorer, defense bot)  
11.6. Implement **recommendation engine**: given a first pick, recommend best second and third picks  
11.7. Create **what-if alliance simulator**: user selects any 3 teams and sees projected score distribution  
11.8. Implement **skill tier classification** (Bronze / Silver / Gold / Elite) based on percentile rankings  
11.9. Expose all ML insights via new endpoints (`/teams/{id}/strategy`, `/events/{id}/clusters`, `/simulator`)  
11.10. Write tests for clustering stability, anomaly precision, and simulator output range  

#### Acceptance Criteria

- ✅ Clustering produces 4–6 stable clusters on a dataset of ≥ 30 teams
- ✅ Anomaly detection flags < 5 % of matches as anomalous on clean data
- ✅ Strategy detection labels at least 3 distinct strategy types per event
- ✅ What-if simulator returns projected score within physically plausible range
- ✅ Skill tiers distribute across all four levels in a balanced event dataset
- ✅ All new endpoints documented in OpenAPI
- ✅ All tests pass

#### Deliverables

- `backend/app/services/ml_service.py`
- `backend/app/services/strategy_detector.py`
- `backend/app/services/simulator.py`
- `backend/app/routers/analytics_advanced.py`
- `backend/app/tasks/ml_tasks.py`
- `backend/tests/test_ml_service.py`

#### Dependencies

- Tier 3 (phase stats)
- Tier 9 (prediction infrastructure)

#### Key Decisions to Document

- Scikit-learn chosen for clustering and anomaly detection (lightweight, no GPU required)
- Strategy detection rule set defined per FRC game year (season-configurable)
- Simulator uses Monte Carlo sampling over prediction model output distribution

---

### Tier 12: Testing, Documentation & Deployment

**Purpose:** Bring Phase 2 to full production readiness: comprehensive test coverage, operations documentation, production deployment, and monitoring.

#### Tasks

12.1. Write **end-to-end tests** covering complete flows:
   - Video upload → processing → analytics → dashboard update
   - TBA sync → cache refresh → WebSocket broadcast  
12.2. **Load test** video processing pipeline (10 concurrent video jobs)  
12.3. **Performance benchmark** all Phase 2 API endpoints (p95 < 200 ms with warm cache)  
12.4. **Security audit** all new components (input validation, file upload sanitization, WebSocket auth)  
12.5. Document all new API endpoints in OpenAPI and export to `docs/api/phase2_openapi.json`  
12.6. Write **Video Processing Guide** (`docs/VIDEO_PROCESSING_GUIDE.md`)  
12.7. Write **ML Model Documentation** (`docs/ML_MODELS.md`) covering training, evaluation, and updating  
12.8. Update `README.md` with Phase 2 setup instructions and architecture diagram  
12.9. Configure **production deployment** (Docker Compose or Kubernetes manifests for Celery workers, Redis, Flower)  
12.10. Set up **monitoring and alerting** (Prometheus metrics for worker queue depth, task failure rate, cache hit rate)  
12.11. Create **runbooks** for common operations: restart worker, clear stuck tasks, full resync, model retrain  
12.12. Verify all Phase 2 tiers function correctly in production environment  

#### Acceptance Criteria

- ✅ End-to-end tests cover all major Phase 2 flows and pass in CI
- ✅ Load test confirms 10 concurrent video jobs complete without worker crash
- ✅ p95 API response time < 200 ms on warm cache under load test conditions
- ✅ Security audit findings resolved; no critical or high vulnerabilities
- ✅ All Phase 2 endpoints appear in OpenAPI export
- ✅ Video Processing Guide reviewed by a non-author developer
- ✅ ML Model Documentation includes reproducible training steps
- ✅ Docker Compose `docker compose up` starts all Phase 2 services cleanly
- ✅ Prometheus metrics visible in Grafana dashboard
- ✅ Runbooks tested against staging environment

#### Deliverables

- `backend/tests/e2e/test_phase2_flows.py`
- `docs/VIDEO_PROCESSING_GUIDE.md`
- `docs/ML_MODELS.md`
- `docs/api/phase2_openapi.json`
- `deploy/docker-compose.phase2.yml`
- `deploy/k8s/` — Kubernetes manifests (optional)
- `monitoring/prometheus/` — metrics configuration
- `docs/runbooks/` — operational runbooks

#### Dependencies

- All Phase 2 tiers (1–11) complete

#### Key Decisions to Document

- Prometheus + Grafana chosen for observability (open-source, self-hosted)
- Docker Compose for development parity; Kubernetes manifests provided for production scale

---

## Summary Table

| Tier | Name | Primary Output | Key Dependency |
|------|------|----------------|----------------|
| 1 | Celery & Redis Setup | Background task infrastructure ready | Phase 1 complete |
| 2 | Video Processing Pipeline | Robot tracking data in database | Tier 1 |
| 3 | Robot Performance Analytics | Phase statistics computed automatically | Tier 2 |
| 4 | Data Caching System | Sub-50 ms API responses | Tier 1, Tier 3 |
| 5 | Blue Alliance Continuous Sync | Live TBA data without manual refresh | Tier 1 |
| 6 | Report Generation & Distribution | PDF/CSV/JSON reports delivered | Tier 3, Tier 4 |
| 7 | Real-Time Dashboard Updates | Live WebSocket dashboard | Tier 1, Phase 1 |
| 8 | Field Heatmaps & Visualizations | Interactive robot movement viewer | Tier 2, Phase 1 |
| 9 | Performance Prediction & Ranking | AI-powered match predictions | Tier 3 |
| 10 | Mobile App / PWA | Field-ready scouting on mobile | Phase 1 |
| 11 | Advanced Analytics & ML | Strategic clustering and simulation | Tier 3, Tier 9 |
| 12 | Testing, Documentation & Deployment | Phase 2 production-ready | All tiers |

---

## Parallelization Opportunities

The following tiers have no mutual dependency and can be developed in parallel by separate team members:

**Parallel Track A — Daemon Core:**
- Tier 1 → Tier 2 → Tier 3 → Tier 4 (sequential; each depends on the previous)

**Parallel Track B — Data Sync & Reports (starts after Tier 1):**
- Tier 5 (TBA Sync) — requires only Tier 1
- Tier 6 (Reports) — requires Tier 3 & 4 (wait for Track A to reach Tier 4)

**Parallel Track C — Frontend Enhancements (starts after Phase 1 and Tier 1):**
- Tier 7 (WebSockets) — requires Tier 1 and Phase 1
- Tier 8 (Heatmaps) — requires Tier 2 and Phase 1 (wait for Track A to reach Tier 2)
- Tier 10 (PWA) — requires only Phase 1 (can start immediately)

**Parallel Track D — ML & Intelligence (starts after Tier 3):**
- Tier 9 (Predictions) — requires Tier 3
- Tier 11 (Advanced ML) — requires Tier 3 and Tier 9

**Tier 12** (Testing & Deployment) depends on all other tiers.

---

## Key Decisions to Document

| Decision | Rationale |
|----------|-----------|
| Celery + Redis over other task queues | Mature ecosystem, Redis dual-use as cache and broker |
| YOLOv8 for detection | Best mAP/speed ratio; pretrained weights available |
| DeepSORT for tracking | No re-ID model required; handles FRC robot count (≤ 6 per field) |
| Gradient boosting for prediction | Interpretable, performs well on small tabular datasets |
| Scikit-learn for clustering/anomaly detection | Lightweight, no GPU required, rich algorithm set |
| Service worker with Workbox | Reduces cache-busting risk; production-grade PWA patterns |
| Prometheus + Grafana for monitoring | Open-source, self-hosted, integrates with Docker Compose |
| Redis Pub/Sub for WebSocket bridge | Decouples Celery workers from WebSocket server processes |

---

## Success Metrics for Phase 2 Completion

- ✅ Video processing pipeline handles a 2-minute match video end-to-end in < 10 minutes (CPU)
- ✅ Robot tracking accuracy > 85 % on standard FRC match footage
- ✅ Analytics computed automatically after every processed video
- ✅ Dashboard updates visible to connected clients within 1 second of data change
- ✅ Field heatmap renders correctly for a full match dataset
- ✅ Match outcome prediction accuracy > 70 % on held-out test matches
- ✅ PWA passes Lighthouse PWA audit and works offline in flight-mode test
- ✅ All ML insights available via API and rendered in the dashboard
- ✅ End-to-end test suite passes in CI with > 85 % code coverage on new modules
- ✅ Production deployment starts cleanly with `docker compose up`
- ✅ All Phase 2 API endpoints documented in OpenAPI
- ✅ Runbooks tested in staging environment
