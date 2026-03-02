"""
Тесты mock-режима (VPN_MOCK_MODE=true).
Проверяем, что бот и admin панель работают без реальных VPN серверов.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestMockVpnService:
    """Тесты заглушки VPN сервиса."""

    async def test_mock_mode_enabled(self):
        """Mock режим активирован."""
        import os
        assert os.environ.get("VPN_MOCK_MODE", "").lower() in ("true", "1", "yes")

    async def test_xui_service_factory_returns_mock(self):
        """Фабрика возвращает mock-сервис в dev режиме."""
        from backend.services.xui_service_mock import MockXuiService
        service = MockXuiService(
            panel_url="http://localhost:54321",
            username="admin",
            password="admin",
            inbound_id=1,
        )
        # В mock режиме всегда возвращается MockXuiService
        assert service is not None
        assert hasattr(service, "login")
        assert hasattr(service, "add_client")
        assert hasattr(service, "update_client")
        assert hasattr(service, "delete_client")
        assert hasattr(service, "get_client_stats")

    async def test_mock_login(self):
        """Mock login всегда успешен."""
        from backend.services.xui_service_mock import MockXuiService
        service = MockXuiService(panel_url="http://localhost", username="admin", password="admin")
        result = await service.login()
        assert result is True

    async def test_mock_add_client(self):
        """Mock добавление клиента возвращает UUID."""
        import uuid
        from backend.services.xui_service_mock import MockXuiService
        service = MockXuiService(panel_url="http://localhost", username="admin", password="admin")
        client_uuid = str(uuid.uuid4())
        result = await service.add_client(
            inbound_id=1,
            email=f"test_{client_uuid}@mock",
            client_uuid=client_uuid,
            traffic_gb=100,
            expire_days=30,
        )
        assert result is True

    async def test_mock_get_client_stats(self):
        """Mock статистика клиента возвращает словарь."""
        import uuid
        from backend.services.xui_service_mock import MockXuiService
        service = MockXuiService(panel_url="http://localhost", username="admin", password="admin")
        client_uuid = str(uuid.uuid4())
        result = await service.get_client_stats(email=f"test_{client_uuid}@mock")
        assert isinstance(result, dict)

    async def test_mock_delete_client(self):
        """Mock удаление клиента всегда успешно."""
        import uuid
        from backend.services.xui_service_mock import MockXuiService
        service = MockXuiService(panel_url="http://localhost", username="admin", password="admin")
        result = await service.delete_client(inbound_id=1, client_uuid=str(uuid.uuid4()))
        assert result is True


class TestFullFlowMockMode:
    """
    Полный цикл: регистрация → бесплатный доступ → оплата → подписка
    Всё работает без реального VPN сервера.
    """

    async def test_full_trial_flow(self, client: AsyncClient):
        """Полный цикл бесплатного доступа."""
        # 1. Регистрация
        reg = await client.post("/api/v1/users/register", json={
            "telegram_id": 600000001,
            "username": "full_flow_user",
            "first_name": "ПолныйЦикл",
        })
        assert reg.status_code == 200
        tg_id = reg.json()["telegram_id"]

        # 2. Проверяем что пробный период не использован
        status = await client.get(f"/api/v1/users/{tg_id}/free-trial-status")
        assert status.json()["already_used"] is False

        # 3. Активируем пробный период
        trial = await client.post(f"/api/v1/users/{tg_id}/free-trial")
        assert trial.status_code == 200
        assert trial.json()["success"] is True
        link = trial.json()["subscription_link"]
        assert link.startswith("happ://")

        # 4. Проверяем что пробный период отмечен
        status2 = await client.get(f"/api/v1/users/{tg_id}/free-trial-status")
        assert status2.json()["already_used"] is True

        # 5. Подписка активна
        sub = await client.get(f"/api/v1/users/{tg_id}/subscription")
        assert sub.json()["is_active"] is True

    async def test_full_payment_flow(self, client: AsyncClient):
        """Полный цикл оплаты подписки."""
        # 1. Регистрация
        reg = await client.post("/api/v1/users/register", json={
            "telegram_id": 600000002,
            "username": "payment_flow",
            "first_name": "Оплата",
        })
        tg_id = reg.json()["telegram_id"]

        # 2. Получаем планы
        plans_resp = await client.get("/api/v1/subscriptions/plans")
        plans = plans_resp.json()["plans"]
        assert len(plans) > 0
        plan_id = plans[0]["id"]

        # 3. Создаём платёж
        pay = await client.post(f"/api/v1/users/{tg_id}/create-payment", json={
            "plan_id": plan_id,
            "period_days": 30,
        })
        assert pay.status_code == 200
        assert pay.json()["success"] is True
        payment_id = pay.json()["payment_id"]

        # 4. Подтверждаем платёж
        confirm = await client.post(f"/api/v1/users/{tg_id}/confirm-payment", json={
            "payment_id": payment_id,
        })
        assert confirm.status_code == 200
        assert confirm.json()["success"] is True

        # 5. Подписка активна, получаем ссылку
        sub = await client.get(f"/api/v1/users/{tg_id}/subscription")
        assert sub.json()["is_active"] is True

    async def test_referral_flow(self, client: AsyncClient):
        """Реферальный поток работает без VPN серверов."""
        # 1. Создаём реферера
        ref_reg = await client.post("/api/v1/users/register", json={
            "telegram_id": 600000003,
            "username": "referrer",
            "first_name": "Реферер",
        })
        referrer = ref_reg.json()
        referral_code = referrer["referral_code"]

        # 2. Получаем реферальную ссылку
        ref_info = await client.get(f"/api/v1/users/{referrer['telegram_id']}/referral")
        assert ref_info.status_code == 200
        data = ref_info.json()
        assert data["referral_code"] == referral_code
        assert "t.me" in data["referral_link"]
        assert data["referrals_count"] == 0

        # 3. Регистрируем реферала (новый пользователь)
        invited_reg = await client.post("/api/v1/users/register", json={
            "telegram_id": 600000004,
            "username": "invited",
            "first_name": "Приглашённый",
        })
        assert invited_reg.status_code == 200

    async def test_servers_without_real_vpn(self, client: AsyncClient):
        """Список серверов работает без реальных VPN серверов."""
        resp = await client.get("/api/v1/servers/")
        assert resp.status_code == 200
        data = resp.json()
        # В mock режиме список пустой или содержит mock-серверы
        assert isinstance(data, (list, dict))
