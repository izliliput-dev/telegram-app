# 🛡️ SDA Telegram App

**Steam Desktop Authenticator** в формате Telegram Web App — управляйте аккаунтами Steam прямо в Telegram!

---

## 📋 Возможности

| Функция | Описание |
|---------|----------|
| 🔑 **2FA коды** | Генерация кодов Steam Guard каждые 30 секунд |
| ✅ **Подтверждения** | Принятие/отклонение торговых подтверждений |
| 🤝 **Трейды** | Управление торговыми предложениями |
| 🎁 **Авто-принятие** | Автоматическое принятие подарочных трейдов |
| 🔐 **Безопасность** | AES-256 шифрование всех данных |
| 📱 **Мультиаккаунт** | Поддержка неограниченного количества аккаунтов |

---

## 🚀 Быстрый старт

### 1. Получение токена бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Сохраните полученный токен

### 2. Настройка проекта

```bash
cd telegram-app/backend
cp .env.example .env
```

Отредактируйте `.env`:
```env
TELEGRAM_BOT_TOKEN=ваш_токен_от_botfather
WEB_APP_URL=https://your-domain.com
ENCRYPTION_KEY=ваш-секретный-ключ-минимум-32-символа
```

### 3. Запуск через Docker

```bash
cd telegram-app
docker-compose up -d
```

### 4. Настройка Web App

1. Откройте @BotFather
2. Отправьте `/mybots` → выберите вашего бота
3. **Bot Settings** → **Menu Button** → **Configure Menu Button**
4. Отправьте URL вашего приложения: `https://your-domain.com`
5. Введите название кнопки: "Открыть SDA"

### 5. Готово!

Откройте вашего бота и нажмите кнопку **"Открыть SDA"**

---

## 📁 Структура проекта

```
telegram-app/
├── backend/
│   ├── main.py              # FastAPI приложение
│   ├── bot.py               # Telegram бот
│   ├── config.py            # Конфигурация
│   ├── models.py            # Pydantic модели
│   ├── lib/
│   │   ├── steam_utils.py   # 2FA, подтверждения
│   │   ├── trade_manager.py # Управление трейдами
│   │   ├── refresh_account.py # Обновление сессии
│   │   └── crypto_manager.py # Шифрование
│   ├── storage/             # Хранилище данных
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── CodeGenerator.tsx
│   │   │   ├── AccountSwitcher.tsx
│   │   │   ├── Confirmations.tsx
│   │   │   └── Trades.tsx
│   │   ├── api/
│   │   │   └── api.ts
│   │   ├── utils/
│   │   │   └── steamGuard.ts
│   │   ├── App.tsx
│   │   └── index.tsx
│   ├── public/
│   │   └── index.html
│   ├── package.json
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 🔧 Локальная разработка

### Backend

```bash
cd telegram-app/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Копирование .env и настройка
cp .env.example .env
# Отредактируйте .env

# Запуск
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd telegram-app/frontend
npm install

# Запуск (прокси на backend)
npm start
```

### Telegram бот

```bash
cd telegram-app/backend
source venv/bin/activate
python bot.py
```

---

## 🌐 Развёртывание на сервере

### Требования

- Docker и Docker Compose
- Домен с HTTPS (обязательно для Telegram Web App)
- Сервер с минимум 512MB RAM

### 1. Подготовка сервера

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Настройка проекта

```bash
git clone <your-repo>
cd telegram-app
cp backend/.env.example backend/.env
```

Отредактируйте `backend/.env`:
```env
TELEGRAM_BOT_TOKEN=ваш_токен
WEB_APP_URL=https://your-domain.com
ENCRYPTION_KEY=очень-длинный-секретный-ключ
```

### 3. HTTPS через Nginx Proxy Manager (рекомендуется)

Установите Nginx Proxy Manager для управления SSL:

```bash
docker run -d \
  -p 80:80 -p 443:443 -p 81:81 \
  -v nginx_pma_data:/data \
  -v nginx_pma_ssl:/etc/letsencrypt \
  --name nginx-proxy-manager \
  jc21/nginx-proxy-manager
```

Затем:
1. Откройте `http://your-server-ip:81`
2. Создайте новый Proxy Host
3. Domain: `your-domain.com`
4. Forward Host: `your-server-ip`
5. Forward Port: `3000`
6. Включите SSL и запросите сертификат

### 4. Запуск

```bash
docker-compose up -d
```

### 5. Проверка

```bash
docker-compose ps
docker-compose logs -f
```

---

## 📡 API Reference

### Accounts

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/accounts` | Список аккаунтов |
| POST | `/api/accounts` | Добавить аккаунт |
| GET | `/api/accounts/{id}` | Данные аккаунта |
| DELETE | `/api/accounts/{id}` | Удалить аккаунт |

### 2FA Codes

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/accounts/{id}/code` | Получить 2FA код |

### Confirmations

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/accounts/{id}/confirmations` | Список подтверждений |
| POST | `/api/accounts/{id}/confirmations/action` | Принять/отклонить |

### Trades

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/accounts/{id}/trades` | Список трейдов |
| POST | `/api/accounts/{id}/trades/action` | Управление трейдом |
| POST | `/api/accounts/{id}/trades/auto-accept` | Авто-принятие |

---

## 🔐 Безопасность

### Что шифруется:
- ✅ Все `.maFile` файлы (AES-256)
- ✅ Учётные данные Steam
- ✅ Сессионные токены

### Рекомендации:
- ⚠️ Используйте надёжный `ENCRYPTION_KEY` (минимум 32 символа)
- ⚠️ Храните резервные копии хранилища
- ⚠️ Не передавайте `.env` файл
- ⚠️ Используйте HTTPS для Web App

---

## ⚙️ Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather | - |
| `WEB_APP_URL` | URL вашего Web App | `http://localhost` |
| `ENCRYPTION_KEY` | Ключ шифрования | `change-this-secret-key...` |
| `STORAGE_PATH` | Путь к хранилищу | `./storage` |
| `PORT` | Порт backend | `8000` |
| `REACT_APP_API_URL` | URL API для frontend | `http://localhost:8000` |

---

## ❓ FAQ

### Q: Как добавить аккаунт?
**A:** Функция добавления аккаунтов в разработке. Временно используйте API напрямую.

### Q: Где хранятся данные?
**A:** В папке `backend/storage/` в зашифрованном виде.

### Q: Можно ли использовать без Docker?
**A:** Да, см. раздел "Локальная разработка".

### Q: Код 2FA не работает?
**A:** Проверьте синхронизацию времени. Приложение автоматически синхронизируется с сервером Steam.

### Q: Как перенести аккаунты?
**A:** Скопируйте папку `backend/storage/` на новый сервер.

---

## 🛠️ Технологии

| Компонент | Технология |
|-----------|------------|
| **Backend** | Python 3.11, FastAPI |
| **Frontend** | React 18, TypeScript |
| **Telegram** | WebApp SDK, Bot API |
| **Шифрование** | Cryptography (AES-256) |
| **Контейнеры** | Docker, Docker Compose |

---

## 📝 Лицензия

MIT License

---

## 🤝 Поддержка

При возникновении проблем:
1. Проверьте логи: `docker-compose logs -f`
2. Убедитесь, что все переменные окружения настроены
3. Проверьте доступность HTTPS для Web App

---

**SDA Telegram App** — современный Steam Authenticator в вашем Telegram! 🚀
