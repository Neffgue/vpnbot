"""Клавиатуры для admin-панели бота (горизонтальные)"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_admin_menu() -> InlineKeyboardMarkup:
    """Главное меню админ-панели — кнопки горизонтально попарно."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
                InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
            ],
            [
                InlineKeyboardButton(text="🚫 Заблокировать", callback_data="admin_ban_user"),
                InlineKeyboardButton(text="✅ Разблокировать", callback_data="admin_unban_user"),
            ],
            [
                InlineKeyboardButton(text="💰 Добавить баланс", callback_data="admin_add_balance"),
                InlineKeyboardButton(text="👥 Все пользователи", callback_data="admin_users"),
            ],
            [
                InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main"),
            ],
        ]
    )


def get_admin_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, подтвердить", callback_data="admin_action_confirm"),
                InlineKeyboardButton(text="❌ Отменить", callback_data="admin_action_cancel"),
            ],
        ]
    )


def get_admin_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в меню админки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ В меню админа", callback_data="admin_menu"),
            ],
        ]
    )


def get_admin_action_keyboard(action: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения конкретного действия."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_{action}"),
                InlineKeyboardButton(text="❌ Отменить", callback_data="admin_action_cancel"),
            ],
        ]
    )
