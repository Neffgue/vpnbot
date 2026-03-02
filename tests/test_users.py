"""
Тесты для API пользователей (/api/v1/users/...)
"""
import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


class TestRegisterUser:
    """Тесты регистрации пользователя."""

    async def test_register_new_user(self, client: AsyncClient):
        """Новый пользователь успешно регистрируется."""
        resp = await client.post("/api/v1/users/register", json={
            "telegram_id": 100000001,
            "username": "testuser",
            "first_name": "Тест",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["telegram_id"] == 100000001
        assert data["username"] == "testuser"
        assert data["first_name"] == "Тест"
        assert "referral_code" in data
        assert data["is_banned"] is False
        assert data["free_trial_used"] is False

    async def test_register_same_user_twice(self, client: AsyncClient):
        """Повторная регистрация возвращает того же пользователя."""
        payload = {"telegram_id": 100000002, "username": "user2", "first_name": "Два"}
        resp1 = await client.post("/api/v1/users/register", json=payload)
        resp2 = await client.post("/api/v1/users/register", json=payload)
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["id"] == resp2.json()["id"]

    async def test_register_without_telegram_id(self, client: AsyncClient):
        """Регистрация без telegram_id возвращает 400."""
        resp = await client.post("/api/v1/users/register", json={"username": "nouid"})
        assert resp.status_code == 400

    async def test_register_generates_referral_code(self, client: AsyncClient):
        """Реферальный код уникален для каждого пользователя."""
        resp1 = await client.post("/api/v1/users/register", json={
            "telegram_id": 100000003, "username": "u3", "first_name": "Три"
        })
        resp2 = await client.post("/api/v1/users/register", json={
            "telegram_id": 100000004, "username": "u4", "first_name": "Четыре"
        })
        assert resp1.json()["referral_code"] != resp2.json()["referral_code"]


class TestGetUser:
    """Тесты получения пользователя."""

    async def test_get_user_by_telegram_id(self, client: AsyncClient, registered_user):
        """Пользователь находится по telegram_id."""
        tg_id = registered_user["telegram_id"]
        resp = await client.get(f"/api/v1/users/{tg_id}")
        assert resp.status_code == 200
        assert resp.json()["telegram_id"] == tg_id

    async def test_get_user_by_uuid(self, client: AsyncClient, registered_user):
        """Пользователь находится по внутреннему UUID."""
        uid = registered_user["id"]
        resp = await client.get(f"/api/v1/users/{uid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == uid

    async def test_get_nonexistent_user(self, client: AsyncClient):
        """Несуществующий пользователь — 404."""
        resp = await client.get("/api/v1/users/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    async def test_get_user_by_referral_code(self, client: AsyncClient, registered_user):
        """Пользователь находится по реферальному коду."""
        code = registered_user["referral_code"]
        resp = await client.get(f"/api/v1/users/by-referral/{code}")
        assert resp.status_code == 200
        assert resp.json()["referral_code"] == code


class TestBanStatus:
    """Тесты проверки блокировки."""

    async def test_ban_status_not_banned(self, client: AsyncClient, registered_user):
        """Незаблокированный пользователь — is_banned=False."""
        tg_id = registered_user["telegram_id"]
        resp = await client.get(f"/api/v1/users/{tg_id}/ban-status")
        assert resp.status_code == 200
        assert resp.json()["is_banned"] is False

    async def test_ban_status_nonexistent_user(self, client: AsyncClient):
        """Несуществующий пользователь — возвращает is_banned=False (не ошибку)."""
        resp = await client.get("/api/v1/users/9999999999/ban-status")
        assert resp.status_code == 200
        assert resp.json()["is_banned"] is False


class TestFreeTrial:
    """Тесты бесплатного доступа."""

    async def test_free_trial_status_unused(self, client: AsyncClient, registered_user):
        """Новый пользователь ещё не использовал пробный период."""
        tg_id = registered_user["telegram_id"]
        resp = await client.get(f"/api/v1/users/{tg_id}/free-trial-status")
        assert resp.status_code == 200
        assert resp.json()["already_used"] is False

    async def test_activate_free_trial(self, client: AsyncClient):
        """Активация пробного периода успешна."""
        # Регистрируем нового пользователя
        reg = await client.post("/api/v1/users/register", json={
            "telegram_id": 200000001, "username": "trial_user", "first_name": "Триал"
        })
        tg_id = reg.json()["telegram_id"]

        resp = await client.post(f"/api/v1/users/{tg_id}/free-trial")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "subscription_link" in data
        assert data["subscription_link"].startswith("happ://")
        assert "expires_at" in data

    async def test_activate_free_trial_twice_fails(self, client: AsyncClient):
        """Повторная активация пробного периода — возвращает ошибку."""
        reg = await client.post("/api/v1/users/register", json={
            "telegram_id": 200000002, "username": "trial2", "first_name": "Триал2"
        })
        tg_id = reg.json()["telegram_id"]

        await client.post(f"/api/v1/users/{tg_id}/free-trial")
        resp = await client.post(f"/api/v1/users/{tg_id}/free-trial")

        assert resp.status_code == 200
        assert resp.json()["success"] is False
        assert "ошибка" in resp.json()["error"].lower() or "использован" in resp.json()["error"].lower()

    async def test_free_trial_marks_used(self, client: AsyncClient):
        """После активации пробного периода флаг already_used=True."""
        reg = await client.post("/api/v1/users/register", json={
            "telegram_id": 200000003, "username": "trial3", "first_name": "Триал3"
        })
        tg_id = reg.json()["telegram_id"]

        await client.post(f"/api/v1/users/{tg_id}/free-trial")

        status_resp = await client.get(f"/api/v1/users/{tg_id}/free-trial-status")
        assert status_resp.json()["already_used"] is True

    async def test_free_trial_nonexistent_user(self, client: AsyncClient):
        """Активация для несуществующего пользователя — 404."""
        resp = await client.post("/api/v1/users/9999999999/free-trial")
        assert resp.status_code == 404


class TestReferral:
    """Тесты реферальной программы."""

    async def test_get_referral_info(self, client: AsyncClient, registered_user):
        """Реферальная информация возвращается корректно."""
        tg_id = registered_user["telegram_id"]
        resp = await client.get(f"/api/v1/users/{tg_id}/referral")
        assert resp.status_code == 200
        data = resp.json()
        assert "referral_code" in data
        assert "referral_link" in data
        assert "referrals_count" in data
        assert "bonus_days" in data
        assert data["referrals_count"] == 0
        assert "t.me" in data["referral_link"]


class TestSubscriptionFlow:
    """Тесты подписки через API."""

    async def test_subscription_empty_for_new_user(self, client: AsyncClient, registered_user):
        """У нового пользователя нет подписки."""
        tg_id = registered_user["telegram_id"]
        resp = await client.get(f"/api/v1/users/{tg_id}/subscription")
        assert resp.status_code == 200
        assert resp.json() == {}

    async def test_devices_empty_without_subscription(self, client: AsyncClient, registered_user):
        """Без подписки список устройств пуст."""
        tg_id = registered_user["telegram_id"]
        resp = await client.get(f"/api/v1/users/{tg_id}/devices")
        assert resp.status_code == 200
        assert resp.json()["devices"] == []

    async def test_add_device_without_subscription(self, client: AsyncClient, registered_user):
        """Добавление устройства без подписки — ошибка."""
        tg_id = registered_user["telegram_id"]
        resp = await client.post(f"/api/v1/users/{tg_id}/devices", json={"device_name": "iPhone"})
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    async def test_create_payment(self, client: AsyncClient, registered_user):
        """Создание платежа возвращает payment_id."""
        tg_id = registered_user["telegram_id"]
        resp = await client.post(f"/api/v1/users/{tg_id}/create-payment", json={
            "plan_id": "Solo",
            "period_days": 30,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "payment_id" in data
        assert data["amount"] > 0

    async def test_confirm_payment_activates_subscription(self, client: AsyncClient):
        """Подтверждение платежа активирует подписку."""
        # Регистрируем пользователя
        reg = await client.post("/api/v1/users/register", json={
            "telegram_id": 300000001, "username": "pay_user", "first_name": "Платёж"
        })
        tg_id = reg.json()["telegram_id"]

        # Создаём платёж
        pay_resp = await client.post(f"/api/v1/users/{tg_id}/create-payment", json={
            "plan_id": "Solo",
            "period_days": 30,
        })
        payment_id = pay_resp.json()["payment_id"]

        # Подтверждаем платёж
        confirm_resp = await client.post(f"/api/v1/users/{tg_id}/confirm-payment", json={
            "payment_id": payment_id
        })
        assert confirm_resp.status_code == 200
        data = confirm_resp.json()
        assert data["success"] is True
        assert "subscription_link" in data
        assert data["subscription_link"].startswith("happ://")

    async def test_subscription_active_after_payment(self, client: AsyncClient):
        """После подтверждения платежа подписка активна."""
        reg = await client.post("/api/v1/users/register", json={
            "telegram_id": 300000002, "username": "pay_user2", "first_name": "Платёж2"
        })
        tg_id = reg.json()["telegram_id"]

        pay_resp = await client.post(f"/api/v1/users/{tg_id}/create-payment", json={
            "plan_id": "Solo", "period_days": 30
        })
        payment_id = pay_resp.json()["payment_id"]
        await client.post(f"/api/v1/users/{tg_id}/confirm-payment", json={"payment_id": payment_id})

        sub_resp = await client.get(f"/api/v1/users/{tg_id}/subscription")
        assert sub_resp.status_code == 200
        sub = sub_resp.json()
        assert sub["is_active"] is True
        assert sub["plan_name"] == "Solo"
        assert "expires_at" in sub

    async def test_add_device_after_payment(self, client: AsyncClient):
        """После оплаты можно добавить устройство."""
        reg = await client.post("/api/v1/users/register", json={
            "telegram_id": 300000003, "username": "dev_user", "first_name": "Устройство"
        })
        tg_id = reg.json()["telegram_id"]

        pay_resp = await client.post(f"/api/v1/users/{tg_id}/create-payment", json={
            "plan_id": "Solo", "period_days": 30
        })
        payment_id = pay_resp.json()["payment_id"]
        await client.post(f"/api/v1/users/{tg_id}/confirm-payment", json={"payment_id": payment_id})

        dev_resp = await client.post(f"/api/v1/users/{tg_id}/devices", json={"device_name": "iPhone"})
        assert dev_resp.status_code == 200
        data = dev_resp.json()
        assert data["success"] is True
        assert "subscription_link" in data
        assert data["subscription_link"].startswith("happ://")
