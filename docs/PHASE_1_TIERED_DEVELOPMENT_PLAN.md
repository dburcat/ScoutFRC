# Phase 1 Tiered Development Plan

## Overview

This document outlines the comprehensive development plan for **Phase 1 of ScouterFRC** — a working data collection and dashboard system without computer vision. The plan focuses on database, API, and UI layers and is broken into **12 tiers** with detailed tasks, acceptance criteria, deliverables, and dependencies for each tier.

**Phase 1 Goal:** Build a fully functional scouting platform that allows teams to browse FRC events, view team/robot performance data, enter match observations manually, and analyze basic statistics.

---

## Tier Breakdown

---

### Tier 1: Database & ORM Setup

**Purpose:** Establish the data foundation for all subsequent tiers. Define the core relational schema and ensure migrations work cleanly.

#### Tasks

1.1. Install and configure **PostgreSQL** (local and Docker-based)  
1.2. Create **SQLAlchemy ORM models**:
   - `Event` — FRC event info (key, name, location, year)
   - `Team` — team number, name, school, rookie year
   - `Match` — match key, event FK, match number, type (qual/playoff)
   - `Alliance` — Red/Blue, match FK, team list, scores
   - `RobotPerformance` — team FK, match FK, basic performance fields  

1.3. Configure **Alembic** for database migrations  
1.4. Write initial migration script (`0001_initial_schema.py`)  
1.5. Create **database seed script** with realistic FRC test data  
1.6. Write model unit tests (relationships, constraints)  

#### Acceptance Criteria

- ✅ All five models exist with correct foreign keys and indexes
- ✅ `alembic upgrade head` runs without errors on a clean database
- ✅ `alembic downgrade base` cleanly reverts all migrations
- ✅ Seed script populates at least 1 event, 30 teams, 12 matches
- ✅ All model unit tests pass

#### Deliverables

- `backend/app/models/` — SQLAlchemy model files
- `backend/alembic/versions/0001_initial_schema.py`
- `backend/scripts/seed_db.py`
- `backend/tests/test_models.py`

#### Dependencies

- None (this is the foundation tier)

#### Key Decisions to Document

- PostgreSQL chosen for reliability and JSON support
- SQLAlchemy chosen for Pythonic ORM with Alembic migration support
- `RobotPerformance` kept generic to support Phase 2 CV data additions

---

### Tier 2: FastAPI Backend — Core Setup & CRUD Endpoints

**Purpose:** Create the REST API layer that the frontend will consume. Establish project structure, routing, and all core data-read endpoints.

#### Tasks

2.1. Scaffold **FastAPI project** with proper directory structure (`app/`, `routers/`, `schemas/`, `crud/`)  
2.2. Configure **database session management** (dependency injection)  
2.3. Create **Pydantic schemas** for all models (request/response)  
2.4. Implement **CRUD endpoints**:
   - `GET /events` — list all events
   - `GET /events/{id}` — event details
   - `GET /events/{id}/matches` — all matches for an event
   - `GET /events/{id}/teams` — all teams at an event
   - `GET /matches/{id}` — match details with alliances
   - `GET /teams` — all teams
   - `GET /teams/{id}` — team profile
   - `GET /teams/{id}/matches` — team's match history  

2.5. Configure **CORS** for frontend origin  
2.6. Add **error handling** middleware (404, 422, 500 with structured JSON responses)  
2.7. Verify **OpenAPI documentation** auto-generates at `/docs` and `/redoc`  

#### Acceptance Criteria

- ✅ All 8 endpoints return correct data with proper HTTP status codes
- ✅ Swagger UI accessible at `/docs`, ReDoc at `/redoc`
- ✅ CORS allows requests from `localhost:5173` (Vite dev server)
- ✅ Invalid IDs return `404` with descriptive error message
- ✅ Malformed requests return `422` with field-level validation errors
- ✅ API tests pass for all endpoints

#### Deliverables

- `backend/app/main.py`
- `backend/app/routers/events.py`, `matches.py`, `teams.py`
- `backend/app/schemas/` — Pydantic models
- `backend/app/crud/` — database query functions
- `backend/tests/test_api_endpoints.py`

#### Dependencies

- **Tier 1** must be complete (database models required)

#### Key Decisions to Document

- FastAPI chosen for automatic OpenAPI docs and async support
- Pydantic v2 for schema validation
- Separation of `crud/` from `routers/` for testability

---

### Tier 3: Authentication & Authorization

**Purpose:** Secure the API so only authenticated users can access scouting data and admin functions. Implement role-based access control.

#### Tasks

3.1. Install and configure **python-jose** for JWT token generation  
3.2. Create `User` model with fields: `id`, `username`, `hashed_password`, `role` (`admin`/`scout`/`viewer`)  
3.3. Add Alembic migration for `User` table  
3.4. Implement **password hashing** with `bcrypt`  
3.5. Create auth endpoints:
   - `POST /auth/register` — create new user account
   - `POST /auth/login` — returns JWT access token
   - `GET /auth/me` — return current user info  

3.6. Implement **JWT middleware** (`get_current_user` dependency)  
3.7. Add **role-based route guards**:
   - `viewer` — read-only access to all GET endpoints
   - `scout` — can submit match observations
   - `admin` — can sync TBA data, manage users  

3.8. Protect write endpoints with auth dependencies  

#### Acceptance Criteria

- ✅ `POST /auth/login` returns valid JWT on correct credentials
- ✅ Invalid credentials return `401 Unauthorized`
- ✅ Protected endpoints return `403` without valid token
- ✅ Admin-only routes reject `scout` and `viewer` roles
- ✅ Passwords stored as bcrypt hashes (never plaintext)
- ✅ JWT expiry enforced (configurable via env var)

#### Deliverables

- `backend/app/models/user.py`
- `backend/app/routers/auth.py`
- `backend/app/core/security.py` (JWT logic)
- `backend/app/core/dependencies.py` (auth middleware)
- `backend/alembic/versions/0002_add_users.py`
- `backend/tests/test_auth.py`

#### Dependencies

- **Tier 2** must be complete (FastAPI project structure required)

#### Key Decisions to Document

- JWT over session cookies for stateless API design
- Three-role system (`admin`/`scout`/`viewer`) to support team scouting workflows
- Bcrypt chosen for password hashing (industry standard)

---

### Tier 4: Blue Alliance API Integration

**Purpose:** Allow admins to import real FRC event data from The Blue Alliance (TBA) API to populate the database with live competition information.

#### Tasks

4.1. Register for **TBA API key** and add to environment config  
4.2. Create **TBA client module** (`backend/app/integrations/tba_client.py`):
   - `get_event(event_key)` — fetch event details
   - `get_event_teams(event_key)` — fetch all teams at event
   - `get_event_matches(event_key)` — fetch all match results  

4.3. Implement **TBA → database mapping functions**:
   - Map TBA event JSON → `Event` model
   - Map TBA team JSON → `Team` model
   - Map TBA match JSON → `Match` + `Alliance` models  

4.4. Create **admin sync endpoint**:
   - `POST /admin/sync-event/{event_key}` — fetches and stores full event  

4.5. Handle **TBA API error cases**:
   - Rate limiting (429) — implement retry with backoff
   - Invalid event key (404) — return descriptive error
   - Network failures — graceful error response  

4.6. Add **sync status tracking** (log what was imported)  

#### Acceptance Criteria

- ✅ `POST /admin/sync-event/2024casj` populates Event, Teams, and Matches from TBA
- ✅ Re-syncing an event updates existing records (upsert behavior)
- ✅ Invalid event key returns `404` with clear message
- ✅ TBA rate limits handled gracefully (no crash on 429)
- ✅ Sync only accessible to `admin` role

#### Deliverables

- `backend/app/integrations/tba_client.py`
- `backend/app/integrations/tba_mapper.py`
- `backend/app/routers/admin.py` (sync endpoint)
- `backend/tests/test_tba_integration.py` (with mocked TBA responses)

#### Dependencies

- **Tier 2** (CRUD endpoints) and **Tier 3** (admin auth) must be complete

#### Key Decisions to Document

- TBA chosen as data source (official FRC API)
- Upsert strategy on sync to support re-importing updated data
- Mocked TBA responses in tests to avoid API key dependency in CI

---

### Tier 5: React Dashboard — Setup & Event View

**Purpose:** Establish the frontend project and build the first user-facing view: the event dashboard where users can browse FRC events.

#### Tasks

5.1. Scaffold **React + TypeScript + Vite** project  
5.2. Install and configure **Tailwind CSS**  
5.3. Install **React Router** and set up routing structure  
5.4. Install **React Query (TanStack Query)** for data fetching and caching  
5.5. Install **Zustand** for global state management  
5.6. Create **API client** (`src/api/client.ts`) with base URL config  
5.7. Build **Event Dashboard** view (`/events`):
   - Fetch and display list of all events
   - Show event name, location, year, team count, match count
   - Filter by season year
   - Click event card to navigate to event detail  

5.8. Build **Event Detail** page (`/events/:id`):
   - Show event metadata
   - List teams attending with links to team profiles
   - List all matches with scores  

5.9. Build shared **Layout** component (nav bar, page wrapper)  
5.10. Implement **loading states** and **error states** for all data fetches  

#### Acceptance Criteria

- ✅ App runs at `localhost:5173` with `npm run dev`
- ✅ `/events` page shows all events with correct data
- ✅ Filtering by year narrows the event list
- ✅ Clicking an event navigates to event detail
- ✅ Loading spinner shown while fetching
- ✅ Error message shown if API is unavailable
- ✅ Responsive layout works on mobile (375px+)

#### Deliverables

- `frontend/` — full React project scaffold
- `frontend/src/pages/EventsPage.tsx`
- `frontend/src/pages/EventDetailPage.tsx`
- `frontend/src/components/Layout.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/api/events.ts`

#### Dependencies

- **Tier 2** (API endpoints for events) must be complete

#### Key Decisions to Document

- Vite chosen over CRA for faster dev experience
- React Query for server state (eliminates manual loading/error state management)
- Zustand for minimal client state (avoid Redux overhead)

---

### Tier 6: React Dashboard — Team & Match Views

**Purpose:** Build the team profile and match detail views so users can drill into specific robot performance data.

#### Tasks

6.1. Build **Team List View** (`/events/:id/teams`):
   - Show all teams attending the event
   - Display team number, name, school
   - Show match count for this event
   - Link to individual team profile  

6.2. Build **Robot Profile View** (`/teams/:id`):
   - Team name, number, rookie year
   - Matches played at current event
   - Match stats from TBA data:
     - Matches played
     - Average score
     - Win/loss record
   - Alliance breakdown (Red/Blue matches)
   - Match history table with scores  

6.3. Build **Match Detail View** (`/matches/:id`):
   - Red alliance: teams + scores
   - Blue alliance: teams + scores
   - Match result (winner)
   - Links to team profiles  

6.4. Add **breadcrumb navigation** (Event → Teams → Team Profile)  
6.5. Add **search/filter** on Team List (by team number or name)  

#### Acceptance Criteria

- ✅ Team List shows all teams for an event with correct counts
- ✅ Team search filters results in real time
- ✅ Robot Profile shows correct win/loss record and average score
- ✅ Match Detail shows both alliances with team links
- ✅ All navigation flows work (forward and back)
- ✅ Pages handle empty data gracefully (no teams, no matches)

#### Deliverables

- `frontend/src/pages/TeamListPage.tsx`
- `frontend/src/pages/TeamProfilePage.tsx`
- `frontend/src/pages/MatchDetailPage.tsx`
- `frontend/src/components/Breadcrumb.tsx`
- `frontend/src/api/teams.ts`
- `frontend/src/api/matches.ts`

#### Dependencies

- **Tier 5** (frontend scaffold + Event views) must be complete
- **Tier 2** (team and match API endpoints) must be complete

#### Key Decisions to Document

- Stats calculated on the frontend from match data (avoids complex backend aggregation in early tier)

---

### Tier 7: Alliance Builder & Scouting Form

**Purpose:** Build the two primary interactive tools: the Alliance Builder for match strategy and the Manual Data Entry form for scout observations.

#### Tasks

7.1. Build **Alliance Builder** (`/alliance-builder`):
   - Select up to 3 robots for Red alliance
   - Select up to 3 robots for Blue alliance
   - Calculate projected score (simple average of team scores)
   - Save/load alliance configurations  

7.2. Create **Alliance backend endpoint**:
   - `POST /alliances` — save alliance configuration
   - `GET /alliances` — list saved alliances
   - `GET /alliances/{id}` — get specific alliance  

7.3. Build **Scouting Form** (`/scout/match/:matchId`):
   - Match selector (event → match → team)
   - Observation fields:
     - Notes / comments (text area)
     - Manual score entry
     - Checkbox fields for game-specific actions
     - Rating sliders (1–5) for subjective assessments
   - Form validation (required fields, score range)
   - Confirmation dialog before submit  

7.4. Create **scouting submission endpoint**:
   - `POST /performances` — submit match observation
   - Updates `RobotPerformance` table  

7.5. Add **Alembic migration** for any new fields  

#### Acceptance Criteria

- ✅ Alliance Builder shows real-time projected score as teams are added
- ✅ Alliance can be saved and retrieved
- ✅ Scouting form validates all required fields before submit
- ✅ Submitted data appears in team's Robot Profile view
- ✅ Form confirmation prevents accidental submission
- ✅ Only `scout` and `admin` roles can submit scouting data

#### Deliverables

- `frontend/src/pages/AllianceBuilderPage.tsx`
- `frontend/src/pages/ScoutingFormPage.tsx`
- `frontend/src/components/AllianceSelector.tsx`
- `backend/app/routers/alliances.py`
- `backend/app/routers/performances.py`
- `backend/app/models/alliance.py` (if not in Tier 1)

#### Dependencies

- **Tier 3** (auth, role guards) must be complete
- **Tier 6** (team views, match data) must be complete

#### Key Decisions to Document

- Alliance projected score uses simple average (OPR-based scoring is Phase 2)
- Scouting form fields kept generic to support future game customization

---

### Tier 8: Basic Analytics & Charts

**Purpose:** Add data visualization so coaches can quickly identify top-performing teams and trends across the event.

#### Tasks

8.1. Install **Recharts** library  
8.2. Build **Team Rankings View** (`/events/:id/rankings`):
   - Teams ranked by average score
   - Win/loss record per team
   - Sortable table (by score, wins, matches played)  

8.3. Add **charts to Robot Profile**:
   - Bar chart: score distribution across matches
   - Line chart: score trend over the event  

8.4. Build **Event Analytics Page** (`/events/:id/analytics`):
   - Bar chart: top 10 teams by average score
   - Pie chart: win distribution by alliance (Red vs. Blue)
   - Line chart: match scores over time (event progression)  

8.5. Create **backend analytics endpoints**:
   - `GET /events/{id}/rankings` — computed team rankings
   - `GET /events/{id}/stats` — event-level aggregate stats  

8.6. Implement **CSV export** for rankings data  

#### Acceptance Criteria

- ✅ Rankings table correctly ranks teams by average score
- ✅ All three chart types render without errors
- ✅ CSV export downloads with correct data
- ✅ Charts show correct data when a team has only 1 match
- ✅ Charts show correct data when scores are tied

#### Deliverables

- `frontend/src/pages/RankingsPage.tsx`
- `frontend/src/pages/EventAnalyticsPage.tsx`
- `frontend/src/components/charts/ScoreBarChart.tsx`
- `frontend/src/components/charts/ScoreTrendChart.tsx`
- `frontend/src/components/charts/WinPieChart.tsx`
- `backend/app/routers/analytics.py`
- `backend/tests/test_analytics.py`

#### Dependencies

- **Tier 4** (TBA data import) — real match data needed for meaningful charts
- **Tier 6** (team/match views) must be complete

#### Key Decisions to Document

- Recharts chosen for ease of use with React
- No advanced heatmaps or field diagrams in Phase 1 (Phase 2 with CV)
- Backend computes rankings to keep frontend logic minimal

---

### Tier 9: API Integration — Scouting Endpoints

**Purpose:** Complete and harden the full API surface for scouting workflows, ensuring all data flows between frontend and backend are robust and well-tested.

#### Tasks

9.1. Audit all existing endpoints for **missing edge cases**  
9.2. Add **pagination** to list endpoints (`/events`, `/teams`, `/matches`)  
9.3. Add **filtering parameters** to list endpoints (by year, event, team number)  
9.4. Implement **bulk operations**:
   - `POST /performances/bulk` — submit multiple observations at once  

9.5. Add **data export endpoints**:
   - `GET /events/{id}/export` — full event data as JSON
   - `GET /events/{id}/export/csv` — rankings as CSV  

9.6. Implement **request rate limiting** on write endpoints  
9.7. Add **API versioning prefix** (`/api/v1/`)  
9.8. Update OpenAPI docs to reflect all new endpoints  

#### Acceptance Criteria

- ✅ Pagination works on all list endpoints (page, page_size params)
- ✅ Filtering works on events by year, teams by number/name
- ✅ Bulk performance submission accepts up to 50 records
- ✅ Export endpoints return correctly formatted JSON and CSV
- ✅ All endpoints documented in Swagger UI
- ✅ Rate limiting returns `429` with `Retry-After` header

#### Deliverables

- Updated router files with pagination + filtering
- `backend/app/routers/export.py`
- `backend/app/middleware/rate_limit.py`
- `backend/tests/test_pagination.py`
- `backend/tests/test_export.py`

#### Dependencies

- **Tiers 2–8** should be complete or in progress
- **Tier 3** (auth) required for rate limiting by user

#### Key Decisions to Document

- Cursor-based vs. offset pagination — offset chosen for simplicity in Phase 1
- API versioning added to support future breaking changes without disrupting clients

---

### Tier 10: Comprehensive Testing & Documentation

**Purpose:** Achieve high test coverage across the full stack and produce documentation sufficient for a new developer to set up and run the project.

#### Tasks

10.1. Write **backend unit tests** for all CRUD functions  
10.2. Write **backend integration tests** for all API endpoints (using `TestClient`)  
10.3. Write **frontend unit tests** for utility functions and hooks (Vitest)  
10.4. Write **frontend component tests** for key components (React Testing Library)  
10.5. Write **end-to-end tests** for critical user flows (Playwright or Cypress):
   - Login → browse event → view team profile
   - Admin sync TBA event → verify data appears in UI
   - Scout submits match observation → data visible in profile  

10.6. Write **API documentation** (beyond auto-generated Swagger):
   - Authentication guide
   - TBA sync workflow
   - Data model reference  

10.7. Write **developer setup guide** (`docs/DEVELOPMENT_SETUP.md`)  
10.8. Write **deployment guide** (`docs/DEPLOYMENT.md`)  

#### Acceptance Criteria

- ✅ Backend test coverage ≥ 80%
- ✅ All critical API endpoints have integration tests
- ✅ All 3 E2E user flows pass
- ✅ New developer can run project locally following setup guide
- ✅ All tests run in CI with `pytest` (backend) and `npm test` (frontend)

#### Deliverables

- `backend/tests/` — complete test suite
- `frontend/src/__tests__/` — component and unit tests
- `e2e/` — E2E test suite
- `docs/DEVELOPMENT_SETUP.md`
- `docs/DEPLOYMENT.md`
- `docs/API_REFERENCE.md`

#### Dependencies

- **Tiers 1–9** should be substantially complete before full E2E tests are written

#### Key Decisions to Document

- Pytest + `httpx` TestClient for backend integration tests
- Vitest + React Testing Library for frontend (consistent with Vite ecosystem)
- E2E tests run against a seeded test database

---

### Tier 11: Deployment & CI/CD Pipeline

**Purpose:** Containerize the application and establish automated pipelines so code changes are automatically tested and deployable.

#### Tasks

11.1. Write **Dockerfile** for FastAPI backend  
11.2. Write **Dockerfile** for React frontend (multi-stage build with Nginx)  
11.3. Write **`docker-compose.yml`** for local full-stack deployment:
   - `postgres` service
   - `backend` service
   - `frontend` service  

11.4. Write **`docker-compose.prod.yml`** for production variant  
11.5. Set up **GitHub Actions CI workflow** (`.github/workflows/ci.yml`):
   - On PR: lint, type-check, run all tests
   - On merge to `main`: build Docker images  

11.6. Configure **environment variable management**:
   - `.env.example` files for backend and frontend
   - Document all required env vars  

11.7. Configure **Nginx** for frontend serving and API proxying  
11.8. Write **health check endpoints** (`GET /health`)  

#### Acceptance Criteria

- ✅ `docker-compose up` starts the full stack from scratch
- ✅ `docker-compose up` includes database migrations automatically
- ✅ GitHub Actions CI runs all tests on every PR
- ✅ Health check endpoint returns `200 OK` with service status
- ✅ `.env.example` documents all required configuration variables
- ✅ Frontend production build served correctly via Nginx

#### Deliverables

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `.github/workflows/ci.yml`
- `backend/.env.example`
- `frontend/.env.example`
- `backend/app/routers/health.py`

#### Dependencies

- **Tier 10** (tests must exist to run in CI)
- **Tiers 1–9** must be functionally complete

#### Key Decisions to Document

- Docker Compose for simplicity (Kubernetes is Phase 2+)
- GitHub Actions chosen as CI (already used by repository)
- Nginx reverse proxy consolidates frontend + API to single origin

---

### Tier 12: Final Integration & Phase 1 Completion

**Purpose:** Perform end-to-end integration verification, fix any remaining issues, and confirm Phase 1 is complete and ready for stakeholder review.

#### Tasks

12.1. Run **full integration walkthrough** against production Docker Compose setup  
12.2. Perform **data integrity checks**:
   - Sync a real TBA event and verify all data flows to UI correctly
   - Submit scouting observations and verify they appear in analytics  

12.3. Fix any **bugs or regressions** found during integration walkthrough  
12.4. Update **MASTER_PROGRESS_DASHBOARD.md** to reflect final completion status  
12.5. Tag repository with **`v1.0.0-phase1`** release  
12.6. Write **Phase 1 Summary document** (`docs/PHASE_1_SUMMARY.md`):
   - What was built
   - Known limitations
   - What Phase 2 builds upon  

12.7. Conduct **stakeholder demo** preparation:
   - Seed demo data for a real FRC event
   - Prepare walkthrough of all 4 main views  

#### Acceptance Criteria

- ✅ All 12 tiers' acceptance criteria are met
- ✅ Full stack runs from `docker-compose up` with no manual steps
- ✅ Real FRC event data syncs and displays correctly end-to-end
- ✅ Scouting workflow completes without errors
- ✅ Alliance Builder calculates and saves correctly
- ✅ Analytics charts display correct data
- ✅ Repository tagged `v1.0.0-phase1`

#### Deliverables

- `docs/PHASE_1_SUMMARY.md`
- Updated `docs/MASTER_PROGRESS_DASHBOARD.md`
- Git tag `v1.0.0-phase1`
- Demo seed data script

#### Dependencies

- **All previous tiers (1–11)** must be complete

#### Key Decisions to Document

- Phase 1 explicitly excludes computer vision (reserved for Phase 2)
- Phase 1 analytics use simple averages (OPR/EPA reserved for Phase 2)

---

## Summary Table

| Tier | Name | Key Output | Dependencies |
|------|------|-----------|--------------|
| 1 | Database & ORM Setup | Schema, migrations, seed data | None |
| 2 | FastAPI Backend — Core Setup | REST API, Swagger UI | Tier 1 |
| 3 | Authentication & Authorization | JWT auth, role-based access | Tier 2 |
| 4 | Blue Alliance API Integration | TBA sync endpoint | Tiers 2, 3 |
| 5 | React Dashboard — Event View | Frontend scaffold, event pages | Tier 2 |
| 6 | React Dashboard — Team & Match Views | Team profile, match detail | Tiers 2, 5 |
| 7 | Alliance Builder & Scouting Form | Alliance builder, scouting form | Tiers 3, 6 |
| 8 | Basic Analytics & Charts | Rankings, charts, CSV export | Tiers 4, 6 |
| 9 | API Integration — Scouting Endpoints | Pagination, filtering, exports | Tiers 2–8 |
| 10 | Comprehensive Testing & Documentation | Full test suite, dev docs | Tiers 1–9 |
| 11 | Deployment & CI/CD Pipeline | Docker, GitHub Actions CI | Tier 10 |
| 12 | Final Integration & Phase 1 Completion | v1.0.0-phase1 release | Tiers 1–11 |

---

## Parallelization Opportunities

The following tiers can be worked on in parallel once their dependencies are met:

```
Tier 1 (DB)
    │
    ▼
Tier 2 (FastAPI)
    │
    ├──────────────────┐
    ▼                  ▼
Tier 3 (Auth)     Tier 5 (React Scaffold)
    │                  │
    ├──────────┐        ▼
    ▼          │   Tier 6 (Team/Match Views)
Tier 4 (TBA)  │        │
              │        ├──────────────────┐
              └──────► Tier 7 (Alliance+Scout)
                            │
                   Tier 8 (Analytics) ──► Tier 9 (API hardening)
                                              │
                                         Tier 10 (Testing)
                                              │
                                         Tier 11 (Deployment)
                                              │
                                         Tier 12 (Final Integration)
```

**Parallel execution groups:**
- **Group A:** Tier 3 + Tier 5 (both depend only on Tier 2)
- **Group B:** Tier 4 + Tier 6 (can start simultaneously after Groups A)
- **Group C:** Tier 7 + Tier 8 (can start simultaneously after Group B)

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Database | PostgreSQL | Reliability, JSON support, FRC data relationships |
| ORM | SQLAlchemy + Alembic | Pythonic, strong migration support |
| Backend framework | FastAPI | Auto OpenAPI docs, async, Pydantic validation |
| Auth | JWT | Stateless, works for API-first architecture |
| Frontend framework | React + TypeScript + Vite | Type safety, fast dev server |
| State management | React Query + Zustand | Separation of server/client state |
| CSS | Tailwind CSS | Rapid UI development, responsive by default |
| Charts | Recharts | React-native, simple API |
| Containerization | Docker Compose | Simple local + production deployment |
| CI/CD | GitHub Actions | Already used in repository |
| FRC data source | The Blue Alliance API | Official FRC data, free API |

---

## Success Metrics

Phase 1 is considered **complete** when all of the following are true:

- ✅ All 12 tiers' acceptance criteria are met
- ✅ A real FRC event can be imported from TBA and browsed in the UI
- ✅ Scouts can submit match observations through the web form
- ✅ Coaches can view team rankings and performance charts
- ✅ Alliance Builder saves and calculates projected scores
- ✅ Full stack runs with `docker-compose up` from a clean checkout
- ✅ All automated tests pass in CI
- ✅ Repository tagged `v1.0.0-phase1`
