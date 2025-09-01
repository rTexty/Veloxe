#!/bin/bash

echo "🚀 Starting Veloxe MVP..."

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found! Please copy .env.example to .env and configure it."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Build and start all services
echo "📦 Building and starting all services..."
docker-compose up --build -d

echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "🎉 Veloxe MVP is starting up!"
echo ""
echo "📱 Services:"
echo "   • Telegram Bot: Running in background"
echo "   • Admin API: http://localhost:8000"
echo "   • Admin Panel: http://localhost:3000"
echo "   • API Docs: http://localhost:8000/docs"
echo ""
echo "💾 Databases:"
echo "   • PostgreSQL: localhost:5432 (veloxe/veloxe123)"
echo "   • Redis: localhost:6379"
echo ""
echo "🔧 Useful commands:"
echo "   docker-compose logs -f          # View all logs"
echo "   docker-compose logs -f bot      # View bot logs"
echo "   docker-compose stop             # Stop all services"
echo "   docker-compose down             # Stop and remove containers"
echo ""
echo "✅ Setup complete! Check the logs if something isn't working."