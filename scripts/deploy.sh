#!/bin/bash

# Veloxe Production Deployment Script
# Usage: ./scripts/deploy.sh [--no-backup] [--force]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="veloxe"
BACKUP_DIR="./backups"
LOG_FILE="./logs/deploy.log"
COMPOSE_FILE="docker-compose.prod.yml"

# Parse arguments
SKIP_BACKUP=false
FORCE_DEPLOY=false

for arg in "$@"; do
    case $arg in
        --no-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --force)
            FORCE_DEPLOY=true
            shift
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Usage: $0 [--no-backup] [--force]"
            exit 1
            ;;
    esac
done

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a $LOG_FILE
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}" | tee -a $LOG_FILE
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a $LOG_FILE
    exit 1
}

# Create necessary directories
mkdir -p logs backups ssl

log "🚀 Starting Veloxe production deployment..."

# Check if .env file exists
if [ ! -f .env ]; then
    error "❌ .env file not found. Copy .env.production to .env and configure it."
fi

# Check if docker-compose.prod.yml exists
if [ ! -f $COMPOSE_FILE ]; then
    error "❌ $COMPOSE_FILE not found."
fi

# Load environment variables from .env file
log "📂 Loading environment variables from .env file..."
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Verify required environment variables
log "🔍 Checking environment variables..."
required_vars=("BOT_TOKEN" "OPENAI_API_KEY" "ADMIN_SECRET" "POSTGRES_PASSWORD")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        error "❌ Required environment variable $var is not set in .env file"
    else
        log "✅ $var is set"
    fi
done

# Check if services are running
if docker-compose -f $COMPOSE_FILE ps | grep -q "Up"; then
    if [ "$FORCE_DEPLOY" = false ]; then
        warn "⚠️ Services are currently running. Use --force to continue anyway."
        read -p "Continue with deployment? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "❌ Deployment cancelled by user"
            exit 1
        fi
    fi
fi

# Create database backup
if [ "$SKIP_BACKUP" = false ]; then
    log "💾 Creating database backup..."
    if ! ./scripts/backup.sh; then
        warn "⚠️ Backup failed, but continuing with deployment"
    fi
else
    warn "⚠️ Skipping database backup as requested"
fi

# Stop existing services
log "🛑 Stopping existing services..."
docker-compose -f $COMPOSE_FILE down --remove-orphans

# Pull latest images
log "📦 Pulling latest Docker images..."
docker-compose -f $COMPOSE_FILE pull

# Build services
log "🔨 Building services..."
docker-compose -f $COMPOSE_FILE build --no-cache

# Run database migrations
log "📊 Running database migrations..."
docker-compose -f $COMPOSE_FILE up -d postgres redis
sleep 10  # Wait for postgres to be ready

# Wait for postgres to be healthy
log "⏳ Waiting for database to be ready..."
timeout=60
counter=0
while [ $counter -lt $timeout ]; do
    if docker-compose -f $COMPOSE_FILE exec -T postgres pg_isready -U veloxe -d veloxe >/dev/null 2>&1; then
        log "✅ Database is ready"
        break
    fi
    counter=$((counter + 1))
    sleep 1
done

if [ $counter -eq $timeout ]; then
    error "❌ Database failed to start within ${timeout} seconds"
fi

# Run migrations
log "🔄 Running Alembic migrations..."
docker-compose -f $COMPOSE_FILE run --rm bot alembic upgrade head

# Start all services
log "🚀 Starting all services..."
docker-compose -f $COMPOSE_FILE up -d

# Wait for services to be healthy
log "⏳ Waiting for services to be healthy..."
sleep 30

# Health checks
log "🏥 Performing health checks..."
services=("postgres" "redis" "bot" "admin-api")
for service in "${services[@]}"; do
    if docker-compose -f $COMPOSE_FILE ps $service | grep -q "Up (healthy)\|Up"; then
        log "✅ $service is running"
    else
        warn "⚠️ $service might not be healthy"
    fi
done

# Test API endpoint
log "🌐 Testing API endpoint..."
if curl -f http://localhost:8000/api/health >/dev/null 2>&1; then
    log "✅ API is responding"
else
    warn "⚠️ API health check failed"
fi

# Clean up old Docker images
log "🧹 Cleaning up old Docker images..."
docker image prune -af

# Show running services
log "📋 Current service status:"
docker-compose -f $COMPOSE_FILE ps

# Show logs
log "📄 Recent logs (last 50 lines):"
docker-compose -f $COMPOSE_FILE logs --tail=50

log "🎉 Deployment completed successfully!"
log "📊 Admin panel: http://localhost:3000"
log "🔗 API docs: http://localhost:8000/docs"
log "📝 Logs location: ./logs/"
log "💾 Backups location: ./backups/"

echo
echo -e "${GREEN}🚀 Veloxe is now running in production mode!${NC}"
echo -e "${BLUE}💡 Tips:${NC}"
echo "   - Monitor logs: docker-compose -f $COMPOSE_FILE logs -f"
echo "   - Check status: docker-compose -f $COMPOSE_FILE ps"
echo "   - Stop services: docker-compose -f $COMPOSE_FILE down"