import logging
import os
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.database import Base, get_engine
from backend.api.v1.router import api_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager — startup и shutdown."""
    logger.info("Starting VPN Sales System API")
    eng = get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")

    # Загружаем BOT_TOKEN из БД при старте, если он не задан в env
    if not os.getenv("BOT_TOKEN") and not os.getenv("TELEGRAM_BOT_TOKEN"):
        try:
            from sqlalchemy.ext.asyncio import AsyncSession
            from sqlalchemy import select
            from backend.models.config import BotText
            async with AsyncSession(eng) as session:
                stmt = select(BotText).where(BotText.key == "system_settings_json")
                result = await session.execute(stmt)
                row = result.scalars().first()
                if row:
                    import json
                    data = json.loads(row.value)
                    token = data.get("bot_token", "")
                    if token:
                        os.environ["BOT_TOKEN"] = token
                        os.environ["TELEGRAM_BOT_TOKEN"] = token
                        logger.info("BOT_TOKEN loaded from DB on startup")
        except Exception as e:
            logger.warning(f"Could not load BOT_TOKEN from DB on startup: {e}")

    yield
    logger.info("Shutting down VPN Sales System API")
    await eng.dispose()


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="VPN Sales System Backend API",
    lifespan=lifespan,
    servers=[{"url": "/", "description": "Production"}],
)


# ── Global Exception Handler ─────────────────────────────────────
# Catches ALL unhandled exceptions — logs full traceback, returns readable JSON.
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}\n{tb}"
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc),
            "path": str(request.url.path),
        },
    )

# CORS — разрешаем admin-panel на localhost и production
allowed_origins = getattr(settings, "ALLOWED_ORIGINS", ["*"])
if isinstance(allowed_origins, str):
    allowed_origins = [o.strip() for o in allowed_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Определяем корень проекта — папка vpnbot
# При запуске через uWSGI __file__ = /home/neffgue313/vpnbot/backend/main.py
# поэтому идём на 2 уровня вверх: backend → vpnbot
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))  # .../vpnbot/backend
_ROOT_DIR = os.path.dirname(_BACKEND_DIR)                  # .../vpnbot

# Статические файлы (загруженные изображения для бота)
ROOT_STATIC_DIR = os.path.join(_ROOT_DIR, "static")
STATIC_DIR = ROOT_STATIC_DIR if os.path.isdir(ROOT_STATIC_DIR) else os.path.join(_BACKEND_DIR, "static")
os.makedirs(os.path.join(STATIC_DIR, "uploads"), exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Admin panel — собранные файлы React (npm run build → admin-panel/dist/)
ADMIN_DIR = os.path.join(_ROOT_DIR, "admin-panel", "dist")
if os.path.isdir(ADMIN_DIR):
    app.mount("/admin", StaticFiles(directory=ADMIN_DIR, html=True), name="admin")
    logger.info(f"Admin panel mounted at /admin from {ADMIN_DIR}")
else:
    logger.warning(f"Admin panel dist not found at {ADMIN_DIR}, skipping mount")

# API роутер
app.include_router(api_router)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Return empty favicon to suppress 404 errors in browser console."""
    from fastapi.responses import Response
    return Response(content=b"", media_type="image/x-icon")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "vpn-sales-api", "version": "1.0.0"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "VPN Sales System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )

# WSGI-обёртка для AlwaysData (uWSGI не поддерживает ASGI напрямую)
# В панели AlwaysData (Web → Sites) указывай: backend.main:wsgi_app
# Working directory: /home/neffgue313/vpnbot
try:
    from a2wsgi import ASGIMiddleware
    wsgi_app = ASGIMiddleware(app)
except ImportError:
    wsgi_app = None
