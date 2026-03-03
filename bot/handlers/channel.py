"""Channel subscription handler"""

import logging
import os
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.config import config
from bot.keyboards.inline_kb import get_link_button
from bot.utils.api_client import APIClient

logger = logging.getLogger(__name__)

router = Router()


CHANNEL_URL = "https://t.me/techwizardsru"


def _resolve_media(path_or_url: str):
    """Reads media from disk or returns URL string."""
    if not path_or_url:
        return None
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    _project_root = "/home/neffgue313/vpnbot"
    candidates = [
        path_or_url,
        os.path.join(_project_root, path_or_url.lstrip("/")),
        os.path.join(_project_root, "static", "uploads", os.path.basename(path_or_url)),
        "/app" + path_or_url,
        os.path.join("/app", path_or_url.lstrip("/")),
    ]
    from aiogram.types import BufferedInputFile
    for candidate in candidates:
        try:
            if os.path.isfile(candidate):
                with open(candidate, "rb") as f:
                    data = f.read()
                return BufferedInputFile(data, filename=os.path.basename(candidate))
        except Exception:
            continue
    logger.warning(f"Media file not found: {path_or_url}")
    return None


@router.callback_query(F.data == "channel")
async def channel_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle channel button — send URL button that opens channel."""
    await callback.answer()
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    # Получаем URL канала и обложку из настроек бота
    channel_url = CHANNEL_URL
    channel_text = "📢 <b>Наш канал</b>\n\nНажмите кнопку ниже:"
    cover_media = None
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            settings = await client.get_bot_settings()
            channel_url = settings.get("channel_url") or CHANNEL_URL
            raw_img = settings.get("channel_image") or ""
            cover_media = _resolve_media(raw_img) if raw_img else None
            texts = await client.get_all_bot_texts()
            channel_text = texts.get("channel_text") or channel_text
    except Exception:
        pass

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Перейти в канал", url=channel_url)],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
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
