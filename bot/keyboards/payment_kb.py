"""Клавиатуры для платёжного флоу."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any


def get_plan_keyboard(plans: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Клавиатура выбора тарифного плана из списка планов."""
    buttons = []
    row = []
    for plan in plans:
        plan_name = plan.get("plan_name") or plan.get("id", "")
        name = plan.get("name") or plan_name
        price = float(plan.get("price_rub") or plan.get("price") or 0)
        devices = int(plan.get("device_limit") or plan.get("devices") or 1)
        btn = InlineKeyboardButton(
            text=f"{name} ({devices} уст.) — от {price:.0f} ₽",
            callback_data=f"plan_{plan_name}",
        )
        row.append(btn)
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_period_keyboard() -> InlineKeyboardMarkup:
    """Статическая клавиатура периодов — используется как fallback.

    Динамическая версия строится в payment.py из реальных данных API.
    """
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
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_plans"),
            ],
        ]
    )


def get_payment_method_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора метода оплаты."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐ Telegram Stars", callback_data="pay_stars"),
                InlineKeyboardButton(text="💳 YooKassa (Карта/СБП)", callback_data="pay_yookassa"),
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_payment"),
            ],
        ]
    )


def get_payment_confirmation_keyboard(price: float) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения оплаты."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"💳 Оплатить {price:.0f} ₽",
                    callback_data="confirm_payment",
                ),
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_periods"),
            ],
        ]
    )


def get_subscription_link_keyboard(link: str) -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой перехода по ссылке подписки."""
    buttons = []
    if link and link.startswith("http"):
        buttons.append([
            InlineKeyboardButton(text="📲 Открыть в Happ", url=link),
        ])
    buttons.extend([
        [InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data="copy_subscription_link")],
        [
            InlineKeyboardButton(text="📖 Инструкции", callback_data="instructions"),
            InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_menu"),
        ],
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
