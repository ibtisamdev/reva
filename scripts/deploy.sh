#!/bin/bash
# Reva production deploy script
# Usage:
#   bash scripts/deploy.sh              # Deploy latest from main
#   bash scripts/deploy.sh --rollback   # Rollback to previous version
#   bash scripts/deploy.sh --migrate    # Deploy and run migrations
set -euo pipefail

# --- Configuration ---
DEPLOY_DIR="/opt/reva"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"
HEALTH_TIMEOUT=60
HEALTH_INTERVAL=2

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()   { echo -e "${GREEN}[deploy]${NC} $1"; }
warn()  { echo -e "${YELLOW}[deploy]${NC} $1"; }
error() { echo -e "${RED}[deploy]${NC} $1" >&2; }

# --- Parse flags ---
ROLLBACK=false
MIGRATE=false
for arg in "$@"; do
  case "$arg" in
    --rollback) ROLLBACK=true ;;
    --migrate)  MIGRATE=true ;;
    *)          error "Unknown flag: $arg"; exit 1 ;;
  esac
done

cd "$DEPLOY_DIR"

# --- Helper: wait for health ---
wait_for_health() {
  local url=$1
  local name=$2
  local max_attempts=$(( HEALTH_TIMEOUT / HEALTH_INTERVAL ))
  local attempt=0

  log "Waiting for $name to be healthy..."
  while [ $attempt -lt $max_attempts ]; do
    if curl -sf "$url" > /dev/null 2>&1; then
      log "$name is healthy"
      return 0
    fi
    sleep "$HEALTH_INTERVAL"
    attempt=$((attempt + 1))
  done
  error "$name failed health check after ${HEALTH_TIMEOUT}s"
  return 1
}

# --- Helper: compose command ---
dc() {
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"
}

# --- Pre-deploy checks ---
log "Running pre-deploy checks..."

if [ ! -f "$ENV_FILE" ]; then
  error "$ENV_FILE not found at $DEPLOY_DIR"
  exit 1
fi

if ! command -v docker &> /dev/null; then
  error "docker not found"
  exit 1
fi

if ! docker compose version &> /dev/null; then
  error "docker compose not found"
  exit 1
fi

# --- Rollback ---
if [ "$ROLLBACK" = true ]; then
  if [ ! -f .last-deploy-tag ]; then
    error "No previous version found (.last-deploy-tag missing)"
    exit 1
  fi

  PREV_TAG=$(cat .last-deploy-tag)
  log "Rolling back to: $PREV_TAG"

  export IMAGE_TAG="$PREV_TAG"
  dc pull
  dc up -d --no-deps api
  wait_for_health "http://localhost:8000/api/v1/health/live" "API"
  dc up -d --no-deps worker
  dc up -d --no-deps web
  wait_for_health "http://localhost:3000/api/health" "Web"

  echo "$PREV_TAG" > .current-deploy-tag
  log "Rollback complete: $PREV_TAG"
  exit 0
fi

# --- Deploy ---
# Save current version for rollback
cat .current-deploy-tag 2>/dev/null > .last-deploy-tag || true

# Pull latest code (for compose file, scripts, migrations)
log "Pulling latest code..."
git pull origin main

# Determine image tag
IMAGE_TAG=$(git rev-parse HEAD)
export IMAGE_TAG
log "Deploying version: $IMAGE_TAG"
echo "$IMAGE_TAG" > .current-deploy-tag

# Pull pre-built images
log "Pulling images..."
dc pull

# Sequential service updates (near-zero-downtime)
log "Updating API..."
dc up -d --no-deps api
wait_for_health "http://localhost:8000/api/v1/health/live" "API" || {
  error "API health check failed, rolling back..."
  if [ -f .last-deploy-tag ]; then
    export IMAGE_TAG=$(cat .last-deploy-tag)
    dc pull && dc up -d
    echo "$IMAGE_TAG" > .current-deploy-tag
    warn "Rolled back to: $IMAGE_TAG"
  fi
  exit 1
}

log "Updating worker..."
dc up -d --no-deps worker

log "Updating web..."
dc up -d --no-deps web
wait_for_health "http://localhost:3000/api/health" "Web" || {
  error "Web health check failed, rolling back..."
  if [ -f .last-deploy-tag ]; then
    export IMAGE_TAG=$(cat .last-deploy-tag)
    dc pull && dc up -d
    echo "$IMAGE_TAG" > .current-deploy-tag
    warn "Rolled back to: $IMAGE_TAG"
  fi
  exit 1
}

# Run migrations if requested
if [ "$MIGRATE" = true ]; then
  log "Running database migrations..."
  API_CONTAINER=$(docker ps -qf "name=api" | head -n 1)
  if [ -z "$API_CONTAINER" ]; then
    error "Could not find API container for migrations"
    exit 1
  fi
  docker exec "$API_CONTAINER" alembic upgrade head
  log "Migrations complete"
fi

# Cleanup
docker image prune -f > /dev/null 2>&1

log "════════════════════════════════════════"
log "Deploy successful"
log "Version: $IMAGE_TAG"
log "════════════════════════════════════════"
log "Verify: docker compose -f $COMPOSE_FILE ps"
