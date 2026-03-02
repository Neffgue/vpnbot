"""Клавиатуры для подписок и личного кабинета — горизонтальные ряды"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any


def get_cabinet_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура личного кабинета — только Мои устройства по ТЗ."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📱 Мои устройства", callback_data="manage_devices"),
            ],
            [
                InlineKeyboardButton(text="💸 Продлить подписку", callback_data="buy_subscription"),
            ],
            [
                InlineKeyboardButton(text="🏠 На главную", callback_data="back_to_menu"),
            ],
        ]
    )


def get_subscription_keyboard(has_active: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура управления подпиской."""
    buttons = []
    if has_active:
        buttons.append([
            InlineKeyboardButton(text="♻️ Продлить", callback_data="renew_subscription"),
            InlineKeyboardButton(text="➕ Добавить устройство", callback_data="add_device"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="💳 Купить подписку", callback_data="buy_subscription"),
        ])
    buttons.append([
        InlineKeyboardButton(text="🏠 На главную", callback_data="back_to_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_device_keyboard(devices: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Управление устройствами — кнопка удаления + подключить + назад по ТЗ."""
    buttons = []
    for device in devices:
        device_id = device.get("id", "")
        model = device.get("model") or device.get("name") or device.get("server", "Устройство")
        buttons.append([InlineKeyboardButton(
            text=f"🗑️ Удалить устройство",
            callback_data=f"delete_device_{device_id}",
        )])
    buttons.append([
        InlineKeyboardButton(text="📲 Подключить устройство", callback_data="add_device"),
    ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_cabinet"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_add_device_keyboard() -> InlineKeyboardMarkup:
    """Выбор типа устройства — горизонтально по 2."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🤖 Android", callback_data="device_android"),
                InlineKeyboardButton(text="🍏 iPhone/iPad", callback_data="device_ios"),
            ],
            [
                InlineKeyboardButton(text="🪟 Windows", callback_data="device_windows"),
                InlineKeyboardButton(text="🍎 macOS", callback_data="device_macos"),
            ],
            [
                InlineKeyboardButton(text="🐧 Linux", callback_data="device_linux"),
                InlineKeyboardButton(text="📺 Android TV", callback_data="device_tv"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_devices"),
            ],
        ]
    )


def get_device_confirmation_keyboard(device_type: str) -> InlineKeyboardMarkup:
    """Подтверждение добавления устройства."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_device_{device_type}"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_device_types"),
            ],
        ]
    )
