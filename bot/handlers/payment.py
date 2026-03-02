"""Payment flow handler"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, LabeledPrice, ShippingOption
from aiogram.fsm.context import FSMContext

from bot.config import config
from bot.keyboards.main_menu import get_main_menu
from bot.keyboards.payment_kb import (
    get_plan_keyboard,
    get_period_keyboard,
    get_payment_method_keyboard,
    get_payment_confirmation_keyboard,
    get_subscription_link_keyboard,
)
from bot.states.payment_states import PaymentStates
from bot.utils.api_client import APIClient
from bot.utils.formatters import format_price, format_payment_confirmation, get_fallback_texts

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data == "buy_subscription")
async def buy_subscription_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handle subscription purchase start
    Show available plans (Соло / Семейный)
    """
    await callback.answer()

    plan_text = (
        "⚡️ <b>Выберите тариф из предложенных</b>\n\n"
        "Каждый тариф позволяет подключить определённое количество устройств к VPN.\n\n"
        "В любой момент вы сможете улучшить свой тариф на большее количество устройств!"
    )

    # Статичные тарифы: Соло и Семейный
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Соло - 1 устройство", callback_data="plan_solo")],
        [InlineKeyboardButton(text="👨‍👩‍👧‍👦 Семейный - 5 устройств", callback_data="plan_family")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")],
    ])

    try:
        await callback.message.edit_text(plan_text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        await callback.message.answer(plan_text, parse_mode="HTML", reply_markup=keyboard)

    await state.set_state(PaymentStates.waiting_plan_selection)


# Цены для тарифов
PLAN_PRICES = {
    "solo": {
        "name": "👤 Минимальный (1 устройство)",
        "devices": 1,
        "prices": {7: 90, 30: 150, 90: 400, 180: 760, 365: 1450},
    },
    "family": {
        "name": "👨‍👩‍👧‍👦 Семейный (5 устройств)",
        "devices": 5,
        "prices": {7: 150, 30: 250, 90: 650, 180: 1200, 365: 2300},
    },
}


def _get_period_keyboard_with_prices(plan_key: str) -> "InlineKeyboardMarkup":
    """Клавиатура выбора периода с ценами из PLAN_PRICES."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    prices = PLAN_PRICES.get(plan_key, PLAN_PRICES["solo"])["prices"]
    period_labels = {7: "7 дней", 30: "1 месяц", 90: "3 месяца", 180: "6 месяцев", 365: "12 месяцев"}
    rows = []
    row = []
    for days, price in prices.items():
        btn = InlineKeyboardButton(
            text=f"{period_labels[days]} — {price} рублей",
            callback_data=f"period_{days}",
        )
        row.append(btn)
        if len(row) == 1:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="buy_subscription")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("plan_"), PaymentStates.waiting_plan_selection)
async def select_plan(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handle plan selection (solo / family)
    Show period selection with prices in rubles
    """
    await callback.answer()

    plan_key = callback.data.replace("plan_", "")  # "solo" or "family"
    plan_info = PLAN_PRICES.get(plan_key, PLAN_PRICES["solo"])

    period_text = (
        "Выберите период, на который хотите оформить подписку\n\n"
        "Учтите! Чем больше период, тем ниже цена 💵\n\n"
        f"Выбран тариф - {plan_info['name']}"
    )

    try:
        await callback.message.edit_text(
            period_text,
            parse_mode="HTML",
            reply_markup=_get_period_keyboard_with_prices(plan_key),
        )
    except Exception:
        await callback.message.answer(
            period_text,
            parse_mode="HTML",
            reply_markup=_get_period_keyboard_with_prices(plan_key),
        )

    await state.update_data(selected_plan={"key": plan_key, **plan_info})
    await state.set_state(PaymentStates.waiting_period_selection)


@router.callback_query(F.data.startswith("period_"), PaymentStates.waiting_period_selection)
async def select_period(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handle period selection — show payment method choice
    """
    await callback.answer()

    period_str = callback.data.replace("period_", "")
    period_days = int(period_str)

    data = await state.get_data()
    selected_plan = data.get("selected_plan", {})
    plan_key = selected_plan.get("key", "solo")
    plan_prices = selected_plan.get("prices", PLAN_PRICES["solo"]["prices"])
    price = plan_prices.get(period_days, 150)

    payment_text = (
        "💸 <b>Выберите способ оплаты для продолжения:</b>\n\n"
        "😁 Советуем оплачивать подписку через <b>СБП</b> — это дешевле и быстрее."
    )

    await state.update_data(
        period_days=period_days,
        price=price,
        yookassa_link="",
        invoice_payload=f"vpn_{plan_key}_{period_days}",
    )
    await state.set_state(PaymentStates.waiting_payment_method)

    try:
        await callback.message.edit_text(
            payment_text,
            parse_mode="HTML",
            reply_markup=get_payment_method_keyboard(),
        )
    except Exception:
        await callback.message.answer(
            payment_text,
            parse_mode="HTML",
            reply_markup=get_payment_method_keyboard(),
        )


@router.callback_query(F.data == "pay_stars", PaymentStates.waiting_payment_method)
async def pay_with_stars(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handle Telegram Stars payment
    Send invoice to user
    """
    await callback.answer()
    
    data = await state.get_data()
    selected_plan = data.get("selected_plan", {})
    period_days = data.get("period_days", 0)
    price = data.get("price", 0)
    invoice_payload = data.get("invoice_payload", "")
    
    user_id = callback.from_user.id
    bot = callback.bot
    
    try:
        # Send invoice for Telegram Stars payment
        prices = [LabeledPrice(label="Подписка VPN", amount=int(price * 100))]
        
        await bot.send_invoice(
            chat_id=user_id,
            title=selected_plan.get("name", "VPN Subscription"),
            description=f"Подписка на {period_days} дней",
            payload=invoice_payload or f"vpn_sub_{user_id}_{period_days}",
            provider_token="",  # Empty for Telegram Stars
            currency="XTR",  # Telegram Stars currency code
            prices=prices,
            start_parameter="vpn_subscription",
        )
        
        try:
            await callback.message.edit_text(
                "⭐ Счёт для оплаты отправлен. Нажмите кнопку <b>Оплатить</b> в сообщении выше.",
                reply_markup=get_main_menu()
            )
        except Exception:
            await callback.message.answer(
                "⭐ Счёт для оплаты отправлен. Нажмите кнопку <b>Оплатить</b> в сообщении выше.",
                reply_markup=get_main_menu()
            )
    
    except Exception as e:
        logger.error(f"Error sending invoice: {e}")
        
        try:
            await callback.message.edit_text(
                "❌ Ошибка при отправке счёта. Попробуйте позже.",
                reply_markup=get_main_menu()
            )
        except Exception:
            await callback.message.answer(
                "❌ Ошибка при отправке счёта. Попробуйте позже.",
                reply_markup=get_main_menu()
            )


@router.callback_query(F.data == "pay_yookassa", PaymentStates.waiting_payment_method)
async def pay_with_yookassa(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handle YooKassa payment
    Send payment link
    """
    await callback.answer()
    
    data = await state.get_data()
    yookassa_link = data.get("yookassa_link", "")
    
    if not yookassa_link:
        try:
            await callback.message.edit_text(
                "❌ Ссылка на оплату недоступна. Попробуйте позже.",
                reply_markup=get_main_menu()
            )
        except Exception:
            await callback.message.answer(
                "❌ Ссылка на оплату недоступна. Попробуйте позже.",
                reply_markup=get_main_menu()
            )
        return
    
    try:
        await callback.message.edit_text(
            "💳 <b>Перейдите по ссылке для оплаты через YooKassa</b>\n\n"
            "Доступные способы оплаты:\n"
            "• Карта Visa/Mastercard/Мир\n"
            "• СБП (переводы по номеру телефона)\n"
            "• Яндекс.Касса\n"
            "• Apple Pay, Google Pay\n\n"
            "После успешной оплаты вам будет отправлена ссылка для подключения.",
            reply_markup=get_subscription_link_keyboard(yookassa_link)
        )
    except Exception:
        await callback.message.answer(
            "💳 <b>Перейдите по ссылке для оплаты через YooKassa</b>\n\n"
            "Доступные способы оплаты:\n"
            "• Карта Visa/Mastercard/Мир\n"
            "• СБП (переводы по номеру телефона)\n"
            "• Яндекс.Касса\n"
            "• Apple Pay, Google Pay\n\n"
            "После успешной оплаты вам будет отправлена ссылка для подключения.",
            reply_markup=get_subscription_link_keyboard(yookassa_link)
        )


@router.callback_query(F.data == "back_to_plans")
async def back_to_plans(callback: CallbackQuery, state: FSMContext) -> None:
    """Go back from period selection to plan selection"""
    await callback.answer()

    # Статичные тарифы — формируем клавиатуру напрямую, как в buy_subscription_handler
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Соло - 1 устройство", callback_data="plan_solo")],
        [InlineKeyboardButton(text="👨‍👩‍👧‍👦 Семейный - 5 устройств", callback_data="plan_family")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")],
    ])

    plan_text = (
        "⚡️ <b>Выберите тариф из предложенных</b>\n\n"
        "Каждый тариф позволяет подключить определённое количество устройств к VPN.\n\n"
        "В любой момент вы сможете улучшить свой тариф на большее количество устройств!"
    )

    try:
        await callback.message.edit_text(plan_text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        await callback.message.answer(plan_text, parse_mode="HTML", reply_markup=keyboard)

    await state.set_state(PaymentStates.waiting_plan_selection)


@router.callback_query(F.data == "back_to_payment")
async def back_to_payment(callback: CallbackQuery, state: FSMContext) -> None:
    """Go back from payment method to period selection"""
    await callback.answer()

    data = await state.get_data()
    selected_plan = data.get("selected_plan", {})
    plan_key = selected_plan.get("key", "solo")

    period_text = (
        "Выберите период, на который хотите оформить подписку\n\n"
        "Учтите! Чем больше период, тем ниже цена 💵\n\n"
        f"Выбран тариф - {selected_plan.get('name', 'Соло')}"
    )

    try:
        await callback.message.edit_text(
            period_text,
            parse_mode="HTML",
            reply_markup=_get_period_keyboard_with_prices(plan_key),
        )
    except Exception:
        await callback.message.answer(
            period_text,
            parse_mode="HTML",
            reply_markup=_get_period_keyboard_with_prices(plan_key),
        )

    await state.set_state(PaymentStates.waiting_period_selection)


@router.callback_query(F.data == "back_to_periods")
async def back_to_periods(callback: CallbackQuery, state: FSMContext) -> None:
    """Go back from payment confirmation to period selection"""
    await callback.answer()

    data = await state.get_data()
    selected_plan = data.get("selected_plan", {})
    plan_key = selected_plan.get("key", "solo")

    period_text = (
        "Выберите период, на который хотите оформить подписку\n\n"
        "Учтите! Чем больше период, тем ниже цена 💵\n\n"
        f"Выбран тариф - {selected_plan.get('name', 'Соло')}"
    )

    try:
        await callback.message.edit_text(
            period_text,
            parse_mode="HTML",
            reply_markup=_get_period_keyboard_with_prices(plan_key),
        )
    except Exception:
        await callback.message.answer(
            period_text,
            parse_mode="HTML",
            reply_markup=_get_period_keyboard_with_prices(plan_key),
        )

    await state.set_state(PaymentStates.waiting_period_selection)


@router.callback_query(F.data == "confirm_payment")
async def confirm_payment_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle confirm payment button — redirect to payment method selection"""
    await callback.answer()
    
    data = await state.get_data()
    selected_plan = data.get("selected_plan", {})
    period_days = data.get("period_days", 0)
    price = data.get("price", 0)

    confirmation_text = format_payment_confirmation(
        plan_name=selected_plan.get("name", "VPN"),
        period_days=period_days,
        price=price,
        currency="RUB"
    )

    try:
        await callback.message.edit_text(
            confirmation_text,
            reply_markup=get_payment_method_keyboard()
        )
    except Exception:
        await callback.message.answer(
            confirmation_text,
            reply_markup=get_payment_method_keyboard()
        )

    await state.set_state(PaymentStates.waiting_payment_method)
