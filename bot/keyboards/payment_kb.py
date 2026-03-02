"""Клавиатуры для оплаты — кнопки горизонтально"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any


def get_plan_keyboard(plans: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Выбор тарифного плана — кнопки попарно горизонтально."""
    buttons = []
    row = []
    for plan in plans:
        plan_id = plan.get("id", "")
        name = plan.get("name", "")
        price = plan.get("price", 0)
        btn = InlineKeyboardButton(
            text=f"📦 {name} — от {price:.0f}₽",
            callback_data=f"plan_{plan_id}",
        )
        row.append(btn)
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_period_keyboard() -> InlineKeyboardMarkup:
    """Выбор периода — 2 кнопки в ряд."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="7 дней", callback_data="period_7"),
                InlineKeyboardButton(text="1 месяц", callback_data="period_30"),
            ],
            [
                InlineKeyboardButton(text="3 месяца", callback_data="period_90"),
                InlineKeyboardButton(text="6 месяцев", callback_data="period_180"),
            ],
            [
                InlineKeyboardButton(text="12 месяцев", callback_data="period_365"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_plans"),
            ],
        ]
    )


def get_payment_method_keyboard() -> InlineKeyboardMarkup:
    """Выбор способа оплаты."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐ Telegram Stars", callback_data="pay_stars"),
                InlineKeyboardButton(text="💳 YooKassa (карта/СБП)", callback_data="pay_yookassa"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_payment"),
            ],
        ]
    )


def get_payment_confirmation_keyboard(price: float) -> InlineKeyboardMarkup:
    """Подтверждение оплаты."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"💳 Оплатить {price:.0f}₽", callback_data="confirm_payment"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_periods"),
            ],
        ]
    )


def get_subscription_link_keyboard(link: str) -> InlineKeyboardMarkup:
    """Клавиатура с ссылкой подписки."""
    buttons = []
    if link and link.startswith("http"):
        buttons.append([
            InlineKeyboardButton(text="🔗 Открыть в Happ", url=link),
        ])
    buttons.extend([
        [InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data="copy_subscription_link")],
        [
            InlineKeyboardButton(text="📖 Инструкция", callback_data="instructions"),
            InlineKeyboardButton(text="🏠 На главную", callback_data="back_to_menu"),
        ],
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
