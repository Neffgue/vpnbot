"""Notifications handler for bot tasks from Celery/Redis"""

import logging
import json
from aiogram import Router, Bot
from aiogram.types import Chat

logger = logging.getLogger(__name__)

router = Router()


class NotificationHandler:
    """
    Handler for receiving notifications from Celery/Redis
    Used for subscription expiry notifications, renewal reminders, etc.
    
    This handler is called by the backend service via:
    - Redis queue tasks
    - Celery beat scheduled tasks
    - Direct API calls with bot.send_message
    
    Notification types:
    - subscription_expiry_24h: 24 hours before expiry
    - subscription_expiry_12h: 12 hours before expiry
    - subscription_expiry_1h: 1 hour before expiry
    - subscription_expired: Subscription has expired
    - subscription_expired_3h: 3 hours after expiry
    """
    
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def send_subscription_notification(
        self,
        user_id: int,
        notification_type: str,
        plan_name: str = "",
        expire_date: str = "",
        days_remaining: int = 0
    ) -> bool:
        """
        Send subscription-related notification to user
        
        Args:
            user_id: Telegram user ID
            notification_type: Type of notification
            plan_name: Name of subscription plan
            expire_date: Expiration date
            days_remaining: Days until expiration
        
        Returns:
            True if sent successfully, False otherwise
        """
        
        try:
            messages = {
                "subscription_expiry_24h": (
                    f"⏰ <b>Напоминание о истечении подписки</b>\n\n"
                    f"Ваша подписка <b>{plan_name}</b> истечет через <b>24 часа</b>\n"
                    f"Дата: {expire_date}\n\n"
                    f"Продлите подписку прямо сейчас, чтобы не потерять доступ."
                ),
                "subscription_expiry_12h": (
                    f"⏰ <b>Внимание!</b> Подписка истечет через <b>12 часов</b>\n\n"
                    f"План: {plan_name}\n"
                    f"Истечение: {expire_date}\n\n"
                    f"Нажмите /start чтобы продлить подписку"
                ),
                "subscription_expiry_1h": (
                    f"🚨 <b>СРОЧНО!</b> Подписка истечет через <b>1 час</b>\n\n"
                    f"План: {plan_name}\n\n"
                    f"Продлите подписку немедленно: /start"
                ),
                "subscription_expired": (
                    f"❌ <b>Подписка истекла</b>\n\n"
                    f"Ваша подписка {plan_name} больше не активна.\n\n"
                    f"Чтобы восстановить доступ, оформите новую подписку.\n"
                    f"Нажмите /start"
                ),
                "subscription_expired_3h": (
                    f"❌ <b>Доступ отключен</b>\n\n"
                    f"Ваша подписка {plan_name} истекла 3 часа назад.\n\n"
                    f"Доступ к VPN отключен. Продлите подписку: /start"
                ),
                "free_trial_expiry_24h": (
                    f"⏰ <b>Пробный период заканчивается</b>\n\n"
                    f"Ваш бесплатный доступ на 24 часа истечет через <b>24 часа</b>\n\n"
                    f"Оформите подписку чтобы продолжить использование VPN.\n"
                    f"Нажмите /start"
                ),
                "referral_bonus": (
                    f"🎁 <b>Новый бонус!</b>\n\n"
                    f"Один из ваших рефералов оформил подписку!\n"
                    f"Вы получили +1 день подписки.\n\n"
                    f"Смотрите статистику: /cabinet"
                ),
                "balance_added": (
                    f"💰 <b>Баланс пополнен</b>\n\n"
                    f"На ваш счет добавлено: +{days_remaining}₽\n\n"
                    f"Личный кабинет: /cabinet"
                ),
            }
            
            message_text = messages.get(
                notification_type,
                f"📢 Уведомление: {notification_type}"
            )
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message_text
            )
            
            logger.info(f"Notification sent to user {user_id}: {notification_type}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send notification to user {user_id}: {e}")
            return False
    
    async def send_bulk_notification(
        self,
        user_ids: list[int],
        message_text: str,
        notification_type: str = "broadcast"
    ) -> dict:
        """
        Send notification to multiple users
        
        Args:
            user_ids: List of Telegram user IDs
            message_text: Message text to send
            notification_type: Type of notification
        
        Returns:
            Dictionary with sent count and failed count
        """
        
        sent_count = 0
        failed_count = 0
        
        for user_id in user_ids:
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=message_text
                )
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id}: {e}")
                failed_count += 1
        
        logger.info(f"Bulk notification: sent {sent_count}, failed {failed_count}")
        return {
            "sent": sent_count,
            "failed": failed_count,
            "type": notification_type
        }


async def process_notification_task(bot: Bot, task_data: dict) -> bool:
    """
    Process notification task from queue
    
    Expected task_data format:
    {
        "user_id": 123456,
        "type": "subscription_expiry_24h",
        "plan_name": "Семейный",
        "expire_date": "2024-01-15",
        "days_remaining": 1
    }
    """
    
    handler = NotificationHandler(bot)
    
    try:
        user_id = task_data.get("user_id")
        notification_type = task_data.get("type", "")
        plan_name = task_data.get("plan_name", "")
        expire_date = task_data.get("expire_date", "")
        days_remaining = task_data.get("days_remaining", 0)
        
        if not user_id or not notification_type:
            logger.error(f"Invalid notification task: {task_data}")
            return False
        
        return await handler.send_subscription_notification(
            user_id=user_id,
            notification_type=notification_type,
            plan_name=plan_name,
            expire_date=expire_date,
            days_remaining=days_remaining
        )
    
    except Exception as e:
        logger.error(f"Error processing notification task: {e}")
        return False


async def process_bulk_notification_task(bot: Bot, task_data: dict) -> dict:
    """
    Process bulk notification task
    
    Expected task_data format:
    {
        "type": "broadcast",
        "user_ids": [123, 456, 789],
        "message": "Message text"
    }
    """
    
    handler = NotificationHandler(bot)
    
    try:
        user_ids = task_data.get("user_ids", [])
        message_text = task_data.get("message", "")
        notification_type = task_data.get("type", "broadcast")
        
        if not user_ids or not message_text:
            logger.error(f"Invalid bulk notification task: {task_data}")
            return {"sent": 0, "failed": 0}
        
        return await handler.send_bulk_notification(
            user_ids=user_ids,
            message_text=message_text,
            notification_type=notification_type
        )
    
    except Exception as e:
        logger.error(f"Error processing bulk notification task: {e}")
        return {"sent": 0, "failed": 0}
