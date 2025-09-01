#!/bin/bash

# Veloxe Database Backup Script
# Usage: ./scripts/backup.sh [database_name]

set -e

# Configuration
BACKUP_DIR="./backups"
DB_NAME="${1:-veloxe}"
DB_USER="${POSTGRES_USER:-veloxe}"
DB_PASSWORD="${POSTGRES_PASSWORD}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_backup_$TIMESTAMP.sql"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

log "🗄️ Starting database backup..."

# Check if postgres container is running
if ! docker-compose -f docker-compose.prod.yml ps postgres | grep -q "Up"; then
    error "❌ PostgreSQL container is not running"
fi

# Check if database password is set
if [ -z "$DB_PASSWORD" ]; then
    error "❌ POSTGRES_PASSWORD environment variable is not set"
fi

# Create backup
log "💾 Creating backup of database '$DB_NAME'..."
if docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-password \
    --verbose \
    --clean \
    --if-exists \
    --create \
    --format=custom > "$BACKUP_FILE.dump" 2>/dev/null; then
    log "✅ Binary backup created: $BACKUP_FILE.dump"
else
    error "❌ Failed to create binary backup"
fi

# Also create SQL backup for easier inspection
if docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-password \
    --verbose \
    --clean \
    --if-exists \
    --create > "$BACKUP_FILE" 2>/dev/null; then
    log "✅ SQL backup created: $BACKUP_FILE"
else
    warn "⚠️ Failed to create SQL backup, but binary backup exists"
fi

# Compress backups
log "🗜️ Compressing backups..."
gzip "$BACKUP_FILE" 2>/dev/null || warn "⚠️ Failed to compress SQL backup"
gzip "$BACKUP_FILE.dump" 2>/dev/null || warn "⚠️ Failed to compress binary backup"

# Verify backup
COMPRESSED_SQL="$BACKUP_FILE.gz"
COMPRESSED_DUMP="$BACKUP_FILE.dump.gz"

if [ -f "$COMPRESSED_SQL" ] || [ -f "$COMPRESSED_DUMP" ]; then
    if [ -f "$COMPRESSED_SQL" ]; then
        SIZE_SQL=$(du -h "$COMPRESSED_SQL" | cut -f1)
        log "✅ SQL backup size: $SIZE_SQL"
    fi
    
    if [ -f "$COMPRESSED_DUMP" ]; then
        SIZE_DUMP=$(du -h "$COMPRESSED_DUMP" | cut -f1)
        log "✅ Binary backup size: $SIZE_DUMP"
    fi
else
    error "❌ No backup files were created successfully"
fi

# Clean up old backups
log "🧹 Cleaning up old backups (keeping last $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "${DB_NAME}_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "${DB_NAME}_backup_*.dump.gz" -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

# List recent backups
log "📋 Recent backups:"
ls -lah "$BACKUP_DIR"/${DB_NAME}_backup_* | tail -5 || true

log "🎉 Backup completed successfully!"
echo
echo -e "${GREEN}💾 Backup files created:${NC}"
[ -f "$COMPRESSED_SQL" ] && echo "   SQL: $COMPRESSED_SQL"
[ -f "$COMPRESSED_DUMP" ] && echo "   Binary: $COMPRESSED_DUMP"
echo
echo -e "${GREEN}💡 To restore from backup:${NC}"
echo "   SQL: gunzip -c $COMPRESSED_SQL | docker-compose -f docker-compose.prod.yml exec -T postgres psql -U $DB_USER"
echo "   Binary: gunzip -c $COMPRESSED_DUMP | docker-compose -f docker-compose.prod.yml exec -T postgres pg_restore -U $DB_USER -d $DB_NAME --clean --if-exists"