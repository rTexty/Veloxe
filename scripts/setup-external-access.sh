#!/bin/bash

# Скрипт для настройки внешнего доступа к админке
# Usage: ./scripts/setup-external-access.sh <server-ip-or-domain>

set -e

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

SERVER_ADDRESS="$1"

if [ -z "$SERVER_ADDRESS" ]; then
    error "❌ Укажите IP адрес или домен сервера"
fi

log "🌐 Настройка внешнего доступа к админке Veloxe"
log "🖥️ Адрес сервера: $SERVER_ADDRESS"

# Обновляем docker-compose для внешнего доступа
log "📝 Обновление docker-compose.prod.yml для внешнего доступа..."

# Создаем специальный compose файл для внешнего доступа
cat > docker-compose.external.yml << EOF
version: '3.8'

services:
  # PostgreSQL Database with persistent storage
  postgres:
    image: postgres:15-alpine
    container_name: veloxe_postgres
    environment:
      POSTGRES_DB: \${POSTGRES_DB:-veloxe}
      POSTGRES_USER: \${POSTGRES_USER:-veloxe}
      POSTGRES_PASSWORD: \${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    ports:
      - "127.0.0.1:5432:5432"  # БД только локально
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U \${POSTGRES_USER:-veloxe} -d \${POSTGRES_DB:-veloxe}"]
      interval: 10s
      timeout: 5s
      retries: 5
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  # Redis Cache with persistent storage
  redis:
    image: redis:7-alpine
    container_name: veloxe_redis
    volumes:
      - redis_data:/data
    ports:
      - "127.0.0.1:6379:6379"  # Redis только локально
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  # Telegram Bot
  bot:
    build:
      context: .
      dockerfile: apps/bot/Dockerfile
    container_name: veloxe_bot
    environment:
      - BOT_TOKEN=\${BOT_TOKEN}
      - OPENAI_API_KEY=\${OPENAI_API_KEY}
      - DATABASE_URL=postgresql+asyncpg://\${POSTGRES_USER:-veloxe}:\${POSTGRES_PASSWORD}@postgres:5432/\${POSTGRES_DB:-veloxe}
      - REDIS_URL=redis://redis:6379/0
      - ADMIN_SECRET=\${ADMIN_SECRET}
      - ENVIRONMENT=production
      - SENTRY_DSN=\${SENTRY_DSN}
      - LOG_LEVEL=\${LOG_LEVEL:-info}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"

  # Admin API (FastAPI) - ОТКРЫТ НАРУЖУ
  admin-api:
    build:
      context: .
      dockerfile: apps/admin/backend/Dockerfile
    container_name: veloxe_admin_api
    environment:
      - DATABASE_URL=postgresql+asyncpg://\${POSTGRES_USER:-veloxe}:\${POSTGRES_PASSWORD}@postgres:5432/\${POSTGRES_DB:-veloxe}
      - REDIS_URL=redis://redis:6379/0
      - ADMIN_SECRET=\${ADMIN_SECRET}
      - ENVIRONMENT=production
      - SENTRY_DSN=\${SENTRY_DSN}
      - WORKERS=\${WORKERS:-4}
      - LOG_LEVEL=\${LOG_LEVEL:-info}
    ports:
      - "8000:8000"  # API доступен извне
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"

  # Admin Frontend (React) - ОТКРЫТ НАРУЖУ
  admin-frontend:
    build:
      context: .
      dockerfile: apps/admin/frontend/Dockerfile.prod
      args:
        - REACT_APP_API_URL=http://$SERVER_ADDRESS:8000/api
    container_name: veloxe_admin_frontend
    ports:
      - "3000:80"  # Фронтенд доступен извне
    depends_on:
      - admin-api
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local

networks:
  default:
    driver: bridge
EOF

log "✅ Создан docker-compose.external.yml"

# Настройка firewall правил
log "🛡️ Настройка firewall правил..."

info "Добавьте следующие правила в firewall сервера:"
echo "  sudo ufw allow 3000/tcp comment 'Veloxe Admin Frontend'"
echo "  sudo ufw allow 8000/tcp comment 'Veloxe Admin API'"
echo "  sudo ufw reload"

# Создаем скрипт запуска с внешним доступом
cat > scripts/start-external.sh << 'EOF'
#!/bin/bash

# Запуск Veloxe с внешним доступом

set -e

GREEN='\033[0;32m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

log "🌐 Запуск Veloxe с внешним доступом..."

# Проверка .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден. Скопируйте .env.external в .env и настройте его."
    exit 1
fi

# Остановка существующих сервисов
log "🛑 Остановка существующих сервисов..."
docker-compose -f docker-compose.external.yml down 2>/dev/null || true

# Запуск с внешним доступом
log "🚀 Запуск сервисов с внешним доступом..."
docker-compose -f docker-compose.external.yml up -d

log "✅ Сервисы запущены!"
log "🌐 Админка доступна по адресу: http://YOUR_SERVER_IP:3000"
log "🔗 API доступен по адресу: http://YOUR_SERVER_IP:8000"
EOF

chmod +x scripts/start-external.sh

log "✅ Создан скрипт scripts/start-external.sh"

# Инструкции для пользователя
echo
info "📋 СЛЕДУЮЩИЕ ШАГИ НА СЕРВЕРЕ:"
echo
echo "1. Настройте firewall:"
echo "   sudo ufw allow 3000/tcp comment 'Veloxe Admin Frontend'"
echo "   sudo ufw allow 8000/tcp comment 'Veloxe Admin API'"
echo "   sudo ufw reload"
echo
echo "2. Скопируйте и настройте конфигурацию:"
echo "   cp .env.external .env"
echo "   nano .env  # замените YOUR_SERVER_IP_HERE на $SERVER_ADDRESS"
echo
echo "3. Запустите с внешним доступом:"
echo "   ./scripts/start-external.sh"
echo
echo "4. Админка будет доступна по адресу:"
echo "   http://$SERVER_ADDRESS:3000"
echo
warn "⚠️ БЕЗОПАСНОСТЬ:"
echo "   - Используйте сильный ADMIN_SECRET (64 символа)"
echo "   - Рассмотрите настройку HTTPS с SSL сертификатами"
echo "   - Ограничьте доступ по IP если возможно"

log "🎉 Настройка внешнего доступа завершена!"