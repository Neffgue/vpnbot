"""Subscription management tasks — cleanup expired and AUTO-RENEWAL."""
import logging
import httpx
import asyncio
import os
from celery import shared_task
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# ─── Database ────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost/vpn_db",
).replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ─── Импорт моделей (правильный путь) ────────────────────────────────────────
from backend.models.subscription import Subscription  # noqa: E402
from backend.models.user import User                   # noqa: E402
from backend.models.payment import Payment             # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────

async def _send_tg_message(telegram_id: int, text: str) -> bool:
    """Отправить сообщение пользователю через Telegram Bot API."""
    token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.error("BOT_TOKEN not configured — cannot send Telegram message")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                json={"chat_id": telegram_id, "text": text, "parse_mode": "HTML"},
            )
            if resp.status_code == 200:
                return True
            logger.warning(f"TG API returned {resp.status_code} for {telegram_id}: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Failed to send TG message to {telegram_id}: {e}")
        return False


async def _fetch_bot_text(key: str, fallback: str = "") -> str:
    """Загрузить текст уведомления из базы данных (через API)."""
    api_url = os.getenv("API_BASE_URL", "http://backend:8000/api/v1")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{api_url}/bot-texts/public")
            if resp.status_code == 200:
                texts = resp.json()
                if isinstance(texts, list):
                    for item in texts:
                        if item.get("key") == key:
                            return item.get("value", fallback)
                elif isinstance(texts, dict):
                    return texts.get(key, fallback)
    except Exception as e:
        logger.warning(f"Failed to fetch bot text '{key}': {e}")
    return fallback


async def _remove_xui_inbound(server, inbound_id: int) -> bool:
    """Удалить inbound из 3x-ui панели при деактивации подписки."""
    if not getattr(server, "panel_url", None):
        return False
    try:
        url = f"{server.panel_url}/xui/api/inbounds/{inbound_id}"
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            resp = await client.delete(
                url, auth=(server.panel_username, server.panel_password)
            )
            return resp.status_code in [200, 204]
    except Exception as e:
        logger.error(f"Failed to remove xui inbound {inbound_id}: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Авто-продление подписки
# ─────────────────────────────────────────────────────────────────────────────

async def _try_auto_renew(session: AsyncSession, subscription: Subscription) -> bool:
    """Попытаться автоматически продлить подписку.

    Логика:
    1. Проверяем баланс пользователя (user.balance).
    2. Если хватает — списываем и продлеваем.
    3. Уведомляем пользователя о результате.
    """
    user = await session.get(User, subscription.user_id)
    if not user:
        return False

    price = float(getattr(subscription, "price", None) or 0)
    period_days = int(getattr(subscription, "period_days", 30) or 30)

    # Авто-продление только если включено у пользователя и есть цена
    if not getattr(user, "auto_renewal", False):
        return False
    if price <= 0:
        return False

    # Проверяем баланс
    balance = float(getattr(user, "balance", 0) or 0)
    if balance < price:
        # Сообщаем что не хватает средств
        if user.telegram_id:
            text_template = await _fetch_bot_text(
                "notification_auto_renewal_failed",
                "❌ <b>Не удалось продлить подписку</b>\n\n"
                "На вашем балансе недостаточно средств для автопродления.\n"
                "Баланс: <b>{balance} ₽</b>\n"
                "Необходимо: <b>{price} ₽</b>\n\n"
                "Пополните баланс, чтобы сохранить доступ к VPN.",
            )
            await _send_tg_message(
                user.telegram_id,
                text_template.format(balance=int(balance), price=int(price)),
            )
        return False

    # Списываем средства
    user.balance = balance - price

    # Продлеваем подписку
    now = datetime.now(timezone.utc)
    current_expires = subscription.expires_at
    if current_expires and current_expires.tzinfo is None:
        current_expires = current_expires.replace(tzinfo=timezone.utc)
    base = max(now, current_expires or now)
    subscription.expires_at = base + timedelta(days=period_days)
    subscription.is_active = True

    # Записываем платёж (поля соответствуют реальной схеме Payment)
    import uuid as _uuid
    payment = Payment(
        id=str(_uuid.uuid4()),
        user_id=user.id,
        amount=price,
        currency="RUB",
        provider="auto_renewal",
        provider_payment_id=f"auto_{subscription.id}_{now.strftime('%Y%m%d%H%M%S')}",
        status="completed",
        plan_name=subscription.plan_name or "vpn",
        period_days=period_days,
        device_limit=getattr(subscription, "device_limit", 1),
    )
    session.add(payment)

    # Уведомляем пользователя об успехе
    if user.telegram_id:
        text_template = await _fetch_bot_text(
            "notification_auto_renewal_success",
            "✅ <b>Подписка успешно продлена!</b>\n\n"
            "Тариф: <b>{plan}</b>\n"
            "Действует до: <b>{expires}</b>\n"
            "Списано: <b>{price} ₽</b>\n"
            "Остаток на балансе: <b>{balance} ₽</b>",
        )
        new_expires = subscription.expires_at
        if new_expires.tzinfo:
            msk = timezone(timedelta(hours=3))
            new_expires = new_expires.astimezone(msk)
        await _send_tg_message(
            user.telegram_id,
            text_template.format(
                plan=subscription.plan_name or "VPN",
                expires=new_expires.strftime("%d.%m.%Y"),
                price=int(price),
                balance=int(user.balance),
            ),
        )

    logger.info(
        f"Auto-renewed subscription {subscription.id} for user {user.id}, "
        f"+{period_days}d, -{price}₽, new_balance={user.balance}"
    )
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Celery Tasks
# ─────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, name="worker.tasks.subscription_manager.cleanup_expired_subscriptions")
def cleanup_expired_subscriptions(self):
    """Деактивация истёкших подписок + попытка авто-продления."""

    async def _run():
        now = datetime.now(timezone.utc)
        results = {"total": 0, "renewed": 0, "deactivated": 0, "failed": 0}

        async with async_session() as session:
            stmt = (
                select(Subscription)
                .where(
                    and_(
                        Subscription.is_active == True,
                        Subscription.expires_at <= now,
                    )
                )
            )
            result = await session.execute(stmt)
            expired = result.scalars().all()
            results["total"] = len(expired)

            for sub in expired:
                try:
                    # 1. Попытка авто-продления
                    renewed = await _try_auto_renew(session, sub)
                    if renewed:
                        results["renewed"] += 1
                        continue

                    # 2. Деактивация
                    if getattr(sub, "server", None) and getattr(sub, "inbound_id", None):
                        await _remove_xui_inbound(sub.server, sub.inbound_id)

                    sub.is_active = False
                    sub.deactivated_at = now
                    results["deactivated"] += 1

                except Exception as e:
                    logger.error(f"Error processing subscription {sub.id}: {e}", exc_info=True)
                    results["failed"] += 1

            await session.commit()

        logger.info(
            f"cleanup_expired_subscriptions: total={results['total']}, "
            f"renewed={results['renewed']}, deactivated={results['deactivated']}, "
            f"failed={results['failed']}"
        )
        return results

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.error(f"Unexpected error in cleanup_expired_subscriptions: {e}", exc_info=True)
        self.retry(exc=e, countdown=3600, max_retries=3)


@shared_task(bind=True, name="worker.tasks.subscription_manager.sync_traffic_stats")
def sync_traffic_stats(self):
    """Синхронизация трафика из 3x-ui панелей в БД."""

    async def _run():
        results = {"total": 0, "synced": 0, "failed": 0}

        async with async_session() as session:
            stmt = select(Subscription).where(Subscription.is_active == True)
            result = await session.execute(stmt)
            subscriptions = result.scalars().all()
            results["total"] = len(subscriptions)

            for sub in subscriptions:
                try:
                    if not getattr(sub, "server", None) or not getattr(sub, "inbound_id", None):
                        continue

                    server = sub.server
                    if not getattr(server, "panel_url", None):
                        continue

                    url = f"{server.panel_url}/xui/api/inbounds/{sub.inbound_id}"
                    async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                        resp = await client.get(
                            url, auth=(server.panel_username, server.panel_password)
                        )
                    if resp.status_code != 200:
                        results["failed"] += 1
                        continue

                    data = resp.json().get("obj", {})
                    total_bytes = int(data.get("up", 0)) + int(data.get("down", 0))
                    sub.traffic_used_gb = total_bytes / (1024 ** 3)
                    sub.last_traffic_sync = datetime.now(timezone.utc)
                    results["synced"] += 1

                except Exception as e:
                    logger.error(f"Error syncing traffic for sub {sub.id}: {e}")
                    results["failed"] += 1

            await session.commit()

        logger.info(
            f"sync_traffic_stats: synced={results['synced']}/{results['total']}, "
            f"failed={results['failed']}"
        )
        return results

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.error(f"Unexpected error in sync_traffic_stats: {e}", exc_info=True)
        self.retry(exc=e, countdown=300, max_retries=3)
