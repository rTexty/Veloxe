# 🚀 Быстрый доступ к админке с других компьютеров

## Вариант 1: По IP адресу (самый простой)

### На сервере:
```bash
# 1. Автоматическая настройка (замените на IP вашего сервера)
./scripts/setup-external-access.sh 192.168.1.100

# 2. Настройка firewall
sudo ufw allow 3000/tcp
sudo ufw allow 8000/tcp
sudo ufw reload

# 3. Настройка переменных
cp .env.external .env
sed -i 's/YOUR_SERVER_IP_HERE/192.168.1.100/g' .env
nano .env  # заполните токены BOT_TOKEN, OPENAI_API_KEY, ADMIN_SECRET

# 4. Запуск
./scripts/start-external.sh
```

### С любого компьютера:
- Откройте браузер и перейдите на: `http://192.168.1.100:3000`

---

## Вариант 2: Через домен (если есть)

### На сервере:
```bash
# 1. Настройка для домена
./scripts/setup-external-access.sh yourdomain.com

# 2. Остальные шаги как в варианте 1
```

### С любого компьютера:
- Откройте браузер и перейдите на: `http://yourdomain.com:3000`

---

## Вариант 3: Только локальная сеть (безопаснее)

Если сервер в локальной сети (192.168.x.x, 10.x.x.x):
```bash
# Используйте локальный IP сервера
./scripts/setup-external-access.sh 192.168.1.100

# Админка будет доступна только из локальной сети
```

---

## 🔒 Безопасность

1. **Обязательно смените пароли:**
   - `ADMIN_SECRET` - минимум 64 символа
   - `POSTGRES_PASSWORD` - сложный пароль для БД

2. **Для продакшена рекомендуется:**
   - Настроить HTTPS с SSL сертификатами
   - Использовать VPN для доступа
   - Ограничить доступ по IP адресам

---

## ❗ Проблемы и решения

### Админка не открывается:
```bash
# Проверить статус сервисов
./scripts/manage.sh status

# Проверить логи
./scripts/manage.sh logs admin-frontend
./scripts/manage.sh logs admin-api

# Проверить открыты ли порты
sudo netstat -tlnp | grep :3000
sudo netstat -tlnp | grep :8000
```

### Нет доступа с других компьютеров:
```bash
# Проверить firewall
sudo ufw status

# Открыть порты
sudo ufw allow 3000/tcp
sudo ufw allow 8000/tcp
```

### API не отвечает:
```bash
# Тест с сервера
curl http://localhost:8000/api/health

# Тест извне
curl http://ВАШ_IP:8000/api/health
```

---

## 📞 Полезные команды

```bash
# Узнать IP сервера
ip addr show | grep inet

# Перезапустить с внешним доступом
./scripts/start-external.sh

# Вернуться к локальному доступу
./scripts/manage.sh start

# Мониторинг
./scripts/monitor.sh
```

🎉 **Готово! Админка доступна с любого компьютера!**