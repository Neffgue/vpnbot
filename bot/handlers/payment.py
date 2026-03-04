"""Payment flow handler — тарифы и цены загружаются из БД через API (Single Source of Truth)."""

import logging
from typing import Optional
from aiogram import Router, F
from aiogram.types import CallbackQuery, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.config import config
from bot.keyboards.main_menu import get_main_menu
from bot.keyboards.payment_kb import (
    get_payment_method_keyboard,
    get_subscription_link_keyboard,
)
from bot.states.payment_states import PaymentStates
from bot.utils.api_client import APIClient
from bot.utils.formatters import format_payment_confirmation
from bot.utils.media import resolve_media

logger = logging.getLogger(__name__)

router = Router()

# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции для работы с тарифами из API
# ─────────────────────────────────────────────────────────────────────────────

PERIOD_LABELS = {
    7: "7 дней",
    14: "14 дней",
    30: "1 месяц",
    60: "2 месяца",
    90: "3 месяца",
    180: "6 месяцев",
    365: "12 месяцев",
}

FALLBACK_PLANS = [
    {
        "id": "solo",
        "plan_name": "solo",
        "name": "👤 Соло (1 устройство)",
        "devices": 1,
        "period_days": 30,
        "price": 150,
        "is_active": True,
    },
    {
        "id": "family",
        "plan_name": "family",
        "name": "👨‍👩‍👧‍👦 Семейный (5 устройств)",
        "devices": 5,
        "period_days": 30,
        "price": 250,
        "is_active": True,
    },
]


async def _fetch_plans(api: APIClient) -> list:
    """Загрузить тарифы из API. При ошибке — вернуть fallback-значения."""
    try:
        plans = await api.get_subscription_plans()
        if plans:
            return [p for p in plans if p.get("is_active", True)]
    except Exception as e:
        logger.warning(f"Failed to fetch plans from API, using fallback: {e}")
    return FALLBACK_PLANS


def _group_plans_by_name(plans: list) -> dict:
    """Сгруппировать тарифы по plan_name → список периодов.

    Поддерживает оба варианта имени поля цены:
    - price_rub (схема БД PlanPrice)
    - price (общий вариант)
    """
    grouped: dict = {}
    for plan in plans:
        key = plan.get("plan_name") or plan.get("id") or "solo"
        if key not in grouped:
            grouped[key] = {
                "key": key,
                "name": plan.get("name", key.capitalize()),
                "devices": plan.get("devices", plan.get("device_limit", 1)),
                "periods": {},
            }
        days = int(plan.get("period_days", 30))
        # Поддержка обоих полей: price_rub (из БД) и price (общий)
        price = float(
            plan.get("price_rub")
            or plan.get("price")
            or 0
        )
        grouped[key]["periods"][days] = price
    return grouped


def _build_plan_keyboard(grouped: dict) -> InlineKeyboardMarkup:
    """Клавиатура выбора тарифного плана (строки = отдельные планы)."""
    rows = []
    for key, info in grouped.items():
        label = f"{info['name']} — {info['devices']} уст."
        rows.append([InlineKeyboardButton(text=label, callback_data=f"plan_{key}")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_period_keyboard(plan_key: str, periods: dict) -> InlineKeyboardMarkup:
    """Клавиатура выбора периода подписки с ценами из БД."""
    rows = []
    for days in sorted(periods.keys()):
        price = periods[days]
        label_day = PERIOD_LABELS.get(int(days), f"{days} дней")
        label = f"{label_day} — {int(price)} ₽"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"period_{days}")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_plans")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────────────────────────────────────────────────────────────────
# Handlers
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "buy_subscription")
async def buy_subscription_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать список тарифных планов, загруженных из БД."""
    await callback.answer()

    async with APIClient(config.API_BASE_URL) as api:
        plans = await _fetch_plans(api)

    grouped = _group_plans_by_name(plans)

    # Сохраняем сгруппированные планы в state для последующих шагов
    await state.update_data(grouped_plans=grouped)
    await state.set_state(PaymentStates.waiting_plan_selection)

    plan_text = (
        "⚡️ <b>Выберите тариф из предложенных</b>\n\n"
        "Каждый тариф позволяет подключить определённое количество устройств к VPN.\n\n"
        "В любой момент вы сможете улучшить свой тариф на большее количество устройств!"
    )

    try:
        await callback.message.edit_text(
            plan_text, parse_mode="HTML", reply_markup=_build_plan_keyboard(grouped)
        )
    except Exception:
        await callback.message.answer(
            plan_text, parse_mode="HTML", reply_markup=_build_plan_keyboard(grouped)
        )


@router.callback_query(F.data.startswith("plan_"), PaymentStates.waiting_plan_selection)
async def select_plan(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор тарифного плана — показываем периоды с ценами из БД."""
    await callback.answer()

    plan_key = callback.data.replace("plan_", "")
    data = await state.get_data()
    grouped = data.get("grouped_plans", {})

    if not grouped:
        # Перезагружаем если state пустой
        async with APIClient(config.API_BASE_URL) as api:
            plans = await _fetch_plans(api)
        grouped = _group_plans_by_name(plans)
        await state.update_data(grouped_plans=grouped)

    plan_info = grouped.get(plan_key)
    if not plan_info:
        await callback.answer("Тариф не найден. Попробуйте ещё раз.", show_alert=True)
        return

    await state.update_data(selected_plan_key=plan_key, selected_plan_info=plan_info)
    await state.set_state(PaymentStates.waiting_period_selection)

    period_text = (
        f"📅 <b>Выберите период подписки</b>\n\n"
        f"Тариф: <b>{plan_info['name']}</b>\n"
        f"Устройств: <b>{plan_info['devices']}</b>\n\n"
        "Учтите! Чем больше период, тем ниже цена 💵"
    )

    try:
        await callback.message.edit_text(
            period_text,
            parse_mode="HTML",
            reply_markup=_build_period_keyboard(plan_key, plan_info["periods"]),
        )
    except Exception:
        await callback.message.answer(
            period_text,
            parse_mode="HTML",
            reply_markup=_build_period_keyboard(plan_key, plan_info["periods"]),
        )


@router.callback_query(F.data.startswith("period_"), PaymentStates.waiting_period_selection)
async def select_period(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор периода — показываем подтверждение с ценой из БД."""
    await callback.answer()

    period_days = int(callback.data.replace("period_", ""))
    data = await state.get_data()
    plan_key = data.get("selected_plan_key", "solo")
    plan_info = data.get("selected_plan_info", {})
    periods = plan_info.get("periods", {})
    price = periods.get(period_days, periods.get(str(period_days), 150))

    await state.update_data(
        period_days=period_days,
        price=price,
        yookassa_link="",
        invoice_payload=f"vpn_{plan_key}_{period_days}",
    )
    await state.set_state(PaymentStates.waiting_payment_method)

    payment_text = format_payment_confirmation(
        plan_name=plan_info.get("name", "VPN"),
        period_days=period_days,
        price=price,
        currency="RUB",
    )

    # Показываем картинку тарифа если есть
    image_url = plan_info.get("image_url", "")
    cover = resolve_media(image_url) if image_url else None

    if cover:
        try:
            await callback.message.delete()
        except Exception:
            pass
        try:
            await callback.bot.send_photo(
                chat_id=callback.from_user.id,
                photo=cover,
                caption=payment_text,
                parse_mode="HTML",
                reply_markup=get_payment_method_keyboard(),
            )
            return
        except Exception as e:
            logger.error(f"Failed to send period cover photo: {e}")

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
    """Оплата Telegram Stars — отправляем invoice."""
    await callback.answer()

    data = await state.get_data()
    plan_info = data.get("selected_plan_info", {})
    period_days = data.get("period_days", 30)
    price = data.get("price", 0)
    invoice_payload = data.get("invoice_payload", f"vpn_sub_{callback.from_user.id}_{period_days}")
    plan_name = plan_info.get("name", "VPN Подписка")

    try:
        prices = [LabeledPrice(label="Подписка VPN", amount=int(float(price) * 100))]
        await callback.bot.send_invoice(
            chat_id=callback.from_user.id,
            title=plan_name,
            description=f"Подписка на {period_days} дней",
            payload=invoice_payload,
            provider_token="",  # Telegram Stars — пустой токен
            currency="XTR",
            prices=prices,
            start_parameter="vpn_subscription",
        )
        try:
            await callback.message.edit_text(
                "⭐ Счёт для оплаты отправлен. Нажмите кнопку <b>Оплатить</b> в сообщении выше.",
                parse_mode="HTML",
                reply_markup=get_main_menu(),
            )
        except Exception:
            await callback.message.answer(
                "⭐ Счёт для оплаты отправлен. Нажмите кнопку <b>Оплатить</b> в сообщении выше.",
                parse_mode="HTML",
                reply_markup=get_main_menu(),
            )
    except Exception as e:
        logger.error(f"Error sending Stars invoice: {e}", exc_info=True)
        try:
            await callback.message.edit_text(
                "❌ Ошибка при отправке счёта. Попробуйте позже.",
                reply_markup=get_main_menu(),
            )
        except Exception:
            await callback.message.answer(
                "❌ Ошибка при отправке счёта. Попробуйте позже.",
                reply_markup=get_main_menu(),
            )


@router.callback_query(F.data == "pay_yookassa", PaymentStates.waiting_payment_method)
async def pay_with_yookassa(callback: CallbackQuery, state: FSMContext) -> None:
    """Оплата YooKassa — показываем ссылку."""
    await callback.answer()

    data = await state.get_data()
    yookassa_link = data.get("yookassa_link", "")

    if not yookassa_link:
        try:
            await callback.message.edit_text(
                "❌ Ссылка на оплату недоступна. Попробуйте позже.",
                reply_markup=get_main_menu(),
            )
        except Exception:
            await callback.message.answer(
                "❌ Ссылка на оплату недоступна. Попробуйте позже.",
                reply_markup=get_main_menu(),
            )
        return

    text = (
        "💳 <b>Перейдите по ссылке для оплаты через YooKassa</b>\n\n"
        "Доступные способы оплаты:\n"
        "• Карта Visa/Mastercard/Мир\n"
        "• СБП (переводы по номеру телефона)\n"
        "• Яндекс.Касса\n"
        "• Apple Pay, Google Pay\n\n"
        "После успешной оплаты вам будет отправлена ссылка для подключения."
    )
    try:
        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=get_subscription_link_keyboard(yookassa_link)
        )
    except Exception:
        await callback.message.answer(
            text, parse_mode="HTML", reply_markup=get_subscription_link_keyboard(yookassa_link)
        )


# ─────────────────────────────────────────────────────────────────────────────
# Навигация назад
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "back_to_plans")
async def back_to_plans(callback: CallbackQuery, state: FSMContext) -> None:
    """Вернуться к выбору тарифного плана."""
    await callback.answer()

    data = await state.get_data()
    grouped = data.get("grouped_plans", {})

    if not grouped:
        async with APIClient(config.API_BASE_URL) as api:
            plans = await _fetch_plans(api)
        grouped = _group_plans_by_name(plans)
        await state.update_data(grouped_plans=grouped)

    await state.set_state(PaymentStates.waiting_plan_selection)

    plan_text = (
        "⚡️ <b>Выберите тариф из предложенных</b>\n\n"
        "Каждый тариф позволяет подключить определённое количество устройств к VPN.\n\n"
        "В любой момент вы сможете улучшить свой тариф на большее количество устройств!"
    )

    try:
        await callback.message.edit_text(
            plan_text, parse_mode="HTML", reply_markup=_build_plan_keyboard(grouped)
        )
    except Exception:
        await callback.message.answer(
            plan_text, parse_mode="HTML", reply_markup=_build_plan_keyboard(grouped)
        )


@router.callback_query(F.data == "back_to_payment")
async def back_to_payment(callback: CallbackQuery, state: FSMContext) -> None:
    """Вернуться к выбору периода."""
    await callback.answer()

    data = await state.get_data()
    plan_key = data.get("selected_plan_key", "solo")
    plan_info = data.get("selected_plan_info", {})

    await state.set_state(PaymentStates.waiting_period_selection)

    period_text = (
        f"📅 <b>Выберите период подписки</b>\n\n"
        f"Тариф: <b>{plan_info.get('name', 'VPN')}</b>\n"
        f"Устройств: <b>{plan_info.get('devices', 1)}</b>\n\n"
        "Учтите! Чем больше период, тем ниже цена 💵"
    )

    try:
        await callback.message.edit_text(
            period_text,
            parse_mode="HTML",
            reply_markup=_build_period_keyboard(plan_key, plan_info.get("periods", {})),
        )
    except Exception:
        await callback.message.answer(
            period_text,
            parse_mode="HTML",
            reply_markup=_build_period_keyboard(plan_key, plan_info.get("periods", {})),
        )


@router.callback_query(F.data == "back_to_periods")
async def back_to_periods(callback: CallbackQuery, state: FSMContext) -> None:
    """Алиас back_to_payment — возврат к периодам."""
    await back_to_payment(callback, state)


@router.callback_query(F.data == "confirm_payment", PaymentStates.waiting_period_selection)
async def confirm_payment_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение оплаты — переходим к выбору метода оплаты."""
    await callback.answer()

    data = await state.get_data()
    plan_info = data.get("selected_plan_info", {})
    period_days = data.get("period_days", 0)
    price = data.get("price", 0)

    confirmation_text = format_payment_confirmation(
        plan_name=plan_info.get("name", "VPN"),
        period_days=period_days,
        price=price,
        currency="RUB",
    )

    # Показываем картинку тарифа если есть
    image_url = plan_info.get("image_url", "")
    cover = resolve_media(image_url) if image_url else None

    if cover:
        try:
            await callback.message.delete()
        except Exception:
            pass
        try:
            await callback.bot.send_photo(
                chat_id=callback.from_user.id,
                photo=cover,
                caption=confirmation_text,
                parse_mode="HTML",
                reply_markup=get_payment_method_keyboard(),
            )
            await state.set_state(PaymentStates.waiting_payment_method)
            return
        except Exception as e:
            logger.error(f"Failed to send plan cover photo: {e}")

    try:
        await callback.message.edit_text(
            confirmation_text,
            parse_mode="HTML",
            reply_markup=get_payment_method_keyboard(),
        )
    except Exception:
        await callback.message.answer(
            confirmation_text,
            parse_mode="HTML",
            reply_markup=get_payment_method_keyboard(),
        )

    await state.set_state(PaymentStates.waiting_payment_method)
