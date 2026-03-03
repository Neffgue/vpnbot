"""Notification tasks — тексты уведомлений загружаются из БД через API (Single Source of Truth)."""
import logging
import asyncio
import httpx
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

# ─── Дефолтные тексты — используются если API недоступен ────────────────────
DEFAULT_TEXTS = {
    "notification_24h": (
        "⏰ <b>Ваша подписка VPN истекает через 24 часа</b>\n\n"
        "Тариф: <b>{plan}</b>\n"
        "Истекает: <b>{expires}</b>\n\n"
        "Продлите подписку, чтобы сохранить доступ к VPN."
    ),
    "notification_12h": (
        "⚠️ <b>Ваша подписка VPN истекает через 12 часов</b>\n\n"
        "Тариф: <b>{plan}</b>\n"
        "Истекает: <b>{expires}</b>\n\n"
        "Поторопитесь продлить подписку!"
    ),
    "notification_1h": (
        "🚨 <b>Ваша подписка VPN истекает через 1 час</b>\n\n"
        "Тариф: <b>{plan}</b>\n"
        "Истекает: <b>{expires}</b>\n\n"
        "Срочно продлите подписку, чтобы не потерять доступ!"
    ),
    "notification_expired": (
        "❌ <b>Ваша подписка VPN истекла</b>\n\n"
        "Тариф: <b>{plan}</b>\n\n"
        "Доступ к VPN прекращён. Продлите подписку, чтобы восстановить доступ."
    ),
    "notification_3h_after": (
        "😔 <b>Ваша VPN-подписка истекла 3 часа назад</b>\n\n"
        "Тариф: <b>{plan}</b>\n\n"
        "Восстановите доступ к VPN — это займёт меньше минуты!"
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────

async def _load_bot_texts() -> dict:
    """Загрузить все тексты уведомлений из API. Fallback — DEFAULT_TEXTS."""
    api_url = os.getenv("API_BASE_URL", "http://backend:8000/api/v1")
    texts = dict(DEFAULT_TEXTS)  # начинаем с дефолтных
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{api_url}/bot-texts/public")
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    for item in data:
                        key = item.get("key", "")
                        val = item.get("value", "")
                        if key and val:
                            texts[key] = val
                elif isinstance(data, dict):
                    texts.update(data)
    except Exception as e:
        logger.warning(f"Failed to load bot texts from API, using defaults: {e}")
    return texts


async def _send_tg_message(telegram_id: int, text: str) -> bool:
    """Отправить сообщение пользователю через Telegram Bot API."""
    token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.error("BOT_TOKEN not configured — cannot send notification")
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
            logger.warning(
                f"TG API returned {resp.status_code} for {telegram_id}: {resp.text[:200]}"
            )
            return False
    except Exception as e:
        logger.error(f"Failed to send TG message to {telegram_id}: {e}")
        return False


async def _mark_notification_sent(session: AsyncSession, sub: Subscription, col: str) -> None:
    """Пометить что уведомление типа col отправлено."""
    if hasattr(sub, col):
        setattr(sub, col, True)
        await session.commit()


async def _get_expiring(session: AsyncSession, hours_from_now: int) -> list:
    """Получить подписки, истекающие в течение заданного количества часов."""
    now = datetime.now(timezone.utc)
    target = now + timedelta(hours=hours_from_now)
    stmt = (
        select(Subscription)
        .join(User, User.id == Subscription.user_id)
        .where(
            and_(
                Subscription.is_active == True,
                Subscription.expires_at > now,
                Subscription.expires_at <= target,
            )
        )
    )
    result = await session.execute(stmt)
    return result.scalars().all()


def _format_expires(expires_at: datetime) -> str:
    """Форматировать дату истечения в московском времени."""
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    msk = timezone(timedelta(hours=3))
    return expires_at.astimezone(msk).strftime("%d.%m.%Y %H:%M (МСК)")


# ─────────────────────────────────────────────────────────────────────────────
# Celery Task
# ─────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, name="worker.tasks.notifications.check_expiring_subscriptions")
def check_expiring_subscriptions(self):
    """Проверить истекающие подписки и отправить уведомления через Telegram."""

    async def _run():
        # Загружаем тексты из БД (единый источник истины)
        texts = await _load_bot_texts()
        bot_username = (
            os.getenv("BOT_USERNAME")
            or os.getenv("TELEGRAM_BOT_USERNAME")
            or "vpnbot"
        )
        bot_link = f"https://t.me/{bot_username}"

        # (hours_until_expiry, text_key, notified_column)
        notification_configs = [
            (24,  "notification_24h",  "notified_24h"),
            (12,  "notification_12h",  "notified_12h"),
            (1,   "notification_1h",   "notified_1h"),
            (0,   "notification_expired", "notified_0h"),
        ]

        total_sent = 0

        async with async_session() as session:
            for hours, text_key, col in notification_configs:
                try:
                    subs = await _get_expiring(session, hours)
                    for sub in subs:
                        # Уже уведомляли?
                        if getattr(sub, col, False):
                            continue

                        user = await session.get(User, sub.user_id)
                        if not user or not user.telegram_id:
                            continue

                        template = texts.get(text_key, DEFAULT_TEXTS.get(text_key, ""))
                        msg = template.format(
                            plan=sub.plan_name or "VPN",
                            expires=_format_expires(sub.expires_at),
                        )
                        msg += f'\n\n<a href="{bot_link}">Продлить подписку</a>'

                        ok = await _send_tg_message(user.telegram_id, msg)
                        if ok:
                            await _mark_notification_sent(session, sub, col)
                            total_sent += 1

                except Exception as e:
                    logger.error(
                        f"Error processing {hours}h notifications: {e}", exc_info=True
                    )

            # ── Уведомление через 3 часа после истечения ──────────────────
            try:
                now = datetime.now(timezone.utc)
                three_hours_ago = now - timedelta(hours=3)
                stmt = (
                    select(Subscription)
                    .join(User, User.id == Subscription.user_id)
                    .where(
                        and_(
                            Subscription.is_active == False,
                            Subscription.expires_at > three_hours_ago,
                            Subscription.expires_at <= now,
                            Subscription.notified_3h_after_expiry == False,
                        )
                    )
                )
                result = await session.execute(stmt)
                subs_3h = result.scalars().all()

                for sub in subs_3h:
                    user = await session.get(User, sub.user_id)
                    if not user or not user.telegram_id:
                        continue

                    template = texts.get("notification_3h_after", DEFAULT_TEXTS["notification_3h_after"])
                    msg = template.format(plan=sub.plan_name or "VPN")
                    msg += f'\n\n<a href="{bot_link}">Восстановить доступ</a>'

                    ok = await _send_tg_message(user.telegram_id, msg)
                    if ok:
                        await _mark_notification_sent(session, sub, "notified_3h_after_expiry")
                        total_sent += 1

            except Exception as e:
                logger.error(f"Error in 3h-after notifications: {e}", exc_info=True)

        logger.info(f"check_expiring_subscriptions: sent {total_sent} notifications")
        return {"sent": total_sent}

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.error(f"Unexpected error in check_expiring_subscriptions: {e}", exc_info=True)
        self.retry(exc=e, countdown=60, max_retries=3)
