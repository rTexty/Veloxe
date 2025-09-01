#!/bin/bash

echo "🛑 Stopping Veloxe Development Services..."

# Kill processes by PID files and related processes
for service in bot admin-api admin-frontend; do
    if [ -f "logs/${service}.pid" ]; then
        pid=$(cat "logs/${service}.pid")
        if kill -0 $pid 2>/dev/null; then
            echo "🔴 Stopping $service (PID: $pid)..."
            # Kill process and all children
            pkill -P $pid 2>/dev/null || true
            kill $pid 2>/dev/null || true
            rm "logs/${service}.pid"
        else
            echo "⚪ $service was not running"
            rm -f "logs/${service}.pid"
        fi
    fi
done

# Kill any remaining uvicorn/python processes on our ports
echo "🧹 Cleaning up any remaining processes..."
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
lsof -ti :3001 | xargs kill -9 2>/dev/null || true
lsof -ti :3002 | xargs kill -9 2>/dev/null || true
lsof -ti :3003 | xargs kill -9 2>/dev/null || true
lsof -ti :3004 | xargs kill -9 2>/dev/null || true
lsof -ti :3005 | xargs kill -9 2>/dev/null || true

# Stop Docker services but keep data
echo "🐳 Stopping Docker databases..."
docker-compose stop postgres redis

echo ""
echo "✅ All development services stopped!"
echo ""
echo "💡 To start again: ./start-dev.sh"
echo "💡 To view logs: ls logs/"