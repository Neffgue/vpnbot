"""Channel handler — прямой редирект по URL из настроек БД."""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.config import config
from bot.utils.api_client import APIClient
from bot.utils.media import resolve_media

logger = logging.getLogger(__name__)

router = Router()

# Fallback — используется если API недоступен
CHANNEL_URL_FALLBACK = "https://t.me/techwizardsru"


@router.callback_query(F.data == "channel")
async def channel_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Кнопка Наш канал — показывает URL-кнопку для перехода в канал.

    URL берётся из настроек БД (поле channel_url).
    Если задана картинка (channel_image) — отправляем фото с caption.
    Если картинки нет — отправляем текстовое сообщение.
    Кнопки: [Перейти в канал (url)] [◀️ Назад]
    """
    await callback.answer()

    channel_url = CHANNEL_URL_FALLBACK
    channel_text = "📢 <b>Наш канал</b>\n\nПерейдите по ссылке ниже:"
    cover_media = None

    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            settings = await client.get_bot_settings()
            if settings:
                channel_url = settings.get("channel_url") or CHANNEL_URL_FALLBACK
                raw_img = settings.get("channel_image") or ""
                if raw_img:
                    cover_media = resolve_media(raw_img)

            texts = await client.get_all_bot_texts()
            if texts:
                channel_text = texts.get("channel_text") or channel_text
    except Exception as e:
        logger.warning(f"Failed to load channel settings from API: {e}")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Перейти в канал", url=channel_url)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")],
    ])

    if cover_media:
        try:
            await callback.message.delete()
        except Exception:
            pass
        try:
            await callback.bot.send_photo(
                chat_id=callback.from_user.id,
                photo=cover_media,
                caption=channel_text,
                parse_mode="HTML",
                reply_markup=kb,
            )
            return
        except Exception as e:
            logger.error(f"Failed to send channel cover photo: {e}")

    try:
        await callback.message.edit_text(channel_text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer(channel_text, parse_mode="HTML", reply_markup=kb)
