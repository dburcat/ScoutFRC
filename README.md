# ScoutFRC

**ScoutFRC** is an automated data collection and analytics system for the FIRST Robotics Competition (FRC). It provides alliance captains with objective, data-driven robot performance profiles for elimination picks — starting with a full-featured scouting dashboard and progressing to computer vision-based video analysis.

## Key Features (Planned)

- 🗄️ **PostgreSQL** relational schema — 11 entities across 3 phases (EVENT → TEAM → MATCH → ROBOT_PERFORMANCE → …) — see [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md)
- ⚡ **FastAPI Backend** — CRUD endpoints, authentication, Blue Alliance API integration
- 📊 **React Dashboard** — event view, team profiles, match data, and basic analytics
- 🤝 **Alliance Builder** — drag-and-drop tool with projected scores and coverage-gap analysis
- 🔄 **Background Daemons** — Celery workers for video processing, data sync, and report generation
- 🤖 **YOLOv8 + DeepSORT** — real-time robot detection and multi-object tracking (Phase 2)
- 🗺️ **Field Heatmaps** — maps robot movement to top-down field coordinates (Phase 2)

## Quick Start

Begin with **Phase 1** — the Core MVP Foundation. Follow the tiers in order:

1. Start at [Phase 1, Tier 1: Database & ORM Setup](docs/PHASE_1_TIERED_DEVELOPMENT_PLAN.md)
2. Complete all 12 Phase 1 tiers before moving to Phase 2
3. See [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) for full architecture and risk assessment

## Development Roadmap

ScoutFRC is built across **3 phases**, each containing **12 tiers**. Complete phases in order — Phase 3 is a future roadmap only.

---

### Phase 1: Core MVP Foundation (12 Tiers)

**Goal:** Build a working data collection and dashboard system — no computer vision yet.

**Key Features:**
- Database & ORM (PostgreSQL + SQLAlchemy + Alembic)
- FastAPI backend with authentication and Blue Alliance API integration
- React dashboard with event, team, and match views
- Alliance Builder and scouting forms
- Basic analytics and charts
- Deployment & CI/CD pipeline

📖 **Detailed Plan:** [`docs/PHASE_1_TIERED_DEVELOPMENT_PLAN.md`](docs/PHASE_1_TIERED_DEVELOPMENT_PLAN.md)

---

### Phase 2: Background Daemons & Computer Vision (12 Tiers)

**Goal:** Add automated data collection and video-based robot tracking on top of the Phase 1 foundation.

**Key Features:**
- Celery + Redis background task infrastructure
- YOLOv8 + DeepSORT video processing pipeline
- Real-time WebSocket dashboard updates
- Performance prediction & ML ranking models
- Automated report generation and distribution
- Field heatmaps and robot movement visualizations
- Mobile-responsive app improvements

📖 **Detailed Plan:** [`docs/PHASE_2_TIERED_DEVELOPMENT_PLAN.md`](docs/PHASE_2_TIERED_DEVELOPMENT_PLAN.md)  
🏗️ **Daemon Architecture:** [`docs/BACKGROUND_DAEMON_ARCHITECTURE.md`](docs/BACKGROUND_DAEMON_ARCHITECTURE.md)

---

### Phase 3: Advanced Ecosystem Expansion (12 Tiers)

> ⚠️ **DO NOT START PHASE 3 UNTIL PHASE 1 & 2 ARE COMPLETE**  
> Phase 3 is a future roadmap. Current focus is Phase 1 and Phase 2.

**Goal:** Expand ScoutFRC into a comprehensive FRC intelligence platform.

**Key Features:**
- Multi-event management and organization support
- AI Coach Assistant with strategy recommendations
- Community platform and knowledge sharing
- Live event streaming with AI commentary
- Enterprise features and white-label deployments
- Native iOS/Android mobile apps
- VR/AR field visualization
- Governance, compliance, and long-term sustainability

📖 **Detailed Plan:** [`docs/PHASE_3_TIERED_DEVELOPMENT_PLAN.md`](docs/PHASE_3_TIERED_DEVELOPMENT_PLAN.md)

---

### Phase Summary

| Phase | Focus | Tiers | Current Status |
|-------|-------|-------|----------------|
| **1** | Core MVP — Database, API, Dashboard, Analytics | 12 | 🎯 **Active Focus** |
| **2** | Background Daemons & Computer Vision | 12 | 🎯 **Active Focus** |
| **3** | Advanced Ecosystem Expansion | 12 | ⏸️ **Future Planning Only** |

## Tech Stack (Summary)

| Layer | Technology |
|---|---|
| CV Backend | Python 3.11 · YOLOv8 · DeepSORT · OpenCV · Celery |
| Database | PostgreSQL 16 · SQLAlchemy 2 · Alembic · Redis |
| API | FastAPI |
| Frontend | React 18 · TypeScript · Vite · TanStack Query · Recharts · Konva.js · Tailwind CSS |
| Infrastructure | Docker · GitHub Actions · AWS S3 / EC2 (GPU) |

## Documentation

| Document | Description |
|---|---|
| [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) | Full architecture, database schema, analytics design, phased roadmap, and risk assessment |
| [`docs/PHASE_1_TIERED_DEVELOPMENT_PLAN.md`](docs/PHASE_1_TIERED_DEVELOPMENT_PLAN.md) | Phase 1 — 12 tiers: Core MVP Foundation (database → deployment) |
| [`docs/PHASE_2_TIERED_DEVELOPMENT_PLAN.md`](docs/PHASE_2_TIERED_DEVELOPMENT_PLAN.md) | Phase 2 — 12 tiers: Background Daemons & Computer Vision |
| [`docs/PHASE_3_TIERED_DEVELOPMENT_PLAN.md`](docs/PHASE_3_TIERED_DEVELOPMENT_PLAN.md) | Phase 3 — 12 tiers: Advanced Ecosystem Expansion (future planning only) |
| [`docs/BACKGROUND_DAEMON_ARCHITECTURE.md`](docs/BACKGROUND_DAEMON_ARCHITECTURE.md) | Daemon system design — Celery, Redis, worker architecture |
| [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md) | Complete database schema reference — all models, relationships, indexes, migrations, sample queries, and security/scalability notes |

## License

See [LICENSE](LICENSE).
