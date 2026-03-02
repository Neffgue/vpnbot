"""
Тесты для API подписок (/api/v1/subscriptions/...)
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestSubscriptionPlans:
    """Тесты получения тарифных планов."""

    async def test_get_plans_returns_list(self, client: AsyncClient):
        """Список планов возвращается корректно."""
        resp = await client.get("/api/v1/subscriptions/plans")
        assert resp.status_code == 200
        data = resp.json()
        assert "plans" in data
        assert isinstance(data["plans"], list)
        assert len(data["plans"]) >= 2  # Solo и Family минимум

    async def test_plans_have_required_fields(self, client: AsyncClient):
        """Каждый план содержит обязательные поля."""
        resp = await client.get("/api/v1/subscriptions/plans")
        plans = resp.json()["plans"]
        for plan in plans:
            assert "id" in plan
            assert "name" in plan
            assert "price" in plan

    async def test_plans_include_solo_and_family(self, client: AsyncClient):
        """Планы включают Solo и Family."""
        resp = await client.get("/api/v1/subscriptions/plans")
        names = [p["name"] for p in resp.json()["plans"]]
        assert "Solo" in names
        assert "Family" in names

    async def test_solo_plan_has_periods(self, client: AsyncClient):
        """У Solo плана есть периоды подписки."""
        resp = await client.get("/api/v1/subscriptions/plans")
        plans = resp.json()["plans"]
        solo = next(p for p in plans if p["name"] == "Solo")
        assert "periods" in solo
        # Ожидаем как минимум один период
        assert isinstance(solo["periods"], list)
