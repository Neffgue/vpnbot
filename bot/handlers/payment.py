# -*- coding: utf-8 -*-
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
from bot.utils.media import resolve_media, get_section_media

logger = logging.getLogger(__name__)

router = Router()

# ═══════════════════════════════════════════════════════════════════════════════
# Тарифы и цены загружаются из БД через API
# ═══════════════════════════════════════════════════════════════════════════════

PERIOD_LABELS = {
    7: "7 дней",
    14: "14 дней",
    30: "1 месяц",
    60: "2 месяца",
    90: "3 месяца",
    180: "6 месяцев",
    365: "12 месяцев",
}

async def _fetch_plans(api: APIClient) -> list:
    """Загружает тарифы из API. При ошибке возвращает пустой список."""
    try:
        plans = await api.get_subscription_plans()
        if plans:
            active = [p for p in plans if p.get("is_active", True)]
            return active
    except Exception as e:
        logger.warning(f"Failed to fetch plans from API: {e}")
    return []


def _group_plans_by_name(plans: list) -> dict:
    """Группирует тарифы по plan_name для отображения в меню выбора.

    Поддерживает оба формата ответа сервера:
    - price_rub (поле из PlanPrice)
    - price (старый формат)
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
                "image_url": plan.get("image_url", ""),
            }
        days = int(plan.get("period_days", 30))
        # Приоритет цены: сначала price_rub (из БД), затем price (старый)
        price = float(
            plan.get("price_rub")
            or plan.get("price")
            or 0
        )
        grouped[key]["periods"][days] = price
    return grouped


def _build_plan_keyboard(grouped: dict) -> InlineKeyboardMarkup:
    """Формирует клавиатуру выбора тарифа (тариф = отдельная кнопка)."""
    rows = []
    for key, info in grouped.items():
        label = f"{info['name']} — {info['devices']} уст."
        rows.append([InlineKeyboardButton(text=label, callback_data=f"plan_{key}")])
    rows.append([InlineKeyboardButton(text="◀️ В меню", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_period_keyboard(plan_key: str, periods: dict) -> InlineKeyboardMarkup:
    """Формирует клавиатуру выбора периода подписки с ценами из БД."""
    rows = []
    for days in sorted(periods.keys()):
        price = periods[days]
        label_day = PERIOD_LABELS.get(int(days), f"{days} дней")
        label = f"{label_day} — {int(price)} ₽"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"period_{days}")])
    rows.append([InlineKeyboardButton(text="◀️ Назад к тарифам", callback_data="back_to_plans")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ═══════════════════════════════════════════════════════════════════════════════
# Handlers
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "buy_subscription")
async def buy_subscription_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать список тарифных планов для выбора."""
    await callback.answer()

    cover_media = None
    async with APIClient(config.api.base_url, config.api.api_key) as api:
        plans = await _fetch_plans(api)
        cover_media = await get_section_media(api, "subscribe_image", "buy_subscription")

    if not plans:
        no_plans_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ В меню", callback_data="back_to_menu")]
        ])
        try:
            await callback.message.edit_text(
                "⚙️ <b>Тарифы ещё не настроены.</b>\n\n"
                "Пожалуйста, обратитесь к администратору или попробуйте позже.",
                parse_mode="HTML",
                reply_markup=no_plans_kb,
            )
        except Exception:
            await callback.message.answer(
                "⚙️ Тарифы ещё не настроены. Обратитесь к администратору.",
                parse_mode="HTML",
                reply_markup=no_plans_kb,
            )
        return

    grouped = _group_plans_by_name(plans)

    # Сохраняем сгруппированные планы в state для использования в следующих шагах
    await state.update_data(grouped_plans=grouped)
    await state.set_state(PaymentStates.waiting_plan_selection)

    plan_text = (
        "⚡️ <b>Выберите тариф из предложенных:</b>\n\n"
        "Каждый тариф позволяет подключить определённое количество устройств к VPN.\n\n"
        "В каждом тарифе вы сможете выбрать удобный период подписки!"
    )

    kb = _build_plan_keyboard(grouped)
    if cover_media:
        try:
            await callback.message.delete()
        except Exception:
            pass
        try:
            await callback.message.answer_photo(
                photo=cover_media,
                caption=plan_text,
                parse_mode="HTML",
                reply_markup=kb,
            )
        except Exception:
            await callback.message.answer(plan_text, parse_mode="HTML", reply_markup=kb)
    else:
        try:
            await callback.message.edit_text(plan_text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await callback.message.answer(plan_text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("plan_"), PaymentStates.waiting_plan_selection)
async def select_plan(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор конкретного тарифа → предлагает периоды с ценами из БД."""
    await callback.answer()

    plan_key = callback.data.replace("plan_", "")
    data = await state.get_data()
    grouped = data.get("grouped_plans", {})

    if not grouped:
        # Перезагружаем если state протух
        async with APIClient(config.api.base_url, config.api.api_key) as api:
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
        f"💎 <b>Выберите период подписки</b>\n\n"
        f"Тариф: <b>{plan_info['name']}</b>\n"
        f"Устройств: <b>{plan_info['devices']}</b>\n\n"
        "Чем дольше период — тем ниже цена! 💵"
    )

    # Показываем с картинкой тарифа, если есть
    image_url = plan_info.get("image_url", "")
    cover = resolve_media(image_url) if image_url else None

    keyboard = _build_period_keyboard(plan_key, plan_info.get("periods", {}))

    if cover:
        try:
            await callback.message.delete()
        except Exception:
            pass
        try:
            await callback.bot.send_photo(
                chat_id=callback.from_user.id,
                photo=cover,
                caption=period_text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            return
        except Exception as e:
            logger.error(f"Failed to send plan cover: {e}")

    try:
        await callback.message.edit_text(
            period_text, parse_mode="HTML", reply_markup=keyboard
        )
    except Exception:
        await callback.message.answer(
            period_text, parse_mode="HTML", reply_markup=keyboard
        )


@router.callback_query(F.data.startswith("period_"), PaymentStates.waiting_period_selection)
async def select_period(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор периода → запоминает цену и переходит к способу оплаты."""
    await callback.answer()

    period_days = int(callback.data.replace("period_", ""))
    data = await state.get_data()
    plan_info = data.get("selected_plan_info", {})
    periods = plan_info.get("periods", {})
    price = periods.get(period_days, 0)

    await state.update_data(period_days=period_days, price=price)
    await state.set_state(PaymentStates.waiting_payment_method)

    confirmation_text = format_payment_confirmation(
        plan_name=plan_info.get("name", "VPN"),
        period_days=period_days,
        price=price,
        currency="RUB",
    )

    # Показываем картинку тарифа при подтверждении, если есть
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


@router.callback_query(F.data == "pay_stars", PaymentStates.waiting_payment_method)
async def pay_with_stars(callback: CallbackQuery, state: FSMContext) -> None:
    """Оплата через Telegram Stars."""
    await callback.answer()

    data = await state.get_data()
    plan_info = data.get("selected_plan_info", {})
    period_days = data.get("period_days", 30)
    price_rub = float(data.get("price", 0))

    # Конвертируем рубли в звёзды (примерно 1 звезда = 1.5 руб)
    stars = max(1, int(price_rub / 1.5))

    plan_name = plan_info.get("name", "VPN")
    period_label = PERIOD_LABELS.get(int(period_days), f"{period_days} дней")
    title = f"VPN: {plan_name}"
    description = f"Подписка на {period_label}"

    try:
        await callback.bot.send_invoice(
            chat_id=callback.from_user.id,
            title=title,
            description=description,
            payload=f"vpn_{plan_info.get('key', 'solo')}_{period_days}",
            provider_token="",  # Пустой для Stars
            currency="XTR",
            prices=[LabeledPrice(label=title, amount=stars)],
        )
    except Exception as e:
        logger.error(f"Failed to send invoice: {e}")
        await callback.message.answer(
            "❌ Ошибка при создании счёта. Попробуйте позже или обратитесь в поддержку."
        )


@router.callback_query(F.data == "back_to_plans")
async def back_to_plans(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат к выбору тарифа."""
    await callback.answer()

    data = await state.get_data()
    grouped = data.get("grouped_plans", {})

    if not grouped:
        async with APIClient(config.api.base_url, config.api.api_key) as api:
            plans = await _fetch_plans(api)
        grouped = _group_plans_by_name(plans)
        await state.update_data(grouped_plans=grouped)

    await state.set_state(PaymentStates.waiting_plan_selection)

    plan_text = (
        "⚡️ <b>Выберите тариф из предложенных:</b>\n\n"
        "Каждый тариф позволяет подключить определённое количество устройств к VPN.\n\n"
        "В каждом тарифе вы сможете выбрать удобный период подписки!"
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
    """Возврат к выбору периода."""
    await callback.answer()

    data = await state.get_data()
    plan_key = data.get("selected_plan_key", "solo")
    plan_info = data.get("selected_plan_info", {})

    await state.set_state(PaymentStates.waiting_period_selection)

    period_text = (
        f"💎 <b>Выберите период подписки</b>\n\n"
        f"Тариф: <b>{plan_info.get('name', 'VPN')}</b>\n"
        f"Устройств: <b>{plan_info.get('devices', 1)}</b>\n\n"
        "Чем дольше период — тем ниже цена! 💵"
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
    """Псевдоним back_to_payment для возврата к периодам."""
    await back_to_payment(callback, state)


@router.callback_query(F.data == "confirm_payment", PaymentStates.waiting_period_selection)
async def confirm_payment_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Переходит к выбору способа оплаты после выбора тарифа."""
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
