"""
Тесты для admin API (/api/v1/admin/...)
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestAdminAuth:
    """Тесты авторизации в admin панели."""

    async def test_admin_stats_without_token(self, client: AsyncClient):
        """Запрос без токена — 401 или 403."""
        resp = await client.get("/api/v1/admin/stats")
        assert resp.status_code in (401, 403)

    async def test_admin_stats_with_valid_token(self, admin_client: AsyncClient):
        """С корректным токеном — 200."""
        resp = await admin_client.get("/api/v1/admin/stats")
        assert resp.status_code == 200

    async def test_admin_users_without_token(self, client: AsyncClient):
        """Список пользователей без токена — 401 или 403."""
        resp = await client.get("/api/v1/admin/users")
        assert resp.status_code in (401, 403)


class TestAdminStats:
    """Тесты статистики."""

    async def test_stats_structure(self, admin_client: AsyncClient):
        """Статистика содержит ожидаемые поля."""
        resp = await admin_client.get("/api/v1/admin/stats")
        assert resp.status_code == 200
        data = resp.json()
        # Минимально ожидаемые поля статистики
        assert "total_users" in data or "users" in data or "stats" in data


class TestAdminUsers:
    """Тесты управления пользователями через admin API."""

    async def test_get_users_list(self, admin_client: AsyncClient, registered_user):
        """Список пользователей возвращается."""
        resp = await admin_client.get("/api/v1/admin/users")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict))

    async def test_ban_user(self, admin_client: AsyncClient, client: AsyncClient):
        """Бан пользователя работает."""
        # Регистрируем нового пользователя
        reg = await client.post("/api/v1/users/register", json={
            "telegram_id": 400000001, "username": "ban_target", "first_name": "Жертва"
        })
        user_id = reg.json()["id"]

        resp = await admin_client.post(f"/api/v1/admin/users/{user_id}/ban", json={
            "user_id": user_id, "is_banned": True
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("is_banned") is True or data.get("success") is True

    async def test_unban_user(self, admin_client: AsyncClient, client: AsyncClient):
        """Разбан пользователя работает."""
        reg = await client.post("/api/v1/users/register", json={
            "telegram_id": 400000002, "username": "unban_target", "first_name": "Жертва2"
        })
        user_id = reg.json()["id"]

        # Сначала баним
        await admin_client.post(f"/api/v1/admin/users/{user_id}/ban", json={
            "user_id": user_id, "is_banned": True
        })
        # Затем разбаниваем
        resp = await admin_client.post(f"/api/v1/admin/users/{user_id}/unban")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("is_banned") is False or data.get("success") is True

    async def test_ban_nonexistent_user(self, admin_client: AsyncClient):
        """Бан несуществующего пользователя — 404."""
        resp = await admin_client.post(
            "/api/v1/admin/users/00000000-0000-0000-0000-000000000000/ban",
            json={"user_id": "00000000-0000-0000-0000-000000000000", "is_banned": True}
        )
        assert resp.status_code == 404


class TestAdminBroadcast:
    """Тесты рассылки сообщений."""

    async def test_broadcast_success(self, admin_client: AsyncClient):
        """Рассылка отправляется успешно (с пустым списком пользователей — sent_count=0)."""
        # In tests no real users exist and BOT_TOKEN is a fake test token.
        # Broadcast to empty user list should return success with sent_count=0.
        resp = await admin_client.post("/api/v1/admin/broadcast", json={
            "message": "Тестовое сообщение для всех пользователей",
            "user_ids": []  # empty list → no real Telegram calls
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert "sent_count" in data

    async def test_broadcast_without_token(self, client: AsyncClient):
        """Рассылка без токена — 401 или 403."""
        resp = await client.post("/api/v1/admin/broadcast", json={
            "message": "Нельзя"
        })
        assert resp.status_code in (401, 403)

    async def test_broadcast_create(self, admin_client: AsyncClient):
        """Создание записи рассылки в БД работает."""
        resp = await admin_client.post("/api/v1/admin/broadcasts", json={
            "message": "Тестовая рассылка"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert "broadcast_id" in data


class TestAdminSettings:
    """Тесты системных настроек."""

    async def test_get_system_settings(self, admin_client: AsyncClient):
        """Получение системных настроек работает."""
        resp = await admin_client.get("/api/v1/admin/system-settings")
        assert resp.status_code == 200
        data = resp.json()
        assert "bot_token" in data
        assert "webhook_url" in data
        assert "min_withdrawal" in data
        assert "max_daily_withdrawal" in data
        assert "referral_percent" in data

    async def test_update_system_settings(self, admin_client: AsyncClient):
        """Обновление системных настроек работает."""
        resp = await admin_client.put("/api/v1/admin/system-settings", json={
            "bot_token": "9999999999:AAtest_token_for_testing",
            "min_withdrawal": 50,
            "referral_percent": 15.0
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("bot_token") == "9999999999:AAtest_token_for_testing"
        assert data.get("min_withdrawal") == 50
        assert data.get("referral_percent") == 15.0

    async def test_system_settings_without_token(self, client: AsyncClient):
        """Системные настройки без токена — 401 или 403."""
        resp = await client.get("/api/v1/admin/system-settings")
        assert resp.status_code in (401, 403)

    async def test_get_bot_settings(self, admin_client: AsyncClient):
        """Получение настроек бота (bot_settings_json) работает."""
        resp = await admin_client.get("/api/v1/admin/settings")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    async def test_update_bot_settings(self, admin_client: AsyncClient):
        """Обновление настроек бота работает."""
        resp = await admin_client.put("/api/v1/admin/settings", json={
            "support_username": "test_support",
            "channel_username": "test_channel",
            "trial_hours": 48
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
