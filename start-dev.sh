#!/bin/bash

echo "🧑‍💻 Starting Veloxe MVP in Development Mode..."

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found! Please copy .env.example to .env and configure it."
    exit 1
fi

# Always stop existing processes first
echo "🧹 Stopping any existing processes..."
./stop-dev.sh >/dev/null 2>&1 || true

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo "⚠️  Port $1 is already in use"
        return 1
    fi
    return 0
}

# Check required ports (databases are expected to be running)
check_port 5432 || echo "   PostgreSQL might be running"
check_port 6379 || echo "   Redis might be running"

echo ""
echo "🏗️  Setting up development environment..."


# Install Node dependencies
echo "📦 Installing Node dependencies..."
cd apps/admin/frontend
npm install
cd ../../..

echo ""
echo "🚀 Starting services..."

# Start PostgreSQL and Redis with Docker
echo "🐳 Starting PostgreSQL and Redis..."
docker-compose up -d postgres redis

# Wait for databases
echo "⏳ Waiting for databases..."
sleep 5

# Export environment variables from .env
export $(grep -v '^#' .env | xargs)

# Function to run in background with logging
run_service() {
    local service_name=$1
    local command=$2
    local log_file="logs/${service_name}.log"
    
    mkdir -p logs
    echo "▶️  Starting $service_name..."
    nohup bash -c "export \$(grep -v '^#' .env | xargs) && $command" > "$log_file" 2>&1 &
    echo $! > "logs/${service_name}.pid"
}

# Start all services
run_service "bot" "cd apps/bot && python3 main.py"
run_service "admin-api" "cd apps/admin/backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000"
run_service "admin-frontend" "cd apps/admin/frontend && npm run dev"

echo ""
echo "⏳ Services are starting up..."
sleep 10

echo ""
echo "🎉 Development environment is ready!"
echo ""
echo "📱 Services:"
echo "   • Telegram Bot: Running (check logs/bot.log)"
echo "   • Admin API: http://localhost:8000 (check logs/admin-api.log)"
echo "   • Admin Panel: http://localhost:3001 (check logs/admin-frontend.log)"
echo ""
echo "🔍 Monitoring:"
echo "   tail -f logs/bot.log           # Bot logs"
echo "   tail -f logs/admin-api.log     # API logs"
echo "   tail -f logs/admin-frontend.log # Frontend logs"
echo ""
echo "🛑 Stop services:"
echo "   ./stop-dev.sh                  # Stop all services"
echo ""
echo "✅ Happy coding! 🚀"