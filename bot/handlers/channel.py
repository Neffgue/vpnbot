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
    """Handle channel button — send URL button that opens channel."""
    await callback.answer()
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    # Получаем URL канала из настроек бота (или используем дефолтный)
    channel_url = CHANNEL_URL
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            settings = await client.get_bot_settings()
            channel_url = settings.get("channel_url") or CHANNEL_URL
    except Exception:
        pass

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Перейти в канал", url=channel_url)],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
    ])
    try:
        await callback.message.edit_text(
            "📢 <b>Наш канал</b>\n\nНажмите кнопку ниже:",
            parse_mode="HTML",
            reply_markup=kb,
        )
    except Exception:
        await callback.message.answer(
            "📢 <b>Наш канал</b>\n\nНажмите кнопку ниже:",
            parse_mode="HTML",
            reply_markup=kb,
        )
