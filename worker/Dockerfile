FROM python:3.11-slim

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Зависимости
COPY worker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --timeout=300 --retries=5 -r /tmp/requirements.txt

# PYTHONPATH
ENV PYTHONPATH=/app

# Код worker и backend (нужен для моделей/сервисов)
COPY worker/ /app/worker/
COPY backend/ /app/backend/

# Запуск Celery worker по умолчанию
CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info"]
