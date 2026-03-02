#!/bin/bash
set -e

echo "========================================="
echo " VPN Sales System — Backend Starting"
echo "========================================="

echo "[1/3] Waiting for PostgreSQL..."
until python -c "
import asyncio, asyncpg, os, sys
async def check():
    url = os.environ.get('DATABASE_URL','').replace('postgresql+asyncpg','postgresql').replace('postgresql+psycopg2','postgresql')
    try:
        conn = await asyncpg.connect(url)
        await conn.close()
    except Exception as e:
        sys.exit(1)
asyncio.run(check())
" 2>/dev/null; do
    echo "  PostgreSQL not ready, retrying in 2s..."
    sleep 2
done
echo "  PostgreSQL is ready!"

echo "[2/3] Creating database tables..."
python /app/backend/init_db.py

echo "[3/3] Starting Uvicorn..."
cd /app
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000 --log-level info
