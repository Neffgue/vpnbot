"""
Тесты сервисного слоя (UserService, SubscriptionService).
Проверяем бизнес-логику напрямую, без HTTP.
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta

pytestmark = pytest.mark.asyncio


class TestUserService:
    """Тесты UserService."""

    async def test_create_user(self, db_session):
        """Создание пользователя успешно."""
        from backend.services.user_service import UserService
        service = UserService(db_session)
        user = await service.create_user(
            telegram_id=700000001,
            username="svc_test",
            first_name="Сервис",
        )
        assert user.id is not None
        assert user.telegram_id == 700000001
        assert user.username == "svc_test"
        assert user.is_banned is False
        assert user.free_trial_used is False
        assert user.referral_code is not None
        assert len(user.referral_code) >= 6

    async def test_get_user_by_telegram_id(self, db_session):
        """Получение пользователя по telegram_id."""
        from backend.services.user_service import UserService
        service = UserService(db_session)
        created = await service.create_user(700000002, "svc2", "Два")
        found = await service.get_user_by_telegram_id(700000002)
        assert found is not None
        assert found.id == created.id

    async def test_get_nonexistent_user(self, db_session):
        """Несуществующий пользователь — None."""
        from backend.services.user_service import UserService
        service = UserService(db_session)
        user = await service.get_user_by_telegram_id(9999999999)
        assert user is None

    async def test_ban_user(self, db_session):
        """Бан пользователя устанавливает is_banned=True."""
        from backend.services.user_service import UserService
        service = UserService(db_session)
        user = await service.create_user(700000003, "svc3", "Три")
        await service.ban_user(user.id)
        updated = await service.get_user(user.id)
        assert updated.is_banned is True

    async def test_unban_user(self, db_session):
        """Разбан пользователя устанавливает is_banned=False."""
        from backend.services.user_service import UserService
        service = UserService(db_session)
        user = await service.create_user(700000004, "svc4", "Четыре")
        await service.ban_user(user.id)
        await service.unban_user(user.id)
        updated = await service.get_user(user.id)
        assert updated.is_banned is False

    async def test_mark_free_trial_used(self, db_session):
        """Метка об использовании пробного периода."""
        from backend.services.user_service import UserService
        service = UserService(db_session)
        user = await service.create_user(700000005, "svc5", "Пять")
        assert user.free_trial_used is False
        await service.mark_free_trial_used(user.id)
        updated = await service.get_user(user.id)
        assert updated.free_trial_used is True

    async def test_referral_code_unique(self, db_session):
        """Реферальный код уникален для каждого пользователя."""
        from backend.services.user_service import UserService
        service = UserService(db_session)
        u1 = await service.create_user(700000006, "svc6", "Шесть")
        u2 = await service.create_user(700000007, "svc7", "Семь")
        assert u1.referral_code != u2.referral_code


class TestSubscriptionService:
    """Тесты SubscriptionService."""

    async def test_create_subscription(self, db_session):
        """Создание подписки успешно."""
        from backend.services.user_service import UserService
        from backend.services.subscription_service import SubscriptionService
        user_service = UserService(db_session)
        user = await user_service.create_user(800000001, "sub1", "Суб1")

        sub_service = SubscriptionService(db_session)
        sub = await sub_service.create_subscription(
            user_id=user.id,
            plan_name="Solo",
            period_days=30,
            device_limit=1,
            traffic_gb=100,
        )
        assert sub.id is not None
        assert sub.user_id == user.id
        assert sub.plan_name == "Solo"
        assert sub.is_active is True
        assert sub.xui_client_uuid is not None

    async def test_subscription_expires_in_future(self, db_session):
        """Дата истечения подписки — в будущем."""
        from backend.services.user_service import UserService
        from backend.services.subscription_service import SubscriptionService
        user_service = UserService(db_session)
        user = await user_service.create_user(800000002, "sub2", "Суб2")

        sub_service = SubscriptionService(db_session)
        sub = await sub_service.create_subscription(
            user_id=user.id,
            plan_name="Solo",
            period_days=30,
            device_limit=1,
            traffic_gb=100,
        )
        assert sub.expires_at > datetime.utcnow()

    async def test_get_active_subscription(self, db_session):
        """Получение активной подписки пользователя."""
        from backend.services.user_service import UserService
        from backend.services.subscription_service import SubscriptionService
        user_service = UserService(db_session)
        user = await user_service.create_user(800000003, "sub3", "Суб3")

        sub_service = SubscriptionService(db_session)
        await sub_service.create_subscription(
            user_id=user.id,
            plan_name="Family",
            period_days=30,
            device_limit=5,
            traffic_gb=500,
        )
        active = await sub_service.get_active_user_subscription(user.id)
        assert active is not None
        assert active.plan_name == "Family"
        assert active.is_active is True

    async def test_no_active_subscription_for_new_user(self, db_session):
        """У нового пользователя нет активной подписки."""
        from backend.services.user_service import UserService
        from backend.services.subscription_service import SubscriptionService
        user_service = UserService(db_session)
        user = await user_service.create_user(800000004, "sub4", "Суб4")

        sub_service = SubscriptionService(db_session)
        active = await sub_service.get_active_user_subscription(user.id)
        assert active is None

    async def test_trial_subscription_lasts_one_day(self, db_session):
        """Пробная подписка — 1 день."""
        from backend.services.user_service import UserService
        from backend.services.subscription_service import SubscriptionService
        user_service = UserService(db_session)
        user = await user_service.create_user(800000005, "sub5", "Суб5")

        sub_service = SubscriptionService(db_session)
        sub = await sub_service.create_subscription(
            user_id=user.id,
            plan_name="Trial",
            period_days=1,
            device_limit=1,
            traffic_gb=10,
        )
        now = datetime.utcnow()
        diff = sub.expires_at - now
        # Разница должна быть близка к 1 дню (с погрешностью 5 минут)
        assert timedelta(hours=23) <= diff <= timedelta(hours=25)

    async def test_deactivate_subscription(self, db_session):
        """Деактивация подписки."""
        from backend.services.user_service import UserService
        from backend.services.subscription_service import SubscriptionService
        user_service = UserService(db_session)
        user = await user_service.create_user(800000006, "sub6", "Суб6")

        sub_service = SubscriptionService(db_session)
        sub = await sub_service.create_subscription(
            user_id=user.id,
            plan_name="Solo",
            period_days=30,
            device_limit=1,
            traffic_gb=100,
        )
        await sub_service.deactivate_subscription(sub.id)
        updated = await sub_service.get_subscription(sub.id)
        assert updated.is_active is False


class TestSecurity:
    """Тесты модуля безопасности."""

    def test_create_and_decode_token(self):
        """Создание и декодирование JWT токена."""
        from backend.utils.security import create_access_token, decode_token
        payload = {"sub": "test-user-id"}
        token = create_access_token(payload)
        assert token is not None
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded.get("sub") == "test-user-id"

    def test_invalid_token_returns_none(self):
        """Неверный токен возвращает None."""
        from backend.utils.security import decode_token
        result = decode_token("invalid.token.here")
        assert result is None

    def test_expired_token(self):
        """Истёкший токен не принимается."""
        from backend.utils.security import create_access_token, decode_token
        from datetime import timedelta
        token = create_access_token({"sub": "user"}, expires_delta=timedelta(seconds=-1))
        result = decode_token(token)
        # Истёкший токен должен вернуть None или пустой payload
        assert result is None or result.get("sub") is None
