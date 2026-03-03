"""Главное меню бота — динамическая генерация из API (Single Source of Truth).

Кнопки загружаются из /api/v1/bot-buttons/public при каждом открытии меню.
Fallback — статические кнопки если API недоступен.
"""

import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)


def _build_default_buttons(show_free_trial: bool = True) -> list:
    """Статические кнопки главного меню — используются как fallback при недоступности API.

    Структура (как в AGENTS.md):
    Ряд 1: 🎁 Бесплатный период | 💳 Купить подписку
    Ряд 2: 🗂 Личный кабинет | 🎁 Получить бесплатно
    Ряд 3: 🤝 Реферальная программа | 📖 Инструкции по подключению
    Ряд 4: 🆘 Написать поддержку | 📢 Наш канал
    """
    buttons = []

    # Ряд 1
    row1 = []
    if show_free_trial:
        row1.append(InlineKeyboardButton(text="🎁 Бесплатный период", callback_data="free_trial"))
    row1.append(InlineKeyboardButton(text="💳 Купить подписку", callback_data="buy_subscription"))
    buttons.append(row1)

    # Ряд 2
    buttons.append([
        InlineKeyboardButton(text="🗂 Личный кабинет", callback_data="cabinet"),
        InlineKeyboardButton(text="🎁 Получить бесплатно", callback_data="get_free"),
    ])

    # Ряд 3
    buttons.append([
        InlineKeyboardButton(text="🤝 Реферальная программа", callback_data="partner"),
        InlineKeyboardButton(text="📖 Инструкции по подключению", callback_data="instructions"),
    ])

    # Ряд 4
    buttons.append([
        InlineKeyboardButton(text="🆘 Написать поддержку", callback_data="support"),
        InlineKeyboardButton(text="📢 Наш канал", callback_data="channel"),
    ])

    return buttons


def get_main_menu(show_free_trial: bool = True) -> InlineKeyboardMarkup:
    """Статическое главное меню — fallback при недоступности API."""
    return InlineKeyboardMarkup(inline_keyboard=_build_default_buttons(show_free_trial))


async def get_dynamic_main_menu(client, show_free_trial: bool = True) -> InlineKeyboardMarkup:
    """Динамическое главное меню — кнопки загружаются из API.

    Если API недоступен или вернул пустой список — используем fallback.
    Поддерживает url-кнопки (прямой редирект) и callback-кнопки.
    show_free_trial=False — скрывает кнопку бесплатного периода.
    """
    try:
        buttons_data = await client.get_bot_buttons()
        if not buttons_data:
            logger.warning("API returned empty bot buttons, using fallback")
            return get_main_menu(show_free_trial)

        # Группируем кнопки по рядам
        rows_dict: dict[int, list] = {}
        for btn in buttons_data:
            if not btn.get("is_active", True):
                continue

            callback_data = btn.get("callback_data", "")
            # Скрываем free_trial если пользователь уже использовал
            if not show_free_trial and callback_data == "free_trial":
                continue

            row = int(btn.get("row", 0))
            if row not in rows_dict:
                rows_dict[row] = []

            text = btn.get("text", "").strip()
            url = (btn.get("url") or "").strip()

            if not text:
                continue

            if url:
                # URL-кнопка — прямой редирект (без промежуточного текста)
                rows_dict[row].append(InlineKeyboardButton(text=text, url=url))
            elif callback_data:
                rows_dict[row].append(InlineKeyboardButton(text=text, callback_data=callback_data))
            else:
                logger.warning(f"Bot button '{text}' has no url or callback_data — skipping")

        if not rows_dict:
            logger.warning("All bot buttons filtered out, using fallback")
            return get_main_menu(show_free_trial)

        inline_keyboard = [rows_dict[r] for r in sorted(rows_dict.keys()) if rows_dict[r]]
        return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    except Exception as e:
        logger.error(f"Failed to load dynamic menu buttons: {e}", exc_info=True)
        return get_main_menu(show_free_trial)


def get_main_menu_with_admin() -> InlineKeyboardMarkup:
    """Меню для администратора — те же кнопки что и у пользователя."""
    return get_main_menu()
