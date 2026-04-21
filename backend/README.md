# ScouterFRC Backend - Phase 1, Tier 1

## Docker Setup (Recommended)

The fastest way to get a local PostgreSQL database running is with Docker.

### Quick Start

```bash
# Start database
docker compose up -d

# Or use the helper script
chmod +x backend/docker-helpers.sh
./docker-helpers.sh start
```

See the detailed guides for full instructions:

- [DOCKER_SETUP.md](DOCKER_SETUP.md) — Complete Docker setup guide with troubleshooting
- [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) — Quick reference card for daily use

### Docker Files

| File | Description |
|------|-------------|
| [docker-compose.yml](docker-compose.yml) | Docker Compose configuration for PostgreSQL 15 |
| [docker-helpers.sh](docker-helpers.sh) | Helper script: `start`, `stop`, `status`, `logs`, `backup`, `reset`, `connect`, `test` |
| [test_docker_connection.py](test_docker_connection.py) | Python script to verify the database connection |

### Helper Script Commands

```bash
./docker-helpers.sh start    # Start database (create container if needed)
./docker-helpers.sh stop     # Stop database
./docker-helpers.sh restart  # Restart database
./docker-helpers.sh status   # Show status info
./docker-helpers.sh logs     # View logs (add -f to follow)
./docker-helpers.sh connect  # Open psql session
./docker-helpers.sh backup   # Backup to scouterfrc-backup.sql
./docker-helpers.sh reset    # Reset database (deletes all data!)
./docker-helpers.sh test     # Test Python connection
```

---

## Setup Instructions

### Prerequisites
- Python 3.10+
- Docker (for PostgreSQL) — see [DOCKER_SETUP.md](DOCKER_SETUP.md)
- pip or conda

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env with your database credentials
# Update DATABASE_URL with your PostgreSQL connection string
```

### 3. PostgreSQL Setup

**Option A: Using Docker Compose (Recommended)**
```bash
docker compose up -d
```

**Option B: Using docker run directly**
```bash
docker run -d \
  --name scouterfrc-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=scouterfrc \
  -v scouterfrc-data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:15
```

**Option C: Local PostgreSQL Installation**
```bash
# macOS with Homebrew
brew install postgresql
brew services start postgresql

# Create database
createdb scouterfrc

# Create user (optional)
createuser -P postgres
```

### 4. Test Database Connection

```bash
python test_docker_connection.py
```

### 5. Run Database Migrations (After Alembic Setup is Complete)
```bash
cd backend
alembic upgrade head
```

### Project Structure
```
backend/
├── app/
│   ├── db/                        # Database connection and session management
│   ├── models/                    # SQLAlchemy ORM models
│   ├── core/                      # Configuration and utilities
│   └── __init__.py
├── alembic/                       # Database migrations
├── docker-compose.yml             # Docker Compose configuration
├── docker-helpers.sh              # Docker helper script
├── test_docker_connection.py      # Python connection test
├── requirements.txt               # Python dependencies
├── .env                           # Local configuration (git-ignored)
├── .env.example                   # Configuration template (committed)
├── DOCKER_SETUP.md                # Complete Docker setup guide
├── DOCKER_QUICKSTART.md           # Quick reference card
└── README.md                      # This file
```

### Phase 1, Tier 1 Progress
- [x] Step 1: Project Structure & Environment Setup
- [ ] Step 2: SQLAlchemy Database Connection
- [ ] Step 3: Install Dependencies & Test
- [ ] Step 4: PostgreSQL Setup
- [ ] Step 5: Alembic Initialization
- [ ] Step 6: Create ORM Models
- [ ] Step 7: Define Relationships & Constraints
- [ ] Step 8: Create Initial Migration
- [ ] Step 9: Session Management
- [ ] Step 10: Testing & Documentation

### Next Steps
After completing Step 1, proceed to Step 2: SQLAlchemy Database Connection setup.
