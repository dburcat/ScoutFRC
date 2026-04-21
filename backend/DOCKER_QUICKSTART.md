# ScouterFRC Docker Quick Start

Quick reference for running PostgreSQL 15 with Docker for local development.

---

## First Time Setup

```bash
# Step 1: Download PostgreSQL 15 image
docker pull postgres:15

# Step 2: Create persistent volume
docker volume create scouterfrc-data

# Step 3: Start container
docker run -d \
  --name scouterfrc-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=scouterfrc \
  -v scouterfrc-data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:15

# Step 4: Verify it's running
docker ps
```

---

## Daily Workflow

```bash
# Morning: Start the database
docker start scouterfrc-db

# Throughout the day: Code normally

# Evening: Stop the database
docker stop scouterfrc-db
```

---

## Alternative: Docker Compose (Easier)

```bash
# Start database
docker compose up -d

# Stop database
docker compose down

# View logs
docker compose logs -f

# Reset (deletes all data)
docker compose down -v
```

---

## Helper Script

```bash
# Make executable (first time only)
chmod +x backend/docker-helpers.sh

# Common commands
./docker-helpers.sh start    # Start database
./docker-helpers.sh stop     # Stop database
./docker-helpers.sh restart  # Restart database
./docker-helpers.sh status   # Show status
./docker-helpers.sh logs     # View logs
./docker-helpers.sh connect  # Open psql session
./docker-helpers.sh backup   # Backup database
./docker-helpers.sh reset    # Reset (deletes data!)
./docker-helpers.sh test     # Test Python connection
```

---

## Connection Info

| Setting | Value |
|---------|-------|
| Host | `localhost` |
| Port | `5432` |
| Database | `scouterfrc` |
| User | `postgres` |
| Password | `password` |
| URL | `postgresql://postgres:password@localhost:5432/scouterfrc` |

---

## Quick Commands

```bash
# Check if container is running
docker ps

# View logs
docker logs scouterfrc-db

# Open psql shell
docker exec -it scouterfrc-db psql -U postgres -d scouterfrc

# Test connection
python backend/test_docker_connection.py
```

---

## Reset Database

⚠️ **Warning: Deletes all data!**

```bash
# Backup first (recommended)
docker exec -t scouterfrc-db pg_dump -U postgres scouterfrc > scouterfrc-backup.sql

# Reset
docker stop scouterfrc-db
docker rm scouterfrc-db
docker volume rm scouterfrc-data
docker volume create scouterfrc-data
docker run -d --name scouterfrc-db \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=scouterfrc \
  -v scouterfrc-data:/var/lib/postgresql/data \
  -p 5432:5432 postgres:15

# Restore schema
cd backend && alembic upgrade head
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 5432 in use | `lsof -i :5432` — stop whatever is using it |
| Container won't start | `docker logs scouterfrc-db` — check for errors |
| Connection refused | `docker ps` — make sure container is running |
| Data disappeared | You forgot `-v scouterfrc-data:...` on first run |

See [DOCKER_SETUP.md](DOCKER_SETUP.md) for detailed troubleshooting.
