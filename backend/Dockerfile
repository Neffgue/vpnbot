FROM python:3.11-slim

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем зависимости
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --timeout=300 --retries=5 -r /tmp/requirements.txt

# Копируем весь проект (нужен backend/ как пакет)
COPY backend/ /app/backend/
COPY backend/alembic.ini /app/alembic.ini

# Создаём папку для статики
RUN mkdir -p /app/static/uploads

# PYTHONPATH чтобы uvicorn нашёл backend.main
ENV PYTHONPATH=/app

# Entrypoint
COPY backend/entrypoint.sh /entrypoint.sh
COPY backend/init_db.py /app/backend/init_db.py
RUN sed -i 's/\r//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
