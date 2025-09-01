#!/bin/bash

# Скрипт для проверки переменных окружения
# Usage: ./scripts/check-env.sh

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
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

log "🔍 Проверка переменных окружения Veloxe"

# Проверка наличия .env файла
if [ ! -f .env ]; then
    error "❌ Файл .env не найден в текущей директории"
    echo
    info "💡 Создайте .env файл:"
    echo "   cp .env.production .env"
    echo "   nano .env"
    exit 1
fi

log "✅ Файл .env найден"

# Загрузка переменных окружения
log "📂 Загрузка переменных окружения..."
if [ -f .env ]; then
    set -a  # automatically export all variables
    if source .env 2>/dev/null; then
        log "✅ Переменные успешно загружены"
    else
        warn "⚠️ Проблема с загрузкой .env файла. Проверьте синтаксис."
    fi
    set +a  # disable automatic export
fi

echo
log "🔍 Проверка обязательных переменных:"

# Список обязательных переменных
declare -A required_vars=(
    ["BOT_TOKEN"]="Токен Telegram бота"
    ["OPENAI_API_KEY"]="API ключ OpenAI"
    ["ADMIN_SECRET"]="Секретный ключ для админки"
    ["POSTGRES_PASSWORD"]="Пароль PostgreSQL"
)

# Список рекомендуемых переменных
declare -A optional_vars=(
    ["POSTGRES_USER"]="Пользователь PostgreSQL (по умолчанию: veloxe)"
    ["POSTGRES_DB"]="Имя базы данных (по умолчанию: veloxe)"
    ["REDIS_URL"]="URL Redis сервера"
    ["DATABASE_URL"]="URL подключения к базе данных"
    ["SENTRY_DSN"]="URL для мониторинга ошибок Sentry"
    ["LOG_LEVEL"]="Уровень логирования (по умолчанию: info)"
)

issues_found=0

# Проверка обязательных переменных
for var in "${!required_vars[@]}"; do
    if [ -n "${!var}" ]; then
        # Маскируем секретные значения
        if [[ "$var" == *"TOKEN"* ]] || [[ "$var" == *"KEY"* ]] || [[ "$var" == *"SECRET"* ]] || [[ "$var" == *"PASSWORD"* ]]; then
            masked_value="${!var:0:8}***"
            log "  ✅ $var = $masked_value (${required_vars[$var]})"
        else
            log "  ✅ $var = ${!var} (${required_vars[$var]})"
        fi
    else
        error "  ❌ $var не установлена (${required_vars[$var]})"
        issues_found=$((issues_found + 1))
    fi
done

echo
log "📋 Рекомендуемые переменные:"

# Проверка рекомендуемых переменных
for var in "${!optional_vars[@]}"; do
    if [ -n "${!var}" ]; then
        log "  ✅ $var = ${!var} (${optional_vars[$var]})"
    else
        warn "  ⚠️ $var не установлена (${optional_vars[$var]})"
    fi
done

echo
log "🔐 Проверка безопасности:"

# Проверка длины ADMIN_SECRET
if [ -n "$ADMIN_SECRET" ]; then
    secret_length=${#ADMIN_SECRET}
    if [ $secret_length -lt 32 ]; then
        warn "  ⚠️ ADMIN_SECRET слишком короткий ($secret_length символов). Рекомендуется минимум 32 символа."
        issues_found=$((issues_found + 1))
    elif [ $secret_length -lt 64 ]; then
        warn "  ⚠️ ADMIN_SECRET коротковат ($secret_length символов). Рекомендуется 64+ символов."
    else
        log "  ✅ ADMIN_SECRET достаточно длинный ($secret_length символов)"
    fi
fi

# Проверка BOT_TOKEN формата
if [ -n "$BOT_TOKEN" ]; then
    if [[ $BOT_TOKEN =~ ^[0-9]+:[A-Za-z0-9_-]{35}$ ]]; then
        log "  ✅ BOT_TOKEN имеет правильный формат"
    else
        warn "  ⚠️ BOT_TOKEN может иметь неправильный формат"
    fi
fi

# Проверка OPENAI_API_KEY формата
if [ -n "$OPENAI_API_KEY" ]; then
    if [[ $OPENAI_API_KEY =~ ^sk-[A-Za-z0-9]{20}T3BlbkFJ[A-Za-z0-9]{20}$ ]] || [[ $OPENAI_API_KEY =~ ^sk-[A-Za-z0-9_-]{43,}$ ]]; then
        log "  ✅ OPENAI_API_KEY имеет правильный формат"
    else
        warn "  ⚠️ OPENAI_API_KEY может иметь неправильный формат"
    fi
fi

echo
if [ $issues_found -eq 0 ]; then
    log "🎉 Все обязательные переменные установлены! Готово к деплою."
    echo
    info "💡 Следующие шаги:"
    echo "   ./scripts/deploy.sh        # Деплой в продакшен"
    echo "   ./scripts/manage.sh start  # Запуск сервисов"
    exit 0
else
    error "🚨 Найдено $issues_found проблем. Исправьте их перед деплоем."
    echo
    info "💡 Для исправления:"
    echo "   nano .env  # Отредактируйте файл"
    echo "   ./scripts/check-env.sh  # Повторная проверка"
    exit 1
fi