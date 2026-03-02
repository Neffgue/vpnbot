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
    """
    Handle support button — redirect directly to support
    """
    await callback.answer()
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать в поддержку", url=SUPPORT_URL)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")],
    ])
    try:
        await callback.message.edit_text(
            "💬 <b>Поддержка</b>\n\nНажмите кнопку ниже, чтобы написать нам:",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except Exception:
        await callback.message.answer(
            "💬 <b>Поддержка</b>\n\nНажмите кнопку ниже, чтобы написать нам:",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
