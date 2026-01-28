# =============================================================================
# DOCKERFILE FOR DJANGO BACKEND
# Production-ready with Gunicorn
# =============================================================================
FROM python:3.11-slim

# Установка переменных окружения
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PORT=8000

# Установка рабочей директории
WORKDIR /app

# Установка зависимостей системы
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Копирование и установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание директории для медиа файлов и статики
RUN mkdir -p /app/media /app/staticfiles

# Сбор статики при сборке образа
RUN python manage.py collectstatic --noinput --clear || true

# Открытие порта
EXPOSE 8000

# Команда запуска - использует PORT из env (Render/Railway передают свой порт)
CMD python manage.py migrate --noinput && gunicorn marsdevs.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120
