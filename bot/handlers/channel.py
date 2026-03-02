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
    Handle channel button — redirect directly to channel without intermediate page
    """
    # Сразу открываем канал — без промежуточного текста
    await callback.answer(url=CHANNEL_URL)
