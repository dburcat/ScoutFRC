# ScoutFRC

**ScoutFRC** is an automated video-based analytics system for the FIRST Robotics Competition (FRC). It replaces manual student scouting by analysing official match videos with computer vision — providing alliance captains with objective, data-driven robot performance profiles for elimination picks.

## Key Features (Planned)

- 🤖 **YOLOv8 + DeepSORT** — real-time robot detection and multi-object tracking
- 🗺️ **Perspective Transform** — maps angled camera footage to top-down field coordinates (x, y)
- 📊 **Analytics Engine** — scoring breakdowns, cycle times, and field heatmaps per robot
- 🤝 **Alliance Builder** — drag-and-drop tool with projected scores and coverage-gap analysis
- 🗄️ **PostgreSQL** relational schema across 7 entities (EVENT → TEAM → MATCH → ROBOT_PERFORMANCE → …)

## Documentation

| Document | Description |
|---|---|
| [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) | Full architecture, database schema, analytics design, phased roadmap, and risk assessment |

## Tech Stack (Summary)

| Layer | Technology |
|---|---|
| CV Backend | Python 3.11 · YOLOv8 · DeepSORT · OpenCV · Celery |
| Database | PostgreSQL 16 · SQLAlchemy 2 · Alembic · Redis |
| API | FastAPI |
| Frontend | React 18 · TypeScript · Vite · TanStack Query · Recharts · Konva.js · Tailwind CSS |
| Infrastructure | Docker · GitHub Actions · AWS S3 / EC2 (GPU) |

## Development Phases

| Phase | Focus | Goal |
|---|---|---|
| 1 — MVP | Detection & Tracking | Robot (x, y, t) position records from match video |
| 2 — Analytics | Scoring & Cycles | Phase breakdowns, cycle times, alliance fit engine |
| 3 — UX/UI | Dashboard | Event Dashboard → Team List → Robot Profile → Alliance Builder |

See [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) for the full implementation plan including the database schema, system architecture, and risk assessment.

## License

See [LICENSE](LICENSE).
