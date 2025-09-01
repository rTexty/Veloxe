#!/bin/bash

# Veloxe Production Monitoring Script
# Usage: ./scripts/monitor.sh [--continuous] [--alerts]

set -e

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
LOG_DIR="./logs"
ALERT_EMAIL=""  # Set this to receive email alerts
CHECK_INTERVAL=60  # seconds

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
CONTINUOUS=false
ENABLE_ALERTS=false

for arg in "$@"; do
    case $arg in
        --continuous)
            CONTINUOUS=true
            shift
            ;;
        --alerts)
            ENABLE_ALERTS=true
            shift
            ;;
        *)
            echo "Usage: $0 [--continuous] [--alerts]"
            exit 1
            ;;
    esac
done

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

send_alert() {
    local message="$1"
    local subject="Veloxe Alert: $message"
    
    if [ "$ENABLE_ALERTS" = true ] && [ -n "$ALERT_EMAIL" ]; then
        echo "$message" | mail -s "$subject" "$ALERT_EMAIL" 2>/dev/null || true
    fi
    
    # Log alert
    error "ALERT: $message"
}

check_service_health() {
    local service="$1"
    local container_id
    
    container_id=$(docker-compose -f "$COMPOSE_FILE" ps -q "$service" 2>/dev/null)
    
    if [ -z "$container_id" ]; then
        return 1
    fi
    
    # Check if container is running
    if ! docker ps --filter "id=$container_id" --filter "status=running" | grep -q "$container_id"; then
        return 1
    fi
    
    # Check health status if available
    health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_id" 2>/dev/null || echo "unknown")
    
    case "$health_status" in
        "healthy")
            return 0
            ;;
        "unhealthy")
            return 1
            ;;
        "starting"|"unknown")
            # For services without health checks or still starting, check if running
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

check_api_endpoints() {
    # Check admin API health
    if ! curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
        return 1
    fi
    
    # Check if admin frontend is accessible
    if ! curl -sf http://localhost:3000/health >/dev/null 2>&1; then
        # Try main page if health endpoint doesn't exist
        if ! curl -sf http://localhost:3000/ >/dev/null 2>&1; then
            return 1
        fi
    fi
    
    return 0
}

check_database_connectivity() {
    if ! docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U veloxe -d veloxe >/dev/null 2>&1; then
        return 1
    fi
    return 0
}

check_redis_connectivity() {
    if ! docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping >/dev/null 2>&1; then
        return 1
    fi
    return 0
}

get_container_stats() {
    local service="$1"
    local container_id
    
    container_id=$(docker-compose -f "$COMPOSE_FILE" ps -q "$service" 2>/dev/null)
    
    if [ -n "$container_id" ]; then
        # Get CPU and memory usage
        docker stats --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" "$container_id" | tail -n 1
    else
        echo "N/A\tN/A\tN/A"
    fi
}

check_disk_space() {
    local usage
    usage=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$usage" -gt 90 ]; then
        send_alert "Disk space usage is ${usage}%"
    elif [ "$usage" -gt 80 ]; then
        warn "Disk space usage is ${usage}%"
    fi
    
    echo "${usage}%"
}

check_log_errors() {
    local error_count
    local recent_logs="$LOG_DIR/recent_errors.log"
    
    # Check for recent errors in logs
    find "$LOG_DIR" -name "*.log" -mmin -5 -exec grep -i "error\|exception\|critical" {} \; > "$recent_logs" 2>/dev/null || true
    
    error_count=$(wc -l < "$recent_logs" 2>/dev/null || echo 0)
    
    if [ "$error_count" -gt 10 ]; then
        send_alert "High error rate detected: $error_count errors in last 5 minutes"
    elif [ "$error_count" -gt 5 ]; then
        warn "Moderate error rate: $error_count errors in last 5 minutes"
    fi
    
    echo "$error_count"
}

perform_health_check() {
    local overall_status="✅ HEALTHY"
    local issues=0
    
    echo "=================================================="
    echo "🏥 VELOXE HEALTH CHECK - $(date)"
    echo "=================================================="
    
    # Check services
    echo
    echo "🔧 SERVICE STATUS:"
    services=("postgres" "redis" "bot" "admin-api" "admin-frontend")
    
    for service in "${services[@]}"; do
        if check_service_health "$service"; then
            echo "   ✅ $service: Running"
        else
            echo "   ❌ $service: Failed"
            overall_status="❌ UNHEALTHY"
            issues=$((issues + 1))
            send_alert "Service $service is not healthy"
        fi
    done
    
    # Check database connectivity
    echo
    echo "🗄️ DATABASE:"
    if check_database_connectivity; then
        echo "   ✅ PostgreSQL: Connected"
    else
        echo "   ❌ PostgreSQL: Connection failed"
        overall_status="❌ UNHEALTHY"
        issues=$((issues + 1))
        send_alert "Database connectivity failed"
    fi
    
    # Check Redis connectivity
    echo
    echo "🗄️ CACHE:"
    if check_redis_connectivity; then
        echo "   ✅ Redis: Connected"
    else
        echo "   ❌ Redis: Connection failed"
        overall_status="❌ UNHEALTHY"
        issues=$((issues + 1))
        send_alert "Redis connectivity failed"
    fi
    
    # Check API endpoints
    echo
    echo "🌐 API ENDPOINTS:"
    if check_api_endpoints; then
        echo "   ✅ API endpoints: Responsive"
    else
        echo "   ❌ API endpoints: Not responding"
        overall_status="❌ UNHEALTHY"
        issues=$((issues + 1))
        send_alert "API endpoints are not responding"
    fi
    
    # System resources
    echo
    echo "💻 SYSTEM RESOURCES:"
    echo "   💾 Disk usage: $(check_disk_space)"
    echo "   📊 Load average: $(uptime | awk -F'load average:' '{print $2}')"
    
    # Container stats
    echo
    echo "🐳 CONTAINER STATS (CPU/Memory):"
    for service in "${services[@]}"; do
        stats=$(get_container_stats "$service")
        echo "   📈 $service: $stats"
    done
    
    # Recent errors
    echo
    echo "🚨 RECENT ERRORS (last 5 min):"
    error_count=$(check_log_errors)
    echo "   ⚠️ Error count: $error_count"
    
    # Overall status
    echo
    echo "=================================================="
    echo "$overall_status"
    if [ "$issues" -gt 0 ]; then
        echo "Issues found: $issues"
    fi
    echo "=================================================="
    
    return $issues
}

# Main execution
if [ "$CONTINUOUS" = true ]; then
    log "🔄 Starting continuous monitoring (interval: ${CHECK_INTERVAL}s)"
    log "📧 Alerts enabled: $ENABLE_ALERTS"
    
    while true; do
        perform_health_check
        echo
        echo "⏰ Next check in ${CHECK_INTERVAL} seconds..."
        sleep "$CHECK_INTERVAL"
        clear
    done
else
    perform_health_check
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log "🎉 All systems are healthy!"
    else
        error "🚨 Found $exit_code issue(s)"
    fi
    
    exit $exit_code
fi