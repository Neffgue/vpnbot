"""
Конфигурация тестов и фикстуры для VPN Sales System.
Использует SQLite в памяти для изоляции тестов.
"""
import os
import pytest
import pytest_asyncio

# Патчим переменные окружения ДО импорта приложения
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("BOT_TOKEN", "1234567890:test_token")
os.environ.setdefault("VPN_MOCK_MODE", "true")
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "1234567890:test_token")

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Создаём все таблицы один раз за сессию."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    """Транзакционная DB-сессия на каждый тест — откатывается после."""
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def client(db_session):
    """HTTPX async клиент с FastAPI app, переопределяет зависимость DB."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def registered_user(client):
    """Зарегистрированный тестовый пользователь."""
    resp = await client.post("/api/v1/users/register", json={
        "telegram_id": 111222333,
        "username": "test_user",
        "first_name": "Иван",
    })
    assert resp.status_code == 200
    return resp.json()


@pytest_asyncio.fixture
async def admin_token(db_session):
    """JWT-токен для администратора."""
    from backend.services.user_service import UserService
    from backend.utils.security import create_access_token

    service = UserService(db_session)
    admin = await service.create_user(
        telegram_id=999999999,
        username="admin",
        first_name="Админ",
    )
    await service.repo.update(admin.id, {"is_admin": True})
    await db_session.commit()
    token = create_access_token({"sub": admin.id})
    return token


@pytest_asyncio.fixture
async def admin_client(db_session, admin_token):
    """HTTPX клиент с токеном администратора."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {admin_token}"},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
