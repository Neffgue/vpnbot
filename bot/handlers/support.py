"""Support handler"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.config import config
from bot.keyboards.inline_kb import get_link_button
from bot.utils.api_client import APIClient

logger = logging.getLogger(__name__)

router = Router()


SUPPORT_URL = "https://t.me/TechWizardsSupport"


@router.callback_query(F.data == "support")
async def support_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle support button — send URL button that opens support chat."""
    await callback.answer()
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    # Получаем URL поддержки из настроек бота (или используем дефолтный)
    support_url = SUPPORT_URL
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            settings = await client.get_bot_settings()
            support_url = settings.get("support_url") or SUPPORT_URL
    except Exception:
        pass

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать в поддержку", url=support_url)],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
    ])
    try:
        await callback.message.edit_text(
            "💬 <b>Поддержка</b>\n\nНажмите кнопку ниже:",
            parse_mode="HTML",
            reply_markup=kb,
        )
    except Exception:
        await callback.message.answer(
            "💬 <b>Поддержка</b>\n\nНажмите кнопку ниже:",
            parse_mode="HTML",
            reply_markup=kb,
        )
