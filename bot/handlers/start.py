"""Start command handler"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from bot.config import config
from bot.keyboards.main_menu import get_main_menu, get_dynamic_main_menu
from bot.utils.api_client import APIClient
from bot.utils.formatters import get_fallback_texts

logger = logging.getLogger(__name__)

router = Router()


def _resolve_media(path_or_url: str):
    """
    Преобразует путь к медиа в BufferedInputFile (локальный файл) или строку URL (https://).
    Возвращает None если файл не найден или путь пустой.
    """
    import os
    from aiogram.types import BufferedInputFile
    if not path_or_url:
        return None
    # Уже полный URL — возвращаем как есть (строка)
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    # Локальный путь — читаем с диска и оборачиваем в BufferedInputFile
    _project_root = "/home/neffgue313/vpnbot"
    candidates = [
        path_or_url,
        os.path.join(_project_root, path_or_url.lstrip("/")),
        os.path.join(_project_root, "static", "uploads", os.path.basename(path_or_url)),
        "/app" + path_or_url,
        os.path.join("/app", path_or_url.lstrip("/")),
    ]
    for candidate in candidates:
        try:
            if os.path.isfile(candidate):
                with open(candidate, "rb") as f:
                    data = f.read()
                filename = os.path.basename(candidate)
                return BufferedInputFile(data, filename=filename)
        except Exception:
            continue
    logger.warning(f"Media file not found: {path_or_url}")
    return None


async def _get_welcome_data(client: APIClient):
    """Получить текст приветствия и картинку из настроек бота."""
    welcome_text = None
    welcome_photo = None
    try:
        texts = await client.get_all_bot_texts()
        welcome_text = texts.get("welcome")
    except Exception:
        pass
    try:
        settings = await client.get_bot_settings()
        raw = settings.get("welcome_image") or settings.get("welcome_photo") or ""
        welcome_photo = _resolve_media(raw)
    except Exception:
        pass
    if not welcome_text:
        fallback = get_fallback_texts()
        welcome_text = fallback.get("welcome", "👋 Добро пожаловать!")
    # Fallback to env if not set in DB
    if not welcome_photo:
        env_photo = config.telegram.welcome_photo or None
        if env_photo:
            welcome_photo = _resolve_media(env_photo) or env_photo
    return welcome_text, welcome_photo


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """
    Handle /start command with optional referral code
    Format: /start ref_CODE
    """
    
    user_id = message.from_user.id
    
    # Clear any previous state
    await state.clear()
    
    # Extract referral code if provided
    # Supported formats: /start REF_XXXXX  or  /start refXXXXX
    args = message.text.split()
    ref_code = None
    if len(args) > 1:
        raw = args[1]
        # Normalise: strip known prefixes so backend always gets the raw code
        ref_code = raw.removeprefix("REF_") if raw.upper().startswith("REF_") else raw
    
    welcome_text = None
    welcome_photo = None
    keyboard = None

    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            # Register user with referral code if provided
            try:
                await client.register_user(
                    user_id=user_id,
                    username=message.from_user.username or "",
                    first_name=message.from_user.first_name or "",
                    ref_code=ref_code,
                )
                if ref_code:
                    logger.info(f"User {user_id} registered with referral code: {ref_code}")
            except Exception as e:
                logger.error(f"Error registering user: {e}")

            welcome_text, welcome_photo = await _get_welcome_data(client)

            # Проверяем использован ли пробный период — скрываем кнопку если да
            show_free_trial = True
            try:
                trial_status = await client.check_free_trial_used(user_id)
                show_free_trial = not trial_status.get("already_used", False)
            except Exception:
                pass

            keyboard = await get_dynamic_main_menu(client, show_free_trial=show_free_trial)
    except Exception as e:
        logger.error(f"Error during start: {e}")

    if not welcome_text:
        fallback = get_fallback_texts()
        welcome_text = fallback.get("welcome", "👋 Добро пожаловать!")
    if keyboard is None:
        keyboard = get_main_menu()

    # Send welcome photo if configured, otherwise plain text
    if welcome_photo:
        try:
            await message.answer_photo(
                photo=welcome_photo,
                caption=welcome_text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            return
        except Exception as e:
            logger.error(f"Failed to send welcome photo: {e}")

    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle back to menu button"""

    # Clear state
    await state.clear()

    welcome_text = None
    welcome_photo = None
    keyboard = None

    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            welcome_text, welcome_photo = await _get_welcome_data(client)

            # Проверяем использован ли пробный период — скрываем кнопку если да
            show_free_trial = True
            try:
                trial_status = await client.check_free_trial_used(callback.from_user.id)
                show_free_trial = not trial_status.get("already_used", False)
            except Exception:
                pass

            keyboard = await get_dynamic_main_menu(client, show_free_trial=show_free_trial)
    except Exception as e:
        logger.error(f"Error fetching menu data: {e}")

    if not welcome_text:
        fallback = get_fallback_texts()
        welcome_text = fallback.get("welcome", "👋 Добро пожаловать!")
    if keyboard is None:
        keyboard = get_main_menu()

    if welcome_photo:
        # Can't edit a photo into a text message — delete old and send new
        try:
            await callback.message.delete()
        except Exception:
            pass
        try:
            await callback.bot.send_photo(
                chat_id=callback.from_user.id,
                photo=welcome_photo,
                caption=welcome_text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            await callback.answer()
            return
        except Exception as e:
            logger.error(f"Failed to send welcome photo: {e}")

    try:
        await callback.message.edit_text(
            welcome_text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except Exception:
        await callback.message.answer(
            welcome_text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    await callback.answer()
