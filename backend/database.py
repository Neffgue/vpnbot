"""Database module — production-grade async SQLAlchemy setup.

Ключевые исправления vs предыдущей версии:
- AsyncAdaptedQueuePool вместо QueuePool (asyncpg несовместим с обычным QueuePool!)
- pool_reset_on_return='rollback' — очищает зависшие транзакции
- get_db() теперь делает commit на выходе и rollback при ошибке
- Retry логика для временных сбоев соединения
"""
import asyncio
import logging

from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from backend.config import settings

logger = logging.getLogger(__name__)

# Base class for all models
Base = declarative_base()

# ─── Lazy engine & session factory ───────────────────────────────────────────
_engine = None
_session_factory = None


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite") or ":memory:" in url


def get_engine():
    """Получить (или создать) async движок БД."""
    global _engine
    if _engine is None:
        url = settings.DATABASE_URL
        if _is_sqlite(url):
            # SQLite (тесты) — NullPool, без connect_args
            _engine = create_async_engine(
                url,
                echo=settings.DEBUG,
                future=True,
                poolclass=NullPool,
            )
        else:
            # PostgreSQL — AsyncAdaptedQueuePool (обязателен для asyncpg!)
            # Обычный QueuePool вызывает ошибки 500 с asyncpg
            _engine = create_async_engine(
                url,
                echo=settings.DEBUG,
                future=True,
                poolclass=AsyncAdaptedQueuePool,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=1800,
                pool_pre_ping=True,
                pool_reset_on_return="rollback",  # очищает зависшие транзакции
            )
        logger.info(
            f"Database engine created: "
            f"{'SQLite' if _is_sqlite(url) else 'PostgreSQL'} | "
            f"pool={'NullPool' if _is_sqlite(url) else 'AsyncAdaptedQueuePool'}"
        )
    return _engine


def get_session_factory():
    """Получить (или создать) фабрику сессий."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


# Совместимость — переменные модуля (тесты могут переопределять)
engine = None
AsyncSessionLocal = None


# ─── Retry logic ─────────────────────────────────────────────────────────────
_RETRYABLE = (OperationalError, InterfaceError, ConnectionRefusedError, OSError, TimeoutError)


async def _execute_with_retry(coro_factory, attempts: int = 3, delay: float = 0.5):
    """Выполнить async-функцию с retry при временных сбоях БД."""
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return await coro_factory()
        except _RETRYABLE as e:
            last_exc = e
            if attempt < attempts:
                logger.warning(
                    f"DB transient error (attempt {attempt}/{attempts}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
                delay *= 2.0
            else:
                logger.error(f"DB error: all {attempts} attempts exhausted. Last: {e}")
    raise last_exc


# ─── FastAPI dependency ───────────────────────────────────────────────────────

async def get_db():
    """FastAPI dependency для получения сессии БД.

    - commit при успешном завершении
    - rollback при исключении
    - close в любом случае (finally)
    """
    factory = AsyncSessionLocal if AsyncSessionLocal is not None else get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ─── DB init ─────────────────────────────────────────────────────────────────

async def init_db():
    """Создание таблиц (только для разработки без Alembic)."""
    eng = engine if engine is not None else get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
