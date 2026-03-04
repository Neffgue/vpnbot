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

echo "[2/3] Creating database tables and running migrations..."
python /app/backend/init_db.py
cd /app/backend

# Stamp current state if alembic_version table doesn't exist yet
# (tables created by init_db.py via create_all, so migrations 001 would fail with DuplicateTable)
python -c "
import psycopg2, os
url = os.environ.get('DATABASE_URL','').replace('postgresql+asyncpg://','postgresql://')
try:
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute(\"SELECT 1 FROM alembic_version LIMIT 1\")
    print('  Alembic version table exists, skipping stamp')
    conn.close()
except Exception:
    print('  Stamping alembic to head (tables already created by init_db)...')
    import subprocess, sys
    subprocess.run([sys.executable, '-m', 'alembic', 'stamp', 'head'], check=False)
" 2>/dev/null || true

alembic upgrade head || echo "  Alembic migrations warning (may already be up to date)"
cd /app

echo "[3/3] Starting Uvicorn..."
cd /app
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000 --log-level info
