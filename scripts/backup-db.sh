#!/bin/bash

# Database backup script for Reva
# This script backs up both the main (reva) and auth (reva_auth) databases
# Run via cron: 0 3 * * * /path/to/backup-db.sh

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/var/backups/reva}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
COMPOSE_FILE="${COMPOSE_FILE:-/opt/reva/docker-compose.prod.yml}"

# Database names
DATABASES=("reva" "reva_auth")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Find the postgres container
# Coolify uses generated names, so we search by service label or image
POSTGRES_CONTAINER=$(docker ps --filter "ancestor=pgvector/pgvector:pg16" --format "{{.Names}}" | head -n 1)

if [ -z "$POSTGRES_CONTAINER" ]; then
    # Fallback: try to find by label if Coolify adds service labels
    POSTGRES_CONTAINER=$(docker ps --filter "label=com.docker.compose.service=postgres" --format "{{.Names}}" | head -n 1)
fi

if [ -z "$POSTGRES_CONTAINER" ]; then
    error "Could not find postgres container. Is it running?"
    exit 1
fi

log "Found postgres container: $POSTGRES_CONTAINER"

# Backup each database
for DB in "${DATABASES[@]}"; do
    log "Backing up database: $DB"

    BACKUP_FILE="$BACKUP_DIR/${DB}_${TIMESTAMP}.dump"

    # Perform backup using custom format (compressed)
    if docker exec "$POSTGRES_CONTAINER" pg_dump -U postgres -Fc -d "$DB" > "$BACKUP_FILE"; then
        # Get file size for logging
        SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        log "✓ Backup completed: $BACKUP_FILE ($SIZE)"
    else
        error "Failed to backup database: $DB"
        # Don't exit - try to backup other databases
        continue
    fi
done

# Cleanup old backups (retention policy)
log "Cleaning up backups older than $RETENTION_DAYS days..."

DELETED_COUNT=0
while IFS= read -r -d '' file; do
    rm -f "$file"
    ((DELETED_COUNT++))
done < <(find "$BACKUP_DIR" -name "*.dump" -type f -mtime +$RETENTION_DAYS -print0)

if [ $DELETED_COUNT -gt 0 ]; then
    log "✓ Deleted $DELETED_COUNT old backup(s)"
else
    log "No old backups to delete"
fi

# Summary
TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "*.dump" -type f | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

log "════════════════════════════════════════"
log "Backup Summary"
log "════════════════════════════════════════"
log "Total backups: $TOTAL_BACKUPS"
log "Total size: $TOTAL_SIZE"
log "Retention: $RETENTION_DAYS days"
log "════════════════════════════════════════"

exit 0
