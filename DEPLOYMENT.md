# 🚀 Veloxe Production Deployment Guide

Это руководство по деплою Veloxe чатбота на продакшен сервер.

## 📋 Системные требования

### Минимальные требования:
- **CPU**: 2 ядра
- **RAM**: 4 GB
- **Диск**: 20 GB свободного места
- **ОС**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **Docker**: 24.0+
- **Docker Compose**: 2.0+

### Рекомендуемые требования:
- **CPU**: 4 ядра
- **RAM**: 8 GB
- **Диск**: 50 GB SSD
- **ОС**: Ubuntu 22.04 LTS

## 🛠️ Предварительная настройка сервера

### 1. Обновление системы
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Установка Docker
```bash
# Удаление старых версий
sudo apt remove docker docker-engine docker.io containerd runc

# Установка зависимостей
sudo apt install apt-transport-https ca-certificates curl gnupg lsb-release

# Добавление GPG ключа Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Добавление репозитория
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установка Docker
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER
```

### 3. Установка дополнительных утилит
```bash
sudo apt install curl jq htop ncdu git
```

## 📁 Подготовка проекта

### 1. Клонирование репозитория
```bash
git clone <repository-url> veloxe
cd veloxe
```

### 2. Настройка переменных окружения
```bash
# Копирование шаблона
cp .env.production .env

# Редактирование конфигурации
nano .env
```

#### Обязательные переменные:
```env
BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
ADMIN_SECRET=your_64_character_secret_key
POSTGRES_PASSWORD=your_strong_postgres_password
```

### 3. Создание необходимых директорий
```bash
mkdir -p logs backups ssl
chmod 755 scripts/*.sh
```

## 🚀 Деплой

### Автоматический деплой
```bash
./scripts/deploy.sh
```

### Ручной деплой
```bash
# Запуск базы данных
docker-compose -f docker-compose.prod.yml up -d postgres redis

# Ожидание готовности БД
sleep 30

# Миграции БД
docker-compose -f docker-compose.prod.yml run --rm bot alembic upgrade head

# Запуск всех сервисов
docker-compose -f docker-compose.prod.yml up -d
```

## 🔧 Управление сервисами

### Основные команды
```bash
# Управление сервисами
./scripts/manage.sh start      # Запуск
./scripts/manage.sh stop       # Остановка
./scripts/manage.sh restart    # Перезапуск
./scripts/manage.sh status     # Статус

# Логи
./scripts/manage.sh logs       # Все логи
./scripts/manage.sh logs bot   # Логи бота

# База данных
./scripts/manage.sh backup     # Бэкап БД
./scripts/manage.sh migrate    # Миграции

# Мониторинг
./scripts/manage.sh monitor    # Проверка здоровья
```

### Мониторинг
```bash
# Разовая проверка
./scripts/monitor.sh

# Непрерывный мониторинг
./scripts/monitor.sh --continuous

# С алертами
./scripts/monitor.sh --continuous --alerts
```

## 🔒 Безопасность

### 1. Firewall настройки
```bash
# UFW
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Закрытие прямого доступа к БД/Redis
sudo ufw deny 5432
sudo ufw deny 6379
```

### 2. SSL сертификаты (Let's Encrypt)
```bash
# Установка Certbot
sudo apt install snapd
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot

# Получение сертификата
sudo certbot certonly --standalone -d your-domain.com

# Копирование сертификатов
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./ssl/key.pem
sudo chown $USER:$USER ./ssl/*.pem
```

### 3. Автообновление сертификатов
```bash
# Добавить в crontab
echo "0 0,12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

## 📊 Мониторинг и логи

### Расположение логов
- **Приложение**: `./logs/veloxe.log`
- **Ошибки**: `./logs/veloxe_error.log`
- **Docker**: `./logs/docker/`
- **Nginx**: `./logs/nginx/`

### Ротация логов
Логи автоматически ротируются:
- Максимальный размер: 10MB
- Количество файлов: 5
- Кодировка: UTF-8

### Системные метрики
```bash
# Использование ресурсов контейнерами
docker stats

# Состояние дисков
df -h

# Использование памяти
free -h

# Загрузка системы
htop
```

## 🗄️ База данных

### Бэкапы
```bash
# Ручной бэкап
./scripts/backup.sh

# Автоматические бэкапы (crontab)
0 2 * * * /path/to/veloxe/scripts/backup.sh
```

### Восстановление
```bash
./scripts/restore.sh ./backups/veloxe_backup_20240101_120000.sql.gz
```

### Миграции
```bash
# Применить все миграции
./scripts/manage.sh migrate

# Проверить состояние
docker-compose -f docker-compose.prod.yml run --rm bot alembic current
```

## 🔧 Обслуживание

### Обновление приложения
```bash
# Получить изменения
git pull origin main

# Обновить и перезапустить
./scripts/manage.sh update
```

### Очистка системы
```bash
# Очистка Docker
./scripts/manage.sh clean

# Очистка старых логов
find ./logs -name "*.log.*" -mtime +30 -delete

# Очистка старых бэкапов
find ./backups -name "*.gz" -mtime +30 -delete
```

## 🚨 Устранение проблем

### Проверка здоровья сервисов
```bash
# Статус контейнеров
docker-compose -f docker-compose.prod.yml ps

# Проверка здоровья
./scripts/monitor.sh

# Логи ошибок
docker-compose -f docker-compose.prod.yml logs bot | grep ERROR
```

### Типичные проблемы

#### 1. База данных недоступна
```bash
# Проверка подключения
docker-compose -f docker-compose.prod.yml exec postgres pg_isready

# Перезапуск БД
docker-compose -f docker-compose.prod.yml restart postgres
```

#### 2. Бот не отвечает
```bash
# Проверка логов бота
docker-compose -f docker-compose.prod.yml logs bot

# Проверка токена
echo $BOT_TOKEN

# Перезапуск бота
docker-compose -f docker-compose.prod.yml restart bot
```

#### 3. API недоступен
```bash
# Проверка API
curl http://localhost:8000/api/health

# Логи API
docker-compose -f docker-compose.prod.yml logs admin-api

# Перезапуск API
docker-compose -f docker-compose.prod.yml restart admin-api
```

## 📞 Поддержка

### Контакты
- **Логи**: `./logs/`
- **Мониторинг**: `./scripts/monitor.sh`
- **Документация**: `CLAUDE.md`

### Полезные команды
```bash
# Проверка версий
docker --version
docker-compose --version

# Использование ресурсов
docker system df

# Информация о контейнерах
docker inspect veloxe_bot
```

---

## ✅ Чек-лист деплоя

- [ ] Сервер настроен и обновлен
- [ ] Docker установлен и работает
- [ ] Переменные окружения настроены
- [ ] SSL сертификаты установлены (для HTTPS)
- [ ] Firewall настроен
- [ ] Автоматические бэкапы настроены
- [ ] Мониторинг настроен
- [ ] Telegram бот токен получен
- [ ] OpenAI API ключ получен
- [ ] Домен настроен (если нужен)

## 🌐 Доступ к админке с других компьютеров

### Быстрая настройка внешнего доступа:

```bash
# Автоматическая настройка (замените на IP вашего сервера)
./scripts/setup-external-access.sh 192.168.1.100

# Настройка firewall
sudo ufw allow 3000/tcp comment 'Veloxe Admin Frontend'
sudo ufw allow 8000/tcp comment 'Veloxe Admin API'
sudo ufw reload

# Настройка переменных окружения
cp .env.external .env
nano .env  # замените YOUR_SERVER_IP_HERE на реальный IP

# Запуск с внешним доступом
./scripts/start-external.sh
```

### Доступ к админке:
- **Админка**: `http://ВАШ_IP:3000`
- **API**: `http://ВАШ_IP:8000/docs`

### С доменным именем:
```bash
# Если у вас есть домен
./scripts/setup-external-access.sh yourdomain.com

# Админка будет доступна по адресу:
# http://yourdomain.com:3000
```

### ⚠️ Важные моменты безопасности:
- Используйте сильный `ADMIN_SECRET` (64+ символов)
- Настройте HTTPS для продакшена
- Рассмотрите VPN доступ для критичных систем
- Ограничьте доступ по IP если возможно

---

🎉 **Готово! Veloxe успешно развернут в продакшене!**