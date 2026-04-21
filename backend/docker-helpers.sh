#!/bin/bash
# ScouterFRC Docker Helper Script
# Usage: ./docker-helpers.sh <command>

CONTAINER_NAME="scouterfrc-db"
VOLUME_NAME="scouterfrc-data"
IMAGE="postgres:15"
DB_USER="postgres"
DB_PASSWORD="password"
DB_NAME="scouterfrc"
HOST_PORT="5432"

# ─────────────────────────────────────────────────────────────────────────────
# Function: show_help
# ─────────────────────────────────────────────────────────────────────────────
show_help() {
  echo ""
  echo "ScouterFRC Docker Helper"
  echo "========================"
  echo ""
  echo "Usage: $0 <command>"
  echo ""
  echo "Commands:"
  echo "  start    Start the PostgreSQL container (create if needed)"
  echo "  stop     Stop the running container"
  echo "  restart  Restart the container"
  echo "  status   Show container, volume, and connection status"
  echo "  logs     View container logs (use 'logs -f' to follow)"
  echo "  connect  Open interactive psql session"
  echo "  backup   Backup database to scouterfrc-backup.sql"
  echo "  reset    Drop and recreate volume (DELETES ALL DATA)"
  echo "  test     Test Python database connection"
  echo ""
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: docker_start
# Start existing container or create a new one if it doesn't exist.
# ─────────────────────────────────────────────────────────────────────────────
docker_start() {
  echo "▶ Starting ScouterFRC PostgreSQL container..."

  # Check if container exists (running or stopped)
  if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    # Container exists — just start it
    docker start "${CONTAINER_NAME}"
  else
    # Container doesn't exist — create volume if needed, then create container
    if ! docker volume ls --format '{{.Name}}' | grep -q "^${VOLUME_NAME}$"; then
      echo "  Creating volume ${VOLUME_NAME}..."
      docker volume create "${VOLUME_NAME}"
    fi

    echo "  Creating new container ${CONTAINER_NAME}..."
    docker run -d \
      --name "${CONTAINER_NAME}" \
      -e POSTGRES_USER="${DB_USER}" \
      -e POSTGRES_PASSWORD="${DB_PASSWORD}" \
      -e POSTGRES_DB="${DB_NAME}" \
      -v "${VOLUME_NAME}:/var/lib/postgresql/data" \
      -p "${HOST_PORT}:5432" \
      "${IMAGE}"
  fi

  # Wait briefly for PostgreSQL to become ready
  echo "  Waiting for PostgreSQL to be ready..."
  local retries=10
  until docker exec "${CONTAINER_NAME}" pg_isready -U "${DB_USER}" -q 2>/dev/null; do
    retries=$((retries - 1))
    if [ "${retries}" -le 0 ]; then
      echo "✗ Timed out waiting for PostgreSQL to start."
      echo "  Run 'docker logs ${CONTAINER_NAME}' to see what went wrong."
      exit 1
    fi
    sleep 1
  done

  echo "✔ Container ${CONTAINER_NAME} is running."
  echo ""
  echo "Connection info:"
  echo "  Host:     localhost"
  echo "  Port:     ${HOST_PORT}"
  echo "  Database: ${DB_NAME}"
  echo "  User:     ${DB_USER}"
  echo "  URL:      postgresql://${DB_USER}:${DB_PASSWORD}@localhost:${HOST_PORT}/${DB_NAME}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: docker_stop
# Stop the running container.
# ─────────────────────────────────────────────────────────────────────────────
docker_stop() {
  echo "■ Stopping ScouterFRC PostgreSQL container..."

  if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    docker stop "${CONTAINER_NAME}"
    echo "✔ Container ${CONTAINER_NAME} stopped."
  else
    echo "  Container ${CONTAINER_NAME} is not running."
  fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: docker_restart
# Stop then start the container.
# ─────────────────────────────────────────────────────────────────────────────
docker_restart() {
  echo "↺ Restarting ScouterFRC PostgreSQL container..."
  docker_stop
  docker_start
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: docker_logs
# Show container logs. Pass -f as second argument to follow.
# ─────────────────────────────────────────────────────────────────────────────
docker_logs() {
  local follow="${2:-}"
  if [ "${follow}" = "-f" ]; then
    echo "Following logs for ${CONTAINER_NAME} (Ctrl+C to stop)..."
    docker logs -f "${CONTAINER_NAME}"
  else
    docker logs --tail 100 "${CONTAINER_NAME}"
  fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: docker_status
# Show container status, volume status, port status, and connection info.
# ─────────────────────────────────────────────────────────────────────────────
docker_status() {
  echo "ScouterFRC Docker Status"
  echo "========================"
  echo ""

  # Container status
  echo "Container:"
  if docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -q "^${CONTAINER_NAME}"; then
    docker ps --format '  Name: {{.Names}}  Status: {{.Status}}  Ports: {{.Ports}}' \
      | grep "${CONTAINER_NAME}"
  elif docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "  ${CONTAINER_NAME} — exists but is STOPPED"
  else
    echo "  ${CONTAINER_NAME} — does NOT exist"
  fi
  echo ""

  # Volume status
  echo "Volume:"
  if docker volume ls --format '{{.Name}}' | grep -q "^${VOLUME_NAME}$"; then
    echo "  ${VOLUME_NAME} — exists"
  else
    echo "  ${VOLUME_NAME} — does NOT exist"
  fi
  echo ""

  # Port status
  echo "Port ${HOST_PORT}:"
  if command -v lsof >/dev/null 2>&1; then
    if lsof -i ":${HOST_PORT}" >/dev/null 2>&1; then
      echo "  In use by: $(lsof -i ":${HOST_PORT}" | awk 'NR==2{print $1}')"
    else
      echo "  Available"
    fi
  fi
  echo ""

  # Connection info
  echo "Connection:"
  echo "  URL: postgresql://${DB_USER}:${DB_PASSWORD}@localhost:${HOST_PORT}/${DB_NAME}"
  echo ""

  # PostgreSQL readiness
  echo "PostgreSQL readiness:"
  if docker exec "${CONTAINER_NAME}" pg_isready -U "${DB_USER}" 2>/dev/null; then
    echo "  ✔ Accepting connections"
  else
    echo "  ✗ Not ready (container may be stopped)"
  fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: docker_connect
# Connect to PostgreSQL inside the container via psql.
# ─────────────────────────────────────────────────────────────────────────────
docker_connect() {
  echo "Connecting to ${DB_NAME} as ${DB_USER}..."
  echo "(Type \\q to exit)"
  echo ""
  docker exec -it "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: docker_backup
# Create a SQL dump of the database and save to scouterfrc-backup.sql.
# ─────────────────────────────────────────────────────────────────────────────
docker_backup() {
  local backup_file="scouterfrc-backup.sql"
  echo "Backing up database ${DB_NAME} to ${backup_file}..."

  if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "✗ Container ${CONTAINER_NAME} is not running. Start it first."
    exit 1
  fi

  docker exec -t "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" "${DB_NAME}" > "${backup_file}"
  echo "✔ Backup saved to ${backup_file}"
  echo "  Size: $(wc -c < "${backup_file}") bytes"
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: docker_reset
# Drop volume, create fresh volume, and start a new container.
# WARNING: All database data will be permanently deleted.
# ─────────────────────────────────────────────────────────────────────────────
docker_reset() {
  echo ""
  echo "⚠  WARNING: This will permanently delete all data in ${VOLUME_NAME}."
  echo "   Your code will not be affected."
  echo ""
  printf "   Type 'yes' to confirm reset: "
  read -r confirmation
  if [ "${confirmation}" != "yes" ]; then
    echo "   Reset cancelled."
    return
  fi

  echo ""
  echo "Resetting ScouterFRC database..."

  # Stop container if running
  if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "  Stopping container..."
    docker stop "${CONTAINER_NAME}"
  fi

  # Remove container if it exists
  if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "  Removing container..."
    docker rm "${CONTAINER_NAME}"
  fi

  # Delete volume
  if docker volume ls --format '{{.Name}}' | grep -q "^${VOLUME_NAME}$"; then
    echo "  Deleting volume ${VOLUME_NAME}..."
    docker volume rm "${VOLUME_NAME}"
  fi

  # Recreate volume and start fresh
  echo "  Creating fresh volume..."
  docker volume create "${VOLUME_NAME}"

  echo "  Starting fresh container..."
  docker_start

  echo ""
  echo "✔ Database reset complete. Run 'alembic upgrade head' to recreate tables."
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: docker_test_python
# Run the Python connection test script.
# ─────────────────────────────────────────────────────────────────────────────
docker_test_python() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local test_script="${script_dir}/test_docker_connection.py"

  if [ ! -f "${test_script}" ]; then
    echo "✗ Test script not found: ${test_script}"
    exit 1
  fi

  echo "Running Python connection test..."
  python "${test_script}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Main menu
# ─────────────────────────────────────────────────────────────────────────────
case "${1:-}" in
  start)   docker_start ;;
  stop)    docker_stop ;;
  restart) docker_restart ;;
  logs)    docker_logs "$@" ;;
  reset)   docker_reset ;;
  status)  docker_status ;;
  connect) docker_connect ;;
  backup)  docker_backup ;;
  test)    docker_test_python ;;
  *)       show_help ;;
esac
