"""Notification tasks for subscription expiry warnings."""
import logging
from datetime import datetime, timedelta
from celery import shared_task
import httpx
import os
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+asyncpg://user:password@localhost/vpn_db'
).replace('postgresql://', 'postgresql+asyncpg://')
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Import models from backend
from backend.models.subscription import Subscription
from backend.models.user import User


class SubscriptionNotificationTask:
    """Helper class for subscription notifications."""
    
    @staticmethod
    async def get_subscriptions_expiring_in(hours: int) -> list:
        """Get subscriptions expiring in specified hours."""
        async with async_session() as session:
            now = datetime.utcnow()
            target_time = now + timedelta(hours=hours)
            
            stmt = select(Subscription).join(User).where(
                and_(
                    Subscription.is_active == True,
                    Subscription.expires_at > now,
                    Subscription.expires_at <= target_time
                )
            )
            result = await session.execute(stmt)
            return result.scalars().all()
    
    @staticmethod
    async def mark_notification_sent(subscription_id: int, notification_type: str):
        """Mark notification as sent on subscription."""
        async with async_session() as session:
            subscription = await session.get(Subscription, subscription_id)
            if subscription:
                if notification_type == '24h':
                    subscription.notified_24h = True
                elif notification_type == '12h':
                    subscription.notified_12h = True
                elif notification_type == '1h':
                    subscription.notified_1h = True
                elif notification_type == '0h':
                    subscription.notified_0h = True
                elif notification_type == '3h_after':
                    subscription.notified_3h_after_expiry = True
                
                await session.commit()
    
    @staticmethod
    async def send_telegram_message(chat_id: int, message: str) -> bool:
        """Send message via Telegram Bot API."""
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            logger.error('TELEGRAM_BOT_TOKEN not set')
            return False
        
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logger.info(f'Telegram message sent to {chat_id}')
                return True
        except Exception as e:
            logger.error(f'Failed to send Telegram message: {e}')
            return False


@shared_task(bind=True, name='worker.tasks.notifications.check_expiring_subscriptions')
def check_expiring_subscriptions(self):
    """
    Check for subscriptions expiring in 24h, 12h, 1h, 0h, or 3h after expiry.
    Send notification to user via Telegram.
    """
    import asyncio
    
    async def run_check():
        bot_username = os.getenv('BOT_USERNAME') or os.getenv('TELEGRAM_BOT_USERNAME') or 'vpnsolid_bot'
        bot_link = f'https://t.me/{bot_username}'

        # Конфиг уведомлений: (часов_до, тип, флаг, текст)
        notification_configs = [
            (
                24, '24h', 'notified_24h',
                '⏰ <b>Ваша VPN-подписка истекает через 24 часа</b>\n\n'
                'Не забудьте продлить подписку, чтобы не потерять доступ к VPN.\n\n'
                '📱 Тариф: {plan}\n'
                '⏳ Истекает: {expires}\n\n'
                '👇 Продлите подписку прямо сейчас:'
            ),
            (
                12, '12h', 'notified_12h',
                '⏰ <b>Ваша VPN-подписка истекает через 12 часов</b>\n\n'
                'Осталось совсем немного! Продлите подписку, чтобы не прерывать доступ.\n\n'
                '📱 Тариф: {plan}\n'
                '⏳ Истекает: {expires}\n\n'
                '👇 Продлите подписку прямо сейчас:'
            ),
            (
                1, '1h', 'notified_1h',
                '🔴 <b>Ваша VPN-подписка истекает через 1 час</b>\n\n'
                'Осталось меньше часа! Продлите подписку прямо сейчас.\n\n'
                '📱 Тариф: {plan}\n'
                '⏳ Истекает: {expires}\n\n'
                '👇 Нажмите, чтобы продлить:'
            ),
            (
                0, '0h', 'notified_0h',
                '🚨 <b>Ваша VPN-подписка истекла!</b>\n\n'
                'Ваш доступ к VPN прекращён. Продлите подписку, чтобы восстановить доступ.\n\n'
                '📱 Тариф: {plan}\n\n'
                '👇 Продлите подписку:'
            ),
        ]

        total_sent = 0

        for hours, notification_type, column, message_template in notification_configs:
            try:
                subscriptions = await SubscriptionNotificationTask.get_subscriptions_expiring_in(hours)

                for subscription in subscriptions:
                    # Проверяем — не отправляли ли уже это уведомление
                    if getattr(subscription, column):
                        continue

                    user = subscription.user
                    if not user or not user.telegram_id:
                        continue

                    # Форматируем дату по МСК
                    from datetime import timezone
                    expires_dt = subscription.expires_at
                    if expires_dt.tzinfo is None:
                        expires_dt = expires_dt.replace(tzinfo=timezone.utc)
                    msk_offset = timedelta(hours=3)
                    expires_msk = expires_dt.astimezone(timezone(msk_offset))
                    expires_str = expires_msk.strftime('%d.%m.%Y %H:%M (МСК)')

                    message = message_template.format(
                        plan=subscription.plan_name,
                        expires=expires_str,
                    )
                    message += f'\n<a href="{bot_link}">Перейти в бот</a>'

                    success = await SubscriptionNotificationTask.send_telegram_message(
                        user.telegram_id, message
                    )

                    if success:
                        await SubscriptionNotificationTask.mark_notification_sent(
                            subscription.id, notification_type
                        )
                        total_sent += 1

            except Exception as e:
                logger.error(f'Error checking {hours}h expiring subscriptions: {e}')

        # Уведомление спустя 3 часа после окончания подписки
        try:
            async with async_session() as session:
                now = datetime.utcnow()
                three_hours_ago = now - timedelta(hours=3)

                stmt = select(Subscription).join(User).where(
                    and_(
                        Subscription.is_active == False,
                        Subscription.expires_at > three_hours_ago,
                        Subscription.expires_at <= now,
                        Subscription.notified_3h_after_expiry == False
                    )
                )
                result = await session.execute(stmt)
                subscriptions = result.scalars().all()

                for subscription in subscriptions:
                    user = subscription.user
                    if not user or not user.telegram_id:
                        continue

                    message = (
                        '❌ <b>Ваша VPN-подписка истекла 3 часа назад</b>\n\n'
                        'Ваш доступ к VPN отключён. Восстановите его прямо сейчас — '
                        'это займёт меньше минуты!\n\n'
                        f'📱 Тариф: {subscription.plan_name}\n\n'
                        f'👇 Продлите подписку:\n<a href="{bot_link}">Перейти в бот</a>'
                    )

                    success = await SubscriptionNotificationTask.send_telegram_message(
                        user.telegram_id, message
                    )

                    if success:
                        await SubscriptionNotificationTask.mark_notification_sent(
                            subscription.id, '3h_after'
                        )
                        total_sent += 1

        except Exception as e:
            logger.error(f'Error checking 3h-after-expiry subscriptions: {e}')
        
        logger.info(f'check_expiring_subscriptions: Sent {total_sent} notifications')
        return {'sent': total_sent}
    
    try:
        return asyncio.run(run_check())
    except Exception as e:
        logger.error(f'Unexpected error in check_expiring_subscriptions: {e}')
        self.retry(exc=e, countdown=60, max_retries=3)
