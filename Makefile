.PHONY: help start start-dev stop stop-dev logs clean install

# Default target
help:
	@echo "🚀 Veloxe MVP Commands"
	@echo ""
	@echo "📦 Setup:"
	@echo "  make install      Install all dependencies"
	@echo "  make setup-env    Create .env from template"
	@echo ""
	@echo "🏃 Run (choose one):"
	@echo "  make start        Start with Docker (production-like)"
	@echo "  make start-dev    Start in development mode"
	@echo ""
	@echo "🛑 Stop:"
	@echo "  make stop         Stop Docker services"
	@echo "  make stop-dev     Stop development services"
	@echo ""
	@echo "📊 Monitoring:"
	@echo "  make logs         View all Docker logs"
	@echo "  make logs-bot     View bot logs"
	@echo "  make logs-api     View API logs"
	@echo "  make logs-dev     View development logs"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  make clean        Clean Docker containers and images"
	@echo "  make reset        Reset everything (databases too!)"

# Installation
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	pip install psutil
	cd apps/admin/frontend && npm install

setup-env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ .env created from template. Please edit it with your values."; \
	else \
		echo "⚠️  .env already exists"; \
	fi

# Docker mode (production-like)
start:
	@./start.sh

stop:
	@echo "🛑 Stopping Docker services..."
	docker-compose down

logs:
	docker-compose logs -f

logs-bot:
	docker-compose logs -f bot

logs-api:
	docker-compose logs -f admin-api

# Development mode
start-dev:
	@./start-dev.sh

stop-dev:
	@./stop-dev.sh

logs-dev:
	@echo "📊 Development Logs:"
	@echo "Press Ctrl+C to stop viewing logs"
	@tail -f logs/*.log

# Cleanup
clean:
	@echo "🧹 Cleaning Docker resources..."
	docker-compose down --rmi all --volumes --remove-orphans
	docker system prune -f

reset: clean
	@echo "🔥 Resetting everything..."
	rm -rf logs/
	sudo rm -rf postgres_data/ redis_data/
	@echo "⚠️  All data deleted! Run 'make setup-env' and 'make install' again."

# Development helpers
shell-bot:
	docker-compose exec bot bash

shell-db:
	docker-compose exec postgres psql -U veloxe -d veloxe

shell-redis:
	docker-compose exec redis redis-cli