"""Support handler — прямой редирект по URL из настроек БД."""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.config import config
from bot.utils.api_client import APIClient
from bot.utils.media import resolve_media, get_section_media

logger = logging.getLogger(__name__)

router = Router()

# Fallback — используется если API недоступен
SUPPORT_URL_FALLBACK = "https://t.me/TechWizardsSupport"


@router.callback_query(F.data == "support")
async def support_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Кнопка Поддержка — показывает URL-кнопку для перехода в чат поддержки.

    URL берётся из настроек БД (поле support_url).
    Если задана картинка (support_image) — отправляем фото с caption.
    Если картинки нет — отправляем текстовое сообщение.
    Кнопки: [Написать в поддержку (url)] [◀️ Назад]
    """
    await callback.answer()

    support_url = SUPPORT_URL_FALLBACK
    support_text = "🆘 <b>Поддержка</b>\n\nНажмите кнопку ниже чтобы написать нам:"
    cover_media = None

    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            settings = await client.get_bot_settings()
            if settings:
                support_url = settings.get("support_url") or SUPPORT_URL_FALLBACK

            texts = await client.get_all_bot_texts()
            if texts:
                support_text = texts.get("support_text") or support_text

            # Берём медиа: сначала из settings, потом из image_url кнопки "support"
            cover_media = await get_section_media(client, "support_image", "support")
    except Exception as e:
        logger.warning(f"Failed to load support settings from API: {e}")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆘 Написать в поддержку", url=support_url)],
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
                caption=support_text,
                parse_mode="HTML",
                reply_markup=kb,
            )
            return
        except Exception as e:
            logger.error(f"Failed to send support cover photo: {e}")

    try:
        await callback.message.edit_text(support_text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer(support_text, parse_mode="HTML", reply_markup=kb)
