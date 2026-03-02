"""Authentication and user registration middleware"""

import logging
from typing import Any, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Update, User, Message, CallbackQuery

from bot.utils.api_client import APIClient
from bot.config import config

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """
    Middleware for user authentication and auto-registration.
    Automatically registers users on first interaction and checks ban status.
    """
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Any],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        """
        Process update through middleware
        """
        
        # Get user from update
        user = self._get_user_from_update(event)
        
        if not user:
            # No user in this update, continue
            return await handler(event, data)
        
        user_id = user.id
        
        # Try to register user if not exists and check ban status
        try:
            async with APIClient(config.api.base_url, config.api.api_key) as client:
                # get_user returns {} if user not found (404), raises on other errors
                user_info = await client.get_user(user_id)
                if not user_info:
                    # User not registered, register them
                    await self._register_user(client, user)
                
                # Check ban status
                ban_status = await client.check_ban(user_id)
                
                if ban_status.get("is_banned", False):
                    # User is banned
                    ban_message = f"❌ Ваш аккаунт заблокирован.\nПричина: {ban_status.get('reason', 'не указана')}\n\nСвяжитесь с поддержкой для подробной информации."
                    
                    from aiogram.types import Message, CallbackQuery, Update as UpdateType
                    if isinstance(event, UpdateType):
                        if event.message:
                            await event.message.answer(ban_message)
                        elif event.callback_query:
                            await event.callback_query.answer(ban_message, show_alert=True)
                    elif isinstance(event, Message):
                        await event.answer(ban_message)
                    elif isinstance(event, CallbackQuery):
                        await event.answer(ban_message, show_alert=True)
                    
                    return
                
                # Store user info in data for handler
                data["user_id"] = user_id
                data["user"] = user
                
        except Exception as e:
            logger.error(f"Auth middleware error: {e}")
            # Continue anyway to not break the bot
            data["user_id"] = user_id
            data["user"] = user
        
        # Call the handler
        return await handler(event, data)
    
    @staticmethod
    def _get_user_from_update(event) -> User:
        """Extract user from update"""
        from aiogram.types import Message, CallbackQuery, InlineQuery, Update
        if isinstance(event, Update):
            if event.message:
                return event.message.from_user
            elif event.callback_query:
                return event.callback_query.from_user
            elif event.inline_query:
                return event.inline_query.from_user
        elif isinstance(event, (Message, CallbackQuery, InlineQuery)):
            if hasattr(event, 'from_user') and event.from_user:
                return event.from_user
        return None
    
    @staticmethod
    async def _register_user(client: APIClient, user: User) -> None:
        """Register new user in the system"""
        try:
            # Check if there's a referral code in user's message (handled in handler)
            await client.register_user(
                user_id=user.id,
                username=user.username or "",
                first_name=user.first_name or "",
                ref_code=None,  # Referral code is handled in start handler
            )
            logger.info(f"User {user.id} registered successfully")
        except Exception as e:
            logger.error(f"Failed to register user {user.id}: {e}")
            raise
