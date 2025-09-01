#!/bin/bash

# Veloxe Database Restore Script
# Usage: ./scripts/restore.sh <backup_file> [database_name]

set -e

# Configuration
BACKUP_FILE="$1"
DB_NAME="${2:-veloxe}"
DB_USER="${POSTGRES_USER:-veloxe}"
DB_PASSWORD="${POSTGRES_PASSWORD}"

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

# Check arguments
if [ -z "$BACKUP_FILE" ]; then
    error "❌ Please specify backup file to restore from"
fi

if [ ! -f "$BACKUP_FILE" ]; then
    error "❌ Backup file not found: $BACKUP_FILE"
fi

# Check if postgres container is running
if ! docker-compose -f docker-compose.prod.yml ps postgres | grep -q "Up"; then
    error "❌ PostgreSQL container is not running"
fi

# Check if database password is set
if [ -z "$DB_PASSWORD" ]; then
    error "❌ POSTGRES_PASSWORD environment variable is not set"
fi

log "🔄 Starting database restore..."
log "📁 Backup file: $BACKUP_FILE"
log "🗄️ Target database: $DB_NAME"

# Create confirmation prompt
echo
warn "⚠️ This will COMPLETELY REPLACE the existing database!"
warn "⚠️ All current data will be LOST!"
echo
read -p "Are you sure you want to continue? Type 'YES' to confirm: " -r
if [ "$REPLY" != "YES" ]; then
    log "❌ Restore cancelled by user"
    exit 1
fi

# Stop bot service to prevent new connections
log "🛑 Stopping bot service..."
docker-compose -f docker-compose.prod.yml stop bot admin-api || true

# Create a backup of current database before restore
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PRE_RESTORE_BACKUP="./backups/pre_restore_backup_$TIMESTAMP.sql.gz"

log "💾 Creating backup of current database before restore..."
if ./scripts/backup.sh "$DB_NAME"; then
    log "✅ Pre-restore backup created"
else
    warn "⚠️ Failed to create pre-restore backup, continuing anyway..."
fi

# Determine restore method based on file extension
if [[ "$BACKUP_FILE" == *.dump.gz ]]; then
    # Binary dump restore
    log "🔄 Restoring from binary dump..."
    gunzip -c "$BACKUP_FILE" | docker-compose -f docker-compose.prod.yml exec -T postgres pg_restore \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --clean \
        --if-exists \
        --verbose \
        --no-owner \
        --no-privileges
elif [[ "$BACKUP_FILE" == *.sql.gz ]]; then
    # SQL dump restore
    log "🔄 Restoring from SQL dump..."
    gunzip -c "$BACKUP_FILE" | docker-compose -f docker-compose.prod.yml exec -T postgres psql -U "$DB_USER" -v ON_ERROR_STOP=1
elif [[ "$BACKUP_FILE" == *.dump ]]; then
    # Uncompressed binary dump
    log "🔄 Restoring from uncompressed binary dump..."
    docker-compose -f docker-compose.prod.yml exec -T postgres pg_restore \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --clean \
        --if-exists \
        --verbose \
        --no-owner \
        --no-privileges < "$BACKUP_FILE"
elif [[ "$BACKUP_FILE" == *.sql ]]; then
    # Uncompressed SQL dump
    log "🔄 Restoring from uncompressed SQL dump..."
    docker-compose -f docker-compose.prod.yml exec -T postgres psql -U "$DB_USER" -v ON_ERROR_STOP=1 < "$BACKUP_FILE"
else
    error "❌ Unsupported backup file format. Supported: .sql, .sql.gz, .dump, .dump.gz"
fi

# Run migrations to ensure database is up to date
log "🔄 Running database migrations..."
docker-compose -f docker-compose.prod.yml run --rm bot alembic upgrade head

# Restart services
log "🚀 Starting services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be ready
log "⏳ Waiting for services to be ready..."
sleep 15

# Health check
log "🏥 Performing health check..."
if docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
    log "✅ Database is ready"
else
    error "❌ Database health check failed"
fi

# Test API
if curl -f http://localhost:8000/api/health >/dev/null 2>&1; then
    log "✅ API is responding"
else
    warn "⚠️ API health check failed"
fi

log "🎉 Database restore completed successfully!"
echo
echo -e "${GREEN}✅ Restore Summary:${NC}"
echo "   Source: $BACKUP_FILE"
echo "   Target: $DB_NAME"
echo "   Pre-restore backup: $PRE_RESTORE_BACKUP"
echo
echo -e "${GREEN}💡 Next steps:${NC}"
echo "   - Verify data integrity in admin panel"
echo "   - Check application logs for any issues"
echo "   - Test critical functionality"