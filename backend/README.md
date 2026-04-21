# ScouterFRC Backend - Phase 1, Tier 1

## Setup Instructions

### Prerequisites
- Python 3.10+
- PostgreSQL 13+ (or Docker)
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

**Option A: Using Docker (Recommended for Development)**
```bash
docker run -d \
  --name scouterfrc-db \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=scouterfrc \
  -p 5432:5432 \
  postgres:15
```

**Option B: Local PostgreSQL Installation**
```bash
# macOS with Homebrew
brew install postgresql
brew services start postgresql

# Create database
createdb scouterfrc

# Create user (optional)
createuser -P postgres
```

### 4. Run Database Migrations (After Step 5 is Complete)
```bash
cd backend
alembic upgrade head
```

### Project Structure
```
backend/
├── app/
│   ├── db/              # Database connection and session management
│   ├── models/          # SQLAlchemy ORM models
│   ├── core/            # Configuration and utilities
│   └── __init__.py
├── alembic/             # Database migrations
├── requirements.txt     # Python dependencies
├── .env                 # Local configuration (git-ignored)
├── .env.example         # Configuration template (committed)
└── README.md           # This file
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
