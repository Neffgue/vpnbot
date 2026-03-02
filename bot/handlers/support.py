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
    Handle support button — redirect directly to support chat without intermediate page
    """
    # Сразу открываем ссылку — без промежуточного текста
    await callback.answer(url=SUPPORT_URL)
