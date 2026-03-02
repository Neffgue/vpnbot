"""
Тесты работоспособности приложения (health check, роутинг, CORS).
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestHealthCheck:
    """Тесты health check эндпоинта."""

    async def test_health_returns_200(self, client: AsyncClient):
        """Health check возвращает 200."""
        resp = await client.get("/health")
        assert resp.status_code == 200

    async def test_health_returns_ok_status(self, client: AsyncClient):
        """Health check возвращает статус ok."""
        resp = await client.get("/health")
        data = resp.json()
        assert data.get("status") == "ok" or data.get("status") == "healthy"

    async def test_root_endpoint(self, client: AsyncClient):
        """Корневой эндпоинт возвращает 200."""
        resp = await client.get("/")
        assert resp.status_code == 200

    async def test_api_v1_exists(self, client: AsyncClient):
        """API v1 роутер подключен."""
        resp = await client.get("/api/v1/subscriptions/plans")
        assert resp.status_code == 200

    async def test_docs_available(self, client: AsyncClient):
        """OpenAPI документация доступна."""
        resp = await client.get("/docs")
        assert resp.status_code == 200


class TestRoutingOrder:
    """Тесты порядка маршрутов (статические vs динамические)."""

    async def test_register_not_matched_as_user_id(self, client: AsyncClient):
        """
        Маршрут /users/register не должен перехватываться /{user_id}.
        Проверяем что POST /register возвращает не 404.
        """
        resp = await client.post("/api/v1/users/register", json={
            "telegram_id": 500000001, "username": "route_test", "first_name": "Маршрут"
        })
        # Должен обработаться как register, не как get_user(user_id="register")
        assert resp.status_code == 200
        assert "telegram_id" in resp.json()

    async def test_by_referral_not_matched_as_user_id(self, client: AsyncClient):
        """
        GET /users/by-referral/CODE не перехватывается /{user_id}.
        """
        resp = await client.get("/api/v1/users/by-referral/NONEXISTENT_CODE")
        # Должен вернуть 404 "User not found", не 404 "Not Found" от неверного маршрута
        assert resp.status_code == 404
        assert "not found" in resp.json().get("detail", "").lower()

    async def test_plans_not_matched_as_subscription_id(self, client: AsyncClient):
        """
        GET /subscriptions/plans не перехватывается /{id}.
        """
        resp = await client.get("/api/v1/subscriptions/plans")
        assert resp.status_code == 200
        assert "plans" in resp.json()
