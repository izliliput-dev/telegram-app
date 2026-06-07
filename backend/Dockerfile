FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY . .

# Создание папки для хранилища
RUN mkdir -p storage/mafiles

# Экспортируем порт
EXPOSE 8000

# Запуск backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
