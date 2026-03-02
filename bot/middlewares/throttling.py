"""Throttling middleware to limit message rate"""

import logging
import time
from typing import Any, Callable, Dict, List
from aiogram import BaseMiddleware
from aiogram.types import Update

logger = logging.getLogger(__name__)

# Если пользователь делает >300 нажатий за 60 секунд — cooldown 10 секунд
MAX_PER_MINUTE = 300
COOLDOWN_SECONDS = 10


class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware for throttling user messages.
    Only rule: if user sends >300 updates in 60 seconds → 10 second cooldown.
    """

    def __init__(self):
        self.user_minute_timestamps: Dict[int, List[float]] = {}
        self.user_cooldown_until: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Any],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        user_id = self._get_user_id(event)

        if not user_id:
            return await handler(event, data)

        current_time = time.time()

        # Если пользователь на cooldown — молча игнорируем
        cooldown_until = self.user_cooldown_until.get(user_id, 0)
        if current_time < cooldown_until:
            logger.debug(f"User {user_id} is on cooldown until {cooldown_until:.1f}")
            return

        # Считаем нажатия за последние 60 секунд
        minute_window = current_time - 60
        timestamps = self.user_minute_timestamps.get(user_id, [])
        timestamps = [t for t in timestamps if t > minute_window]
        timestamps.append(current_time)
        self.user_minute_timestamps[user_id] = timestamps

        if len(timestamps) > MAX_PER_MINUTE:
            # Ставим cooldown 10 секунд
            self.user_cooldown_until[user_id] = current_time + COOLDOWN_SECONDS
            logger.warning(f"User {user_id} exceeded {MAX_PER_MINUTE}/min limit — cooldown {COOLDOWN_SECONDS}s")
            return

        return await handler(event, data)

    @staticmethod
    def _get_user_id(event) -> int:
        """Extract user ID from update"""
        from aiogram.types import Message, CallbackQuery, InlineQuery, Update
        if isinstance(event, Update):
            if event.message:
                return event.message.from_user.id
            elif event.callback_query:
                return event.callback_query.from_user.id
            elif event.inline_query:
                return event.inline_query.from_user.id
        elif isinstance(event, (Message, CallbackQuery, InlineQuery)):
            if hasattr(event, 'from_user') and event.from_user:
                return event.from_user.id
        return None
