"""Главное меню бота — вертикальная структура кнопок"""

import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)


def _build_default_buttons(show_free_trial: bool = True) -> list:
    """Строит список кнопок главного меню. Кнопка пробного периода скрывается если уже использован."""
    buttons = []
    if show_free_trial:
        buttons.append([
            InlineKeyboardButton(text="🎁 Бесплатный доступ", callback_data="free_trial"),
        ])
    buttons += [
        [
            InlineKeyboardButton(text="💸 Оплатить тариф", callback_data="buy_subscription"),
        ],
        [
            InlineKeyboardButton(text="👤 Личный кабинет", callback_data="cabinet"),
        ],
        [
            InlineKeyboardButton(text="🔗 Реферальная система", callback_data="partner"),
            InlineKeyboardButton(text="⚙️ Инструкция по подключению", callback_data="instructions"),
        ],
        [
            InlineKeyboardButton(text="👨‍💻 Поддержка", callback_data="support"),
        ],
        [
            InlineKeyboardButton(text="📢 Наш канал", callback_data="channel"),
        ],
    ]
    return buttons


def get_main_menu(show_free_trial: bool = True) -> InlineKeyboardMarkup:
    """
    Главное меню для всех пользователей (статичное, fallback).
    Кнопка Админ панели ОТСУТСТВУЕТ — доступ только через команду /admin.
    show_free_trial=False скрывает кнопку пробного периода.
    """
    return InlineKeyboardMarkup(inline_keyboard=_build_default_buttons(show_free_trial))


async def get_dynamic_main_menu(client, show_free_trial: bool = True) -> InlineKeyboardMarkup:
    """
    Загружает кнопки меню из БД через API.
    Если кнопки не настроены или API недоступен — возвращает статичное меню.
    show_free_trial=False скрывает кнопку пробного периода.
    """
    try:
        buttons_data = await client.get_bot_buttons()
        if not buttons_data:
            return get_main_menu(show_free_trial)

        # Группируем кнопки по рядам
        rows_dict: dict[int, list] = {}
        for btn in buttons_data:
            # Если кнопка — пробный период и он уже использован — пропускаем
            callback_data = btn.get("callback_data", "")
            if not show_free_trial and callback_data == "free_trial":
                continue

            row = int(btn.get("row", 0))
            if row not in rows_dict:
                rows_dict[row] = []
            # Создаём кнопку: url-кнопка или callback
            url = btn.get("url", "")
            text = btn.get("text", "")
            if not text:
                continue
            if url:
                rows_dict[row].append(InlineKeyboardButton(text=text, url=url))
            elif callback_data:
                rows_dict[row].append(InlineKeyboardButton(text=text, callback_data=callback_data))
            else:
                rows_dict[row].append(InlineKeyboardButton(text=text, callback_data="noop"))

        if not rows_dict:
            return get_main_menu(show_free_trial)

        inline_keyboard = [rows_dict[r] for r in sorted(rows_dict.keys()) if rows_dict[r]]
        return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    except Exception as e:
        logger.error(f"Failed to load dynamic menu buttons: {e}")
        return get_main_menu(show_free_trial)


def get_main_menu_with_admin() -> InlineKeyboardMarkup:
    """
    Меню для администраторов — точно такое же, без кнопки Админ.
    Доступ к админке только через /admin.
    """
    return get_main_menu()
