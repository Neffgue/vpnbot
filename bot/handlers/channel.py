"""Channel subscription handler"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.config import config
from bot.keyboards.inline_kb import get_link_button

logger = logging.getLogger(__name__)

router = Router()


CHANNEL_URL = "https://t.me/techwizardsru"


@router.callback_query(F.data == "channel")
async def channel_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handle channel button — redirect directly to channel
    """
    await callback.answer()
    # Перенаправляем сразу по ссылке через URL-кнопку
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Перейти на канал", url=CHANNEL_URL)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")],
    ])
    try:
        await callback.message.edit_text(
            "📢 <b>Наш канал</b>\n\nНажмите кнопку ниже, чтобы перейти в наш Telegram-канал:",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except Exception:
        await callback.message.answer(
            "📢 <b>Наш канал</b>\n\nНажмите кнопку ниже, чтобы перейти в наш Telegram-канал:",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
