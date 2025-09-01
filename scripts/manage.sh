#!/bin/bash

# Veloxe Production Management Script
# Usage: ./scripts/manage.sh <command> [options]

set -e

COMPOSE_FILE="docker-compose.prod.yml"

# Load environment variables if .env exists
if [ -f .env ]; then
    set -a  # automatically export all variables
    source .env 2>/dev/null || true
    set +a  # disable automatic export
fi

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

show_usage() {
    echo "Veloxe Production Management"
    echo "Usage: $0 <command> [options]"
    echo
    echo "Commands:"
    echo "  start              Start all services"
    echo "  stop               Stop all services"  
    echo "  restart            Restart all services"
    echo "  status             Show service status"
    echo "  logs [service]     Show logs for all services or specific service"
    echo "  backup             Create database backup"
    echo "  restore <file>     Restore database from backup"
    echo "  migrate            Run database migrations"
    echo "  shell <service>    Open shell in service container"
    echo "  update             Update and restart services"
    echo "  monitor            Show system health"
    echo "  clean              Clean unused Docker resources"
    echo
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 logs bot"
    echo "  $0 backup"
    echo "  $0 restore ./backups/veloxe_backup_20240101_120000.sql.gz"
}

case "${1:-}" in
    start)
        log "🚀 Starting Veloxe services..."
        docker-compose -f $COMPOSE_FILE up -d
        log "✅ Services started"
        ;;
    
    stop)
        log "🛑 Stopping Veloxe services..."
        docker-compose -f $COMPOSE_FILE down
        log "✅ Services stopped"
        ;;
    
    restart)
        log "🔄 Restarting Veloxe services..."
        docker-compose -f $COMPOSE_FILE down
        docker-compose -f $COMPOSE_FILE up -d
        log "✅ Services restarted"
        ;;
    
    status)
        log "📊 Service status:"
        docker-compose -f $COMPOSE_FILE ps
        ;;
    
    logs)
        service="${2:-}"
        if [ -n "$service" ]; then
            log "📄 Showing logs for $service..."
            docker-compose -f $COMPOSE_FILE logs -f "$service"
        else
            log "📄 Showing logs for all services..."
            docker-compose -f $COMPOSE_FILE logs -f
        fi
        ;;
    
    backup)
        log "💾 Creating database backup..."
        ./scripts/backup.sh
        ;;
    
    restore)
        backup_file="${2:-}"
        if [ -z "$backup_file" ]; then
            error "❌ Please specify backup file to restore"
        fi
        log "🔄 Restoring database from $backup_file..."
        ./scripts/restore.sh "$backup_file"
        ;;
    
    migrate)
        log "🗄️ Running database migrations..."
        docker-compose -f $COMPOSE_FILE run --rm bot alembic upgrade head
        log "✅ Migrations completed"
        ;;
    
    shell)
        service="${2:-bot}"
        log "🐚 Opening shell in $service container..."
        docker-compose -f $COMPOSE_FILE exec "$service" /bin/sh
        ;;
    
    update)
        log "🔄 Updating Veloxe..."
        docker-compose -f $COMPOSE_FILE pull
        docker-compose -f $COMPOSE_FILE build --no-cache
        docker-compose -f $COMPOSE_FILE down
        docker-compose -f $COMPOSE_FILE up -d
        log "✅ Update completed"
        ;;
    
    monitor)
        log "🏥 Running health check..."
        ./scripts/monitor.sh
        ;;
    
    clean)
        log "🧹 Cleaning Docker resources..."
        docker system prune -f
        docker volume prune -f
        log "✅ Cleanup completed"
        ;;
    
    help|--help|-h)
        show_usage
        ;;
    
    *)
        if [ -z "${1:-}" ]; then
            error "❌ No command specified"
        else
            error "❌ Unknown command: $1"
        fi
        echo
        show_usage
        exit 1
        ;;
esac