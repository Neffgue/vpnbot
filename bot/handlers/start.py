"""Start command handler — тексты и фото из API (Single Source of Truth)."""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from bot.config import config
from bot.keyboards.main_menu import get_main_menu, get_dynamic_main_menu
from bot.utils.api_client import APIClient
from bot.utils.media import resolve_media

logger = logging.getLogger(__name__)

router = Router()

FALLBACK_WELCOME = (
    "👋 <b>Добро пожаловать в VPN бот!</b>\n\n"
    "Здесь вы можете купить подписку на быстрый и надёжный VPN."
)


async def _get_welcome_data(client: APIClient):
    """Загрузить приветственный текст и фото из API.

    Возвращает (welcome_text, welcome_photo | None).
    Никогда не бросает исключений — при ошибке возвращает fallback.
    """
    welcome_text = None
    welcome_photo = None

    try:
        texts = await client.get_all_bot_texts()
        if texts:
            welcome_text = texts.get("welcome") or texts.get("welcome_text")
    except Exception as e:
        logger.warning(f"Failed to load welcome text from API: {e}")

    try:
        settings = await client.get_bot_settings()
        if settings:
            raw = (
                settings.get("welcome_image")
                or settings.get("welcome_photo")
                or ""
            )
            if raw:
                welcome_photo = resolve_media(raw)
    except Exception as e:
        logger.warning(f"Failed to load welcome photo from API: {e}")

    if not welcome_text:
        # Fallback из env (если задан)
        env_text = getattr(config, "welcome_text", None)
        welcome_text = env_text or FALLBACK_WELCOME

    if not welcome_photo:
        env_photo = getattr(config.telegram, "welcome_photo", None) if hasattr(config, "telegram") else None
        if env_photo:
            welcome_photo = resolve_media(env_photo) or env_photo

    return welcome_text, welcome_photo


async def _send_welcome(
    message_or_bot,
    chat_id: int,
    welcome_text: str,
    welcome_photo,
    keyboard,
    is_callback: bool = False,
    original_message=None,
):
    """Отправить приветственное сообщение (с фото или без).

    Используется как в /start так и в back_to_menu.
    """
    if welcome_photo:
        if is_callback and original_message:
            try:
                await original_message.delete()
            except Exception:
                pass
        try:
            if is_callback:
                await message_or_bot.send_photo(
                    chat_id=chat_id,
                    photo=welcome_photo,
                    caption=welcome_text,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
            else:
                await original_message.answer_photo(
                    photo=welcome_photo,
                    caption=welcome_text,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
            return
        except Exception as e:
            logger.error(f"Failed to send welcome photo: {e}")

    # Fallback — текстовое сообщение
    if is_callback and original_message:
        try:
            await original_message.edit_text(
                welcome_text, parse_mode="HTML", reply_markup=keyboard
            )
            return
        except Exception:
            pass
        try:
            await message_or_bot.send_message(
                chat_id=chat_id,
                text=welcome_text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except Exception as e:
            logger.error(f"Failed to send welcome text: {e}")
    else:
        try:
            await original_message.answer(
                welcome_text, parse_mode="HTML", reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Failed to answer with welcome text: {e}")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Обработчик команды /start с поддержкой реферального кода (/start ref_CODE)."""
    await state.clear()

    # Извлечь реферальный код
    args = message.text.split()
    ref_code = None
    if len(args) > 1:
        raw = args[1]
        ref_code = raw.removeprefix("REF_") if raw.upper().startswith("REF_") else raw

    welcome_text = None
    welcome_photo = None
    keyboard = None

    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            welcome_text, welcome_photo = await _get_welcome_data(client)

            # Зарегистрировать пользователя + реферал
            try:
                await client.get_or_create_user(
                    telegram_id=message.from_user.id,
                    username=message.from_user.username,
                    full_name=message.from_user.full_name,
                    ref_code=ref_code,
                )
            except Exception as e:
                logger.warning(f"Failed to register user {message.from_user.id}: {e}")

            # Показать/скрыть кнопку бесплатного периода
            show_free_trial = True
            try:
                trial_status = await client.check_free_trial_used(message.from_user.id)
                show_free_trial = not trial_status.get("already_used", False)
            except Exception:
                pass

            keyboard = await get_dynamic_main_menu(client, show_free_trial=show_free_trial)
    except Exception as e:
        logger.error(f"Error during /start: {e}", exc_info=True)

    if not welcome_text:
        welcome_text = FALLBACK_WELCOME
    if keyboard is None:
        keyboard = get_main_menu()

    await _send_welcome(
        message_or_bot=None,
        chat_id=message.from_user.id,
        welcome_text=welcome_text,
        welcome_photo=welcome_photo,
        keyboard=keyboard,
        is_callback=False,
        original_message=message,
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик кнопки ◀️ Назад в главное меню."""
    await state.clear()
    await callback.answer()

    welcome_text = None
    welcome_photo = None
    keyboard = None

    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            welcome_text, welcome_photo = await _get_welcome_data(client)

            show_free_trial = True
            try:
                trial_status = await client.check_free_trial_used(callback.from_user.id)
                show_free_trial = not trial_status.get("already_used", False)
            except Exception:
                pass

            keyboard = await get_dynamic_main_menu(client, show_free_trial=show_free_trial)
    except Exception as e:
        logger.error(f"Error fetching menu data on back_to_menu: {e}", exc_info=True)

    if not welcome_text:
        welcome_text = FALLBACK_WELCOME
    if keyboard is None:
        keyboard = get_main_menu()

    await _send_welcome(
        message_or_bot=callback.bot,
        chat_id=callback.from_user.id,
        welcome_text=welcome_text,
        welcome_photo=welcome_photo,
        keyboard=keyboard,
        is_callback=True,
        original_message=callback.message,
    )
