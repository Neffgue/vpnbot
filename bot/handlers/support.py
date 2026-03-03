"""Support handler"""

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


SUPPORT_URL = "https://t.me/TechWizardsSupport"


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


@router.callback_query(F.data == "support")
async def support_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle support button — send URL button that opens support chat."""
    await callback.answer()
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    # Получаем URL поддержки и обложку из настроек бота
    support_url = SUPPORT_URL
    support_text = "💬 <b>Поддержка</b>\n\nНажмите кнопку ниже:"
    cover_media = None
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            settings = await client.get_bot_settings()
            support_url = settings.get("support_url") or SUPPORT_URL
            raw_img = settings.get("support_image") or ""
            cover_media = _resolve_media(raw_img) if raw_img else None
            texts = await client.get_all_bot_texts()
            support_text = texts.get("support_text") or support_text
    except Exception:
        pass

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать в поддержку", url=support_url)],
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
