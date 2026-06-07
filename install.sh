#!/bin/bash

################################################################################
# SDA Telegram App - Автоматизированная установка на Ubuntu сервер
# Сценарий: обновление Ubuntu -> установка Docker -> настройка nginx -> SSL -> запуск
################################################################################

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# === 1. Проверка прав root ===
log_info "Проверка прав суперпользователя..."
if [ "$EUID" -ne 0 ]; then
    log_error "Пожалуйста, запустите скрипт через sudo"
    exit 1
fi

# === 2. Обновление системы ===
log_info "Обновление системы Ubuntu..."
echo "================================================"
echo "Этот шаг может занять 10-15 минут."
echo "Пожалуйста, следите за выводом..."
echo "================================================"
apt update
apt upgrade -y
apt install -y curl git wget nano htop

log_success "Система обновлена"

# === 3. Установка Docker и Docker Compose ===
log_info "Установка Docker и Docker Compose..."

# Удаление старых версий Docker
apt remove -y docker docker-engine docker.io containerd runc > /dev/null 2>&1 || true

# Устанавливаем необходимые пакеты
apt install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Добавляем ключ Docker GPG
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Добавляем репозиторий Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установка Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Запуск Docker и добавление в автозагрузку
systemctl start docker
systemctl enable docker

# Проверка установки
if ! command -v docker &> /dev/null || ! command -v docker-compose &> /dev/null; then
    log_error "Docker или Docker Compose не установлены корректно"
    exit 1
fi

log_success "Docker и Docker Compose установлены"

# === 4. Установка Certbot для Let's Encrypt ===
log_info "Установка Certbot для получения SSL сертификата..."
apt install -y certbot python3-certbot-nginx

log_success "Certbot установлен"

# === 5. Настройка брандмауэра (ufw) ===
log_info "Настройка брандмауэра..."
ufw allow OpenSSH > /dev/null 2>&1
ufw allow 80/tcp > /dev/null 2>&1
ufw allow 443/tcp > /dev/null 2>&1
ufw --force enable > /dev/null 2>&1

log_success "Брандмауэр настроен"

# === 6. Клонирование репозитория ===
log_info "Получение кода приложения из GitHub..."
cd /root
rm -rf telegram-app 2>/dev/null || true
git clone https://github.com/izliliput-dev/telegram-app.git > /dev/null 2>&1
if [ $? -ne 0 ]; then
    log_error "Не удалось клонировать репозиторий"
    exit 1
fi

cd telegram-app

log_success "Репозиторий клонирован"

# === 7. Создание конфигурационных файлов ===
log_info "Создание конфигурационных файлов..."

# Создаем .env файл с запросом переменных
read -p "Введите токен вашего Telegram бота: " TELEGRAM_BOT_TOKEN
read -p "Введите домен для приложения (например, botsda.hackquest.com): " DOMAIN
read -p "Введите email для Let's Encrypt (для уведомлений): " EMAIL
read -p "Введите секретный ключ для шифрования (минимум 32 символа, или оставьте пустым для генерации): " ENCRYPTION_KEY

# Генерируем случайный ключ если не введен
if [ -z "$ENCRYPTION_KEY" ]; then
    ENCRYPTION_KEY=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)
    log_warn "Сгенерирован случайный ключ шифрования: $ENCRYPTION_KEY\nСохраните его для восстановления данных!"
fi

# Создаем .env файл
cat > .env << EOF
TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN
WEB_APP_URL=https://$DOMAIN
ENCRYPTION_KEY=$ENCRYPTION_KEY
STORAGE_PATH=/app/storage
PORT=8000
EOF

log_success ".env файл создан"

# === 8. Создание конфигурации nginx ===
log_info "Создание конфигурации nginx..."

mkdir -p nginx/nginx.conf nginx/conf.d nginx/ssl nginx/html

cat > nginx/nginx.conf << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    keepalive_timeout 65;

    include /etc/nginx/conf.d/*.conf;
}
EOF

cat > nginx/conf.d/$DOMAIN.conf << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location /.well-known/acme-challenge/ {
        root /usr/share/nginx/html;
    }

    location / {
        return 302 https://\$server_name\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate /etc/nginx/ssl/\$server_name/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/\$server_name/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl.session_timeout 1d;
    ssl_session_cache shared:SSL:50m;

    access_log /var/log/nginx/\$server_name.access.log;
    error_log /var/log/nginx/\$server_name.error.log;

    client_max_body_size 10M;

    location / {
        proxy_pass http://frontend:80;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

log_success "nginx конфигурация создана"

# === 9. Обновление docker-compose.yml ===
log_info "Обновление docker-compose.yml..."

cat > docker-compose.yml << EOF
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - TELEGRAM_BOT_TOKEN=\${TELEGRAM_BOT_TOKEN}
      - WEB_APP_URL=\${WEB_APP_URL}
      - ENCRYPTION_KEY=\${ENCRYPTION_KEY}
      - STORAGE_PATH=/app/storage
      - PORT=8000
    volumes:
      - ./backend/storage:/app/storage
    restart: unless-stopped
    networks:
      - sda-network
    expose:
      - "8000"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      - REACT_APP_API_URL=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - sda-network

  bot:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: python bot.py
    environment:
      - TELEGRAM_BOT_TOKEN=\${TELEGRAM_BOT_TOKEN}
      - WEB_APP_URL=\${WEB_APP_URL}
      - ENCRYPTION_KEY=\${ENCRYPTION_KEY}
      - STORAGE_PATH=/app/storage
    volumes:
      - ./backend/storage:/app/storage
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - sda-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/ssl:/etc/nginx/ssl:rw
      - ./nginx/html:/usr/share/nginx/html:rw
    depends_on:
      - frontend
      - backend
    restart: unless-stopped
    networks:
      - sda-network

networks:
  sda-network:
    driver: bridge
EOF

log_success "docker-compose.yml обновлен"

# === 10. Создание папок для хранения ===
log_info "Создание директорий для хранения..."
mkdir -p backend/storage/mafiles
mkdir -p nginx/ssl/$DOMAIN
mkdir -p nginx/html/.well-known/acme-challenge

log_success "Директории созданы"

# === 11. Получение SSL сертификата ===
echo "================================================"
echo "ВНИМАНИЕ: Для получения SSL сертификата необходимо"
echo "1. Настроить DNS запись A для домена $DOMAIN"
echo "2. Убедиться, что порт 80 открыт на сервере"
echo "================================================"

read -p "DNS запись A уже настроена? (да/нет): " DNS_CONFIGURED
if [ "$DNS_CONFIGURED" != "да" ]; then
    log_error "Сначала настройте DNS запись A для домена $DOMAIN, указывающую на IP сервера"
    log_error "Без этого сертификат получить не получится"
    exit 1
fi

# Создание пробной директории для проверки
mkdir -p /usr/share/nginx/html/.well-known/acme-challenge

log_info "Запрос SSL сертификата через Let's Encrypt..."
log_info "Это может занять 1-2 минуты..."

# Первый запрос сертификата
certbot certonly --webroot -w /usr/share/nginx/html \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN

if [ $? -ne 0 ]; then
    log_error "Не удалось получить SSL сертификат"
    log_error "Проверьте:"
    log_error "  1. DNS запись A для $DOMAIN指向ет на IP этого сервера"
    log_error "  2. Порт 80 открыт (ufw allow 80/tcp)"
    log_error "  3. Интернет доступность домена"
    exit 1
fi

log_success "SSL сертификат получен!"
log_info "Сертификаты размещены в: /etc/letsencrypt/live/$DOMAIN/"

# === 12. Настройка nginx для использования сертификатов Let's Encrypt ===
log_info "Настройка nginx для использования SSL сертификатов..."

cp nginx/conf.d/$DOMAIN.conf nginx/conf.d/$DOMAIN.conf.backup

cat > nginx/conf.d/$DOMAIN.conf << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location /.well-known/acme-challenge/ {
        root /usr/share/nginx/html;
    }

    location / {
        return 302 https://\$server_name\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate /etc/letsencrypt/live/\$server_name/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/\$server_name/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;

    access_log /var/log/nginx/\$server_name.access.log;
    error_log /var/log/nginx/\$server_name.error.log;

    client_max_body_size 10M;

    location / {
        proxy_pass http://frontend:80;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

log_success "nginx настроен для использования Let's Encrypt"

# === 13. Проверка конфигурации и запуск контейнеров ===
log_info "Проверка конфигурации Docker Compose..."
docker-compose config > /dev/null

if [ $? -ne 0 ]; then
    log_error "Ошибки в docker-compose.yml"
    exit 1
fi

log_info "Запуск всех контейнеров..."
docker-compose up -d --build

if [ $? -ne 0 ]; then
    log_error "Ошибка при запуске контейнеров"
    exit 1
fi

# === 14. Ожидание запуска и проверка ===
log_info "Ожидание запуска контейнеров (30 секунд)..."
sleep 30

# Проверка статуса
log_info "Проверка статуса контейнеров..."
docker-compose ps

# Проверяем что все контейнеры запущены
RUNNING=$(docker-compose ps | grep -c "Up" || echo "0")
if [ "$RUNNING" -lt 3 ]; then
    log_warn "Не все контейнеры запустились"
    log_info "Вывод логов для диагностики:"
else
    log_success "Все контейнеры запущены!"
fi

# === 15. Настройка автоматического обновления SSL ===
log_info "Настройка автоматического обновления SSL сертификатов..."
(
    echo "# Автоматическое обновление SSL сертификатов"
    echo "0 3 * * * cd /root/telegram-app && /usr/bin/certbot renew --quiet >> /var/log/certbot.log 2>&1"
) > /etc/cron.d/certbot
chmod 644 /etc/cron.d/certbot

log_success "Автоматическое обновление SSL настроено (каждый день в 3:00)"

# === 16. Финальная информация ===
echo ""
echo "================================================"
echo -e "${GREEN}🎉 Установка завершена успешно!${NC}"
echo "================================================"
echo ""
echo "📊 Статус сервиса:"
docker-compose ps
echo ""
echo "🔗 Доступ к сервисам:"
echo "   Frontend: https://$DOMAIN"
echo "   Backend API: https://$DOMAIN/api"
echo "   Telegram Bot: используйте команду /start в боте"
echo ""
echo "📁 Полезные команды:"
echo "   Просмотр логов:    docker-compose logs -f"
echo "   Перезапуск:        docker-compose restart"
echo "   Остановка:         docker-compose down"
echo "   Пересоздание:      docker-compose up -d --build"
echo ""
echo "🔒 SSL сертификат:"
echo "   Путь: /etc/letsencrypt/live/$DOMAIN/"
echo "   Автоматическое обновление: через cron (ежедневно в 3:00)"
echo ""
echo "💡 Настройка Telegram бота:"
echo "   1. Откройте @BotFather в Telegram"
echo "   2. /mybots -> выберите бота"
echo "   3. Bot Settings -> Menu Button"
echo "   4. Configure Menu Button"
echo "   5. Введите: https://$DOMAIN"
echo "   6. Название кнопки: 'Открыть SDA'"
echo ""
echo "📋 Команды бота:"
echo "   /start - Открыть приложение"
echo "   /add - Добавить аккаунт Steam (.maFile)"
echo "   /log pass - Восстановить сохраненные логины/пароли"
echo "   /help - Справка"
echo ""
echo "🔐 Информация для восстановления:"
echo "   ENCRYPTION_KEY: $ENCRYPTION_KEY"
echo "   ⚠️ Сохраните этот ключ! Без него данные будут недоступны!"
echo ""
echo "📝 Логи:"
echo "   docker logs telegram-app-backend-1"
echo "   docker logs telegram-app-bot-1"
echo "   docker logs telegram-app-frontend-1"
echo ""
echo "================================================"
