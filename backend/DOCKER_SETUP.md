# ScouterFRC Docker Setup Guide

Complete guide for running PostgreSQL 15 in Docker for local ScouterFRC development.

---

## A. Prerequisites

### Install Docker

- **macOS:** [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
- **Windows:** [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
- **Linux:** [Docker Engine for Linux](https://docs.docker.com/engine/install/)

### Verify Installation

```bash
docker --version
# Expected: Docker version 24.x.x or later

docker compose version
# Expected: Docker Compose version v2.x.x or later
```

---

## B. Initial Setup (One-Time)

Run these commands once when setting up your development environment for the first time.

### Step 1: Pull PostgreSQL 15 Image

```bash
docker pull postgres:15
```

This downloads the official PostgreSQL 15 image from Docker Hub (~150 MB). Docker caches
it locally so you won't need to download it again.

### Step 2: Create Docker Volume for Data Persistence

```bash
docker volume create scouterfrc-data
```

**What is a Docker volume?**
A Docker volume is a named storage location managed by Docker, stored outside the
container filesystem. This means your database data persists even if the container is
stopped, removed, or updated. Without a volume, all data would be lost when the
container stops.

### Docker Concepts Explained

| Concept | Description |
|---------|-------------|
| **Image** | A read-only template used to create containers (like a blueprint) |
| **Container** | A running instance of an image (like a building from a blueprint) |
| **Volume** | Persistent storage that survives container restarts and deletions |
| **Port mapping** | Connects a host port to a container port (`host:container`) |

---

## C. Starting PostgreSQL Container

### Full `docker run` Command

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

### Flags Explained

| Flag | Value | Description |
|------|-------|-------------|
| `-d` | — | Run in detached (background) mode |
| `--name` | `scouterfrc-db` | Name the container for easy reference |
| `-e POSTGRES_USER` | `postgres` | PostgreSQL superuser username |
| `-e POSTGRES_PASSWORD` | `password` | PostgreSQL superuser password |
| `-e POSTGRES_DB` | `scouterfrc` | Name of the default database to create |
| `-v` | `scouterfrc-data:/var/lib/postgresql/data` | Mount the named volume to the PostgreSQL data directory |
| `-p` | `5432:5432` | Map host port 5432 to container port 5432 |
| `postgres:15` | — | The Docker image to use |

### Environment Variables

| Variable | Value | Purpose |
|----------|-------|---------|
| `POSTGRES_USER` | `postgres` | Superuser account created on first run |
| `POSTGRES_PASSWORD` | `password` | Password for the superuser (change for production!) |
| `POSTGRES_DB` | `scouterfrc` | Database created automatically on first run |

### Port Mapping (5432:5432)

The format is `host_port:container_port`. Port 5432 is PostgreSQL's default port.
Your application connects to `localhost:5432`, which Docker forwards into the container.

### Volume Mounting

`-v scouterfrc-data:/var/lib/postgresql/data` attaches the `scouterfrc-data` Docker
volume to the container's data directory. PostgreSQL stores all database files there.

---

## D. Verification Steps

### 1. Verify Container is Running

```bash
docker ps
```

Expected output:
```
CONTAINER ID   IMAGE         COMMAND                  CREATED        STATUS        PORTS                    NAMES
abc123def456   postgres:15   "docker-entrypoint.s…"   5 seconds ago  Up 4 seconds  0.0.0.0:5432->5432/tcp   scouterfrc-db
```

### 2. Test Connection from Command Line

```bash
docker exec -it scouterfrc-db psql -U postgres -d scouterfrc -c "SELECT version();"
```

Expected output:
```
                                                 version
---------------------------------------------------------------------------------------------------------
 PostgreSQL 15.x on x86_64-pc-linux-gnu, compiled by gcc (Debian ...), 64-bit
(1 row)
```

### 3. Test Connection from Python

```bash
cd backend
python test_docker_connection.py
```

Expected output:
```
✅ Connected to PostgreSQL successfully!
   Server version: PostgreSQL 15.x ...
   Database: scouterfrc
   User: postgres
```

---

## E. Daily Workflow

### Start Container Before Work

```bash
# If container already exists (after initial setup)
docker start scouterfrc-db

# Verify it started
docker ps
```

### Stop Container After Work

```bash
docker stop scouterfrc-db
```

### Check Container Status

```bash
docker ps -a
# Shows all containers including stopped ones
```

### Check Logs If Issues

```bash
docker logs scouterfrc-db
# Or follow logs in real time:
docker logs -f scouterfrc-db
```

---

## F. Useful Docker Commands

### List Containers

```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a
```

### View Container Logs

```bash
# Show last 50 lines
docker logs --tail 50 scouterfrc-db

# Follow logs in real time (Ctrl+C to stop)
docker logs -f scouterfrc-db
```

### Container Control

```bash
# Stop container
docker stop scouterfrc-db

# Start stopped container
docker start scouterfrc-db

# Restart container
docker restart scouterfrc-db

# Remove container (data is safe in volume)
docker rm scouterfrc-db
```

### Execute Commands in Container

```bash
# Open interactive psql session
docker exec -it scouterfrc-db psql -U postgres -d scouterfrc

# Run a single SQL command
docker exec -it scouterfrc-db psql -U postgres -d scouterfrc -c "SELECT * FROM pg_tables;"

# Open a bash shell inside the container
docker exec -it scouterfrc-db bash
```

---

## G. Troubleshooting

### Port 5432 Already in Use

**Error:** `Error starting userland proxy: listen tcp4 0.0.0.0:5432: bind: address already in use`

**Solution:**

```bash
# Check what is using port 5432
# macOS/Linux:
lsof -i :5432

# Windows:
netstat -ano | findstr :5432

# If it's a local PostgreSQL installation:
# macOS: brew services stop postgresql
# Linux: sudo systemctl stop postgresql
# Windows: net stop postgresql

# Or use a different host port (e.g. 5433):
docker run -d --name scouterfrc-db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=scouterfrc -v scouterfrc-data:/var/lib/postgresql/data \
  -p 5433:5432 postgres:15
# Then update DB_PORT=5433 in your .env file
```

### Container Won't Start

```bash
# Check container logs
docker logs scouterfrc-db

# Check if container exists (might be stopped)
docker ps -a | grep scouterfrc-db

# Remove and recreate if needed (data is safe in volume)
docker rm scouterfrc-db
docker run -d --name scouterfrc-db ... (full command from section C)
```

### Connection Refused

**Error:** `could not connect to server: Connection refused`

**Checklist:**
1. Is the container running? → `docker ps`
2. Did you use the right port? → Default is 5432
3. Did you use the right hostname? → Use `localhost` (not `127.0.0.1` for some tools)
4. Is your `.env` file configured correctly? → Check `DATABASE_URL`

```bash
# Test the connection directly
docker exec -it scouterfrc-db pg_isready -U postgres
# Expected: /var/run/postgresql:5432 - accepting connections
```

### Data Persistence Issues

If your data disappeared after restarting:
- The container was run **without** the `-v scouterfrc-data:...` flag
- Solution: Stop and remove the container, then run it again with the volume flag

```bash
# Verify volume exists
docker volume ls | grep scouterfrc-data

# Inspect volume details
docker volume inspect scouterfrc-data
```

---

## H. Reset / Clean Database

### Reset Database (Keep Your Code)

⚠️ **Warning: This permanently deletes all database data.**

```bash
# 1. Stop the container
docker stop scouterfrc-db

# 2. Remove the container
docker rm scouterfrc-db

# 3. Delete the volume (THIS DELETES ALL DATA)
docker volume rm scouterfrc-data

# 4. Create a fresh volume
docker volume create scouterfrc-data

# 5. Start fresh container
docker run -d \
  --name scouterfrc-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=scouterfrc \
  -v scouterfrc-data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:15

# 6. Run migrations to restore schema
cd backend
alembic upgrade head
```

### Backup Before Reset

```bash
# Create a SQL dump before resetting
docker exec -t scouterfrc-db pg_dump -U postgres scouterfrc > scouterfrc-backup.sql

# After reset, restore from backup
cat scouterfrc-backup.sql | docker exec -i scouterfrc-db psql -U postgres -d scouterfrc
```

### Using docker-compose (Easier Reset)

```bash
# Stop and remove containers + volumes
docker compose down -v

# Start fresh
docker compose up -d

# Run migrations
alembic upgrade head
```

---

## See Also

- [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) — Quick reference card
- [docker-compose.yml](docker-compose.yml) — Docker Compose alternative
- [docker-helpers.sh](docker-helpers.sh) — Helper script for common tasks
- [test_docker_connection.py](test_docker_connection.py) — Test database connectivity
