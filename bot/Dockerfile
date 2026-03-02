FROM python:3.11-slim

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Зависимости
COPY bot/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --timeout=300 --retries=5 -r /tmp/requirements.txt

# PYTHONPATH
ENV PYTHONPATH=/app

# Код бота
COPY bot/ /app/bot/

# Запуск — ждёт backend через python, затем запускает бота
CMD ["python", "-m", "bot.main"]
