from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import declarative_base

from backend.config import settings

# Base class for all models — создаётся всегда
Base = declarative_base()

# Движок и сессия создаются лениво через get_engine()
# чтобы тесты могли подменить DATABASE_URL до первого использования
_engine = None
_session_factory = None


def get_engine():
    """Получить (или создать) async движок БД."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            future=True,
            pool_pre_ping=True,
            poolclass=NullPool,
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


# Совместимость — engine и AsyncSessionLocal как свойства модуля
# Тесты могут напрямую переустановить эти переменные
engine = None           # будет инициализирован при первом вызове get_engine()
AsyncSessionLocal = None  # будет инициализирован при первом вызове get_session_factory()


async def get_db():
    """Dependency для получения сессии БД (используется в FastAPI)."""
    # Используем модульные переменные если они переопределены (для тестов)
    factory = AsyncSessionLocal if AsyncSessionLocal is not None else get_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Инициализация БД: создание таблиц (только для разработки)."""
    eng = engine if engine is not None else get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
