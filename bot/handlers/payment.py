"""Payment flow handler вЂ” С‚Р°СЂРёС„С‹ Рё С†РµРЅС‹ Р·Р°РіСЂСѓР¶Р°СЋС‚СЃСЏ РёР· Р‘Р” С‡РµСЂРµР· API (Single Source of Truth)."""

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

# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
# Р’СЃРїРѕРјРѕРіР°С‚РµР»СЊРЅС‹Рµ С„СѓРЅРєС†РёРё РґР»СЏ СЂР°Р±РѕС‚С‹ СЃ С‚Р°СЂРёС„Р°РјРё РёР· API
# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

PERIOD_LABELS = {
    7: "7 РґРЅРµР№",
    14: "14 РґРЅРµР№",
    30: "1 РјРµСЃСЏС†",
    60: "2 РјРµСЃСЏС†Р°",
    90: "3 РјРµСЃСЏС†Р°",
    180: "6 РјРµСЃСЏС†РµРІ",
    365: "12 РјРµСЃСЏС†РµРІ",
}

FALLBACK_PLANS = [
    {
        "id": "solo",
        "plan_name": "solo",
        "name": "рџ‘¤ РЎРѕР»Рѕ (1 СѓСЃС‚СЂРѕР№СЃС‚РІРѕ)",
        "devices": 1,
        "period_days": 30,
        "price": 150,
        "is_active": True,
    },
    {
        "id": "family",
        "plan_name": "family",
        "name": "рџ‘ЁвЂЌрџ‘©вЂЌрџ‘§вЂЌрџ‘¦ РЎРµРјРµР№РЅС‹Р№ (5 СѓСЃС‚СЂРѕР№СЃС‚РІ)",
        "devices": 5,
        "period_days": 30,
        "price": 250,
        "is_active": True,
    },
]


async def _fetch_plans(api: APIClient) -> list:
    """Р—Р°РіСЂСѓР·РёС‚СЊ С‚Р°СЂРёС„С‹ РёР· API. РџСЂРё РѕС€РёР±РєРµ вЂ” РІРµСЂРЅСѓС‚СЊ fallback-Р·РЅР°С‡РµРЅРёСЏ."""
    try:
        plans = await api.get_subscription_plans()
        if plans:
            return [p for p in plans if p.get("is_active", True)]
    except Exception as e:
        logger.warning(f"Failed to fetch plans from API, using fallback: {e}")
    return FALLBACK_PLANS


def _group_plans_by_name(plans: list) -> dict:
    """РЎРіСЂСѓРїРїРёСЂРѕРІР°С‚СЊ С‚Р°СЂРёС„С‹ РїРѕ plan_name в†’ СЃРїРёСЃРѕРє РїРµСЂРёРѕРґРѕРІ.

    РџРѕРґРґРµСЂР¶РёРІР°РµС‚ РѕР±Р° РІР°СЂРёР°РЅС‚Р° РёРјРµРЅРё РїРѕР»СЏ С†РµРЅС‹:
    - price_rub (СЃС…РµРјР° Р‘Р” PlanPrice)
    - price (РѕР±С‰РёР№ РІР°СЂРёР°РЅС‚)
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
        # РџРѕРґРґРµСЂР¶РєР° РѕР±РѕРёС… РїРѕР»РµР№: price_rub (РёР· Р‘Р”) Рё price (РѕР±С‰РёР№)
        price = float(
            plan.get("price_rub")
            or plan.get("price")
            or 0
        )
        grouped[key]["periods"][days] = price
    return grouped


def _build_plan_keyboard(grouped: dict) -> InlineKeyboardMarkup:
    """РљР»Р°РІРёР°С‚СѓСЂР° РІС‹Р±РѕСЂР° С‚Р°СЂРёС„РЅРѕРіРѕ РїР»Р°РЅР° (СЃС‚СЂРѕРєРё = РѕС‚РґРµР»СЊРЅС‹Рµ РїР»Р°РЅС‹)."""
    rows = []
    for key, info in grouped.items():
        label = f"{info['name']} вЂ” {info['devices']} СѓСЃС‚."
        rows.append([InlineKeyboardButton(text=label, callback_data=f"plan_{key}")])
    rows.append([InlineKeyboardButton(text="в—ЂпёЏ РќР°Р·Р°Рґ", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_period_keyboard(plan_key: str, periods: dict) -> InlineKeyboardMarkup:
    """РљР»Р°РІРёР°С‚СѓСЂР° РІС‹Р±РѕСЂР° РїРµСЂРёРѕРґР° РїРѕРґРїРёСЃРєРё СЃ С†РµРЅР°РјРё РёР· Р‘Р”."""
    rows = []
    for days in sorted(periods.keys()):
        price = periods[days]
        label_day = PERIOD_LABELS.get(int(days), f"{days} РґРЅРµР№")
        label = f"{label_day} вЂ” {int(price)} в‚Ѕ"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"period_{days}")])
    rows.append([InlineKeyboardButton(text="в—ЂпёЏ РќР°Р·Р°Рґ", callback_data="back_to_plans")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
# Handlers
# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

@router.callback_query(F.data == "buy_subscription")
async def buy_subscription_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """РџРѕРєР°Р·Р°С‚СЊ СЃРїРёСЃРѕРє С‚Р°СЂРёС„РЅС‹С… РїР»Р°РЅРѕРІ, Р·Р°РіСЂСѓР¶РµРЅРЅС‹С… РёР· Р‘Р”."""
    await callback.answer()

    async with APIClient(config.api.base_url, config.api.api_key) as api:
        plans = await _fetch_plans(api)

    grouped = _group_plans_by_name(plans)

    # РЎРѕС…СЂР°РЅСЏРµРј СЃРіСЂСѓРїРїРёСЂРѕРІР°РЅРЅС‹Рµ РїР»Р°РЅС‹ РІ state РґР»СЏ РїРѕСЃР»РµРґСѓСЋС‰РёС… С€Р°РіРѕРІ
    await state.update_data(grouped_plans=grouped)
    await state.set_state(PaymentStates.waiting_plan_selection)

    plan_text = (
        "вљЎпёЏ <b>Р’С‹Р±РµСЂРёС‚Рµ С‚Р°СЂРёС„ РёР· РїСЂРµРґР»РѕР¶РµРЅРЅС‹С…</b>\n\n"
        "РљР°Р¶РґС‹Р№ С‚Р°СЂРёС„ РїРѕР·РІРѕР»СЏРµС‚ РїРѕРґРєР»СЋС‡РёС‚СЊ РѕРїСЂРµРґРµР»С‘РЅРЅРѕРµ РєРѕР»РёС‡РµСЃС‚РІРѕ СѓСЃС‚СЂРѕР№СЃС‚РІ Рє VPN.\n\n"
        "Р’ Р»СЋР±РѕР№ РјРѕРјРµРЅС‚ РІС‹ СЃРјРѕР¶РµС‚Рµ СѓР»СѓС‡С€РёС‚СЊ СЃРІРѕР№ С‚Р°СЂРёС„ РЅР° Р±РѕР»СЊС€РµРµ РєРѕР»РёС‡РµСЃС‚РІРѕ СѓСЃС‚СЂРѕР№СЃС‚РІ!"
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
    """Р’С‹Р±РѕСЂ С‚Р°СЂРёС„РЅРѕРіРѕ РїР»Р°РЅР° вЂ” РїРѕРєР°Р·С‹РІР°РµРј РїРµСЂРёРѕРґС‹ СЃ С†РµРЅР°РјРё РёР· Р‘Р”."""
    await callback.answer()

    plan_key = callback.data.replace("plan_", "")
    data = await state.get_data()
    grouped = data.get("grouped_plans", {})

    if not grouped:
        # РџРµСЂРµР·Р°РіСЂСѓР¶Р°РµРј РµСЃР»Рё state РїСѓСЃС‚РѕР№
        async with APIClient(config.api.base_url, config.api.api_key) as api:
            plans = await _fetch_plans(api)
        grouped = _group_plans_by_name(plans)
        await state.update_data(grouped_plans=grouped)

    plan_info = grouped.get(plan_key)
    if not plan_info:
        await callback.answer("РўР°СЂРёС„ РЅРµ РЅР°Р№РґРµРЅ. РџРѕРїСЂРѕР±СѓР№С‚Рµ РµС‰С‘ СЂР°Р·.", show_alert=True)
        return

    await state.update_data(selected_plan_key=plan_key, selected_plan_info=plan_info)
    await state.set_state(PaymentStates.waiting_period_selection)

    period_text = (
        f"рџ“… <b>Р’С‹Р±РµСЂРёС‚Рµ РїРµСЂРёРѕРґ РїРѕРґРїРёСЃРєРё</b>\n\n"
        f"РўР°СЂРёС„: <b>{plan_info['name']}</b>\n"
        f"РЈСЃС‚СЂРѕР№СЃС‚РІ: <b>{plan_info['devices']}</b>\n\n"
        "РЈС‡С‚РёС‚Рµ! Р§РµРј Р±РѕР»СЊС€Рµ РїРµСЂРёРѕРґ, С‚РµРј РЅРёР¶Рµ С†РµРЅР° рџ’µ"
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
    """Р’С‹Р±РѕСЂ РїРµСЂРёРѕРґР° вЂ” РїРѕРєР°Р·С‹РІР°РµРј РїРѕРґС‚РІРµСЂР¶РґРµРЅРёРµ СЃ С†РµРЅРѕР№ РёР· Р‘Р”."""
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

    # РџРѕРєР°Р·С‹РІР°РµРј РєР°СЂС‚РёРЅРєСѓ С‚Р°СЂРёС„Р° РµСЃР»Рё РµСЃС‚СЊ
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
    """РћРїР»Р°С‚Р° Telegram Stars вЂ” РѕС‚РїСЂР°РІР»СЏРµРј invoice."""
    await callback.answer()

    data = await state.get_data()
    plan_info = data.get("selected_plan_info", {})
    period_days = data.get("period_days", 30)
    price = data.get("price", 0)
    invoice_payload = data.get("invoice_payload", f"vpn_sub_{callback.from_user.id}_{period_days}")
    plan_name = plan_info.get("name", "VPN РџРѕРґРїРёСЃРєР°")

    try:
        prices = [LabeledPrice(label="РџРѕРґРїРёСЃРєР° VPN", amount=int(float(price) * 100))]
        await callback.bot.send_invoice(
            chat_id=callback.from_user.id,
            title=plan_name,
            description=f"РџРѕРґРїРёСЃРєР° РЅР° {period_days} РґРЅРµР№",
            payload=invoice_payload,
            provider_token="",  # Telegram Stars вЂ” РїСѓСЃС‚РѕР№ С‚РѕРєРµРЅ
            currency="XTR",
            prices=prices,
            start_parameter="vpn_subscription",
        )
        try:
            await callback.message.edit_text(
                "в­ђ РЎС‡С‘С‚ РґР»СЏ РѕРїР»Р°С‚С‹ РѕС‚РїСЂР°РІР»РµРЅ. РќР°Р¶РјРёС‚Рµ РєРЅРѕРїРєСѓ <b>РћРїР»Р°С‚РёС‚СЊ</b> РІ СЃРѕРѕР±С‰РµРЅРёРё РІС‹С€Рµ.",
                parse_mode="HTML",
                reply_markup=get_main_menu(),
            )
        except Exception:
            await callback.message.answer(
                "в­ђ РЎС‡С‘С‚ РґР»СЏ РѕРїР»Р°С‚С‹ РѕС‚РїСЂР°РІР»РµРЅ. РќР°Р¶РјРёС‚Рµ РєРЅРѕРїРєСѓ <b>РћРїР»Р°С‚РёС‚СЊ</b> РІ СЃРѕРѕР±С‰РµРЅРёРё РІС‹С€Рµ.",
                parse_mode="HTML",
                reply_markup=get_main_menu(),
            )
    except Exception as e:
        logger.error(f"Error sending Stars invoice: {e}", exc_info=True)
        try:
            await callback.message.edit_text(
                "вќЊ РћС€РёР±РєР° РїСЂРё РѕС‚РїСЂР°РІРєРµ СЃС‡С‘С‚Р°. РџРѕРїСЂРѕР±СѓР№С‚Рµ РїРѕР·Р¶Рµ.",
                reply_markup=get_main_menu(),
            )
        except Exception:
            await callback.message.answer(
                "вќЊ РћС€РёР±РєР° РїСЂРё РѕС‚РїСЂР°РІРєРµ СЃС‡С‘С‚Р°. РџРѕРїСЂРѕР±СѓР№С‚Рµ РїРѕР·Р¶Рµ.",
                reply_markup=get_main_menu(),
            )


@router.callback_query(F.data == "pay_yookassa", PaymentStates.waiting_payment_method)
async def pay_with_yookassa(callback: CallbackQuery, state: FSMContext) -> None:
    """РћРїР»Р°С‚Р° YooKassa вЂ” РїРѕРєР°Р·С‹РІР°РµРј СЃСЃС‹Р»РєСѓ."""
    await callback.answer()

    data = await state.get_data()
    yookassa_link = data.get("yookassa_link", "")

    if not yookassa_link:
        try:
            await callback.message.edit_text(
                "вќЊ РЎСЃС‹Р»РєР° РЅР° РѕРїР»Р°С‚Сѓ РЅРµРґРѕСЃС‚СѓРїРЅР°. РџРѕРїСЂРѕР±СѓР№С‚Рµ РїРѕР·Р¶Рµ.",
                reply_markup=get_main_menu(),
            )
        except Exception:
            await callback.message.answer(
                "вќЊ РЎСЃС‹Р»РєР° РЅР° РѕРїР»Р°С‚Сѓ РЅРµРґРѕСЃС‚СѓРїРЅР°. РџРѕРїСЂРѕР±СѓР№С‚Рµ РїРѕР·Р¶Рµ.",
                reply_markup=get_main_menu(),
            )
        return

    text = (
        "рџ’і <b>РџРµСЂРµР№РґРёС‚Рµ РїРѕ СЃСЃС‹Р»РєРµ РґР»СЏ РѕРїР»Р°С‚С‹ С‡РµСЂРµР· YooKassa</b>\n\n"
        "Р”РѕСЃС‚СѓРїРЅС‹Рµ СЃРїРѕСЃРѕР±С‹ РѕРїР»Р°С‚С‹:\n"
        "вЂў РљР°СЂС‚Р° Visa/Mastercard/РњРёСЂ\n"
        "вЂў РЎР‘Рџ (РїРµСЂРµРІРѕРґС‹ РїРѕ РЅРѕРјРµСЂСѓ С‚РµР»РµС„РѕРЅР°)\n"
        "вЂў РЇРЅРґРµРєСЃ.РљР°СЃСЃР°\n"
        "вЂў Apple Pay, Google Pay\n\n"
        "РџРѕСЃР»Рµ СѓСЃРїРµС€РЅРѕР№ РѕРїР»Р°С‚С‹ РІР°Рј Р±СѓРґРµС‚ РѕС‚РїСЂР°РІР»РµРЅР° СЃСЃС‹Р»РєР° РґР»СЏ РїРѕРґРєР»СЋС‡РµРЅРёСЏ."
    )
    try:
        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=get_subscription_link_keyboard(yookassa_link)
        )
    except Exception:
        await callback.message.answer(
            text, parse_mode="HTML", reply_markup=get_subscription_link_keyboard(yookassa_link)
        )


# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
# РќР°РІРёРіР°С†РёСЏ РЅР°Р·Р°Рґ
# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

@router.callback_query(F.data == "back_to_plans")
async def back_to_plans(callback: CallbackQuery, state: FSMContext) -> None:
    """Р’РµСЂРЅСѓС‚СЊСЃСЏ Рє РІС‹Р±РѕСЂСѓ С‚Р°СЂРёС„РЅРѕРіРѕ РїР»Р°РЅР°."""
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
        "вљЎпёЏ <b>Р’С‹Р±РµСЂРёС‚Рµ С‚Р°СЂРёС„ РёР· РїСЂРµРґР»РѕР¶РµРЅРЅС‹С…</b>\n\n"
        "РљР°Р¶РґС‹Р№ С‚Р°СЂРёС„ РїРѕР·РІРѕР»СЏРµС‚ РїРѕРґРєР»СЋС‡РёС‚СЊ РѕРїСЂРµРґРµР»С‘РЅРЅРѕРµ РєРѕР»РёС‡РµСЃС‚РІРѕ СѓСЃС‚СЂРѕР№СЃС‚РІ Рє VPN.\n\n"
        "Р’ Р»СЋР±РѕР№ РјРѕРјРµРЅС‚ РІС‹ СЃРјРѕР¶РµС‚Рµ СѓР»СѓС‡С€РёС‚СЊ СЃРІРѕР№ С‚Р°СЂРёС„ РЅР° Р±РѕР»СЊС€РµРµ РєРѕР»РёС‡РµСЃС‚РІРѕ СѓСЃС‚СЂРѕР№СЃС‚РІ!"
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
    """Р’РµСЂРЅСѓС‚СЊСЃСЏ Рє РІС‹Р±РѕСЂСѓ РїРµСЂРёРѕРґР°."""
    await callback.answer()

    data = await state.get_data()
    plan_key = data.get("selected_plan_key", "solo")
    plan_info = data.get("selected_plan_info", {})

    await state.set_state(PaymentStates.waiting_period_selection)

    period_text = (
        f"рџ“… <b>Р’С‹Р±РµСЂРёС‚Рµ РїРµСЂРёРѕРґ РїРѕРґРїРёСЃРєРё</b>\n\n"
        f"РўР°СЂРёС„: <b>{plan_info.get('name', 'VPN')}</b>\n"
        f"РЈСЃС‚СЂРѕР№СЃС‚РІ: <b>{plan_info.get('devices', 1)}</b>\n\n"
        "РЈС‡С‚РёС‚Рµ! Р§РµРј Р±РѕР»СЊС€Рµ РїРµСЂРёРѕРґ, С‚РµРј РЅРёР¶Рµ С†РµРЅР° рџ’µ"
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
    """РђР»РёР°СЃ back_to_payment вЂ” РІРѕР·РІСЂР°С‚ Рє РїРµСЂРёРѕРґР°Рј."""
    await back_to_payment(callback, state)


@router.callback_query(F.data == "confirm_payment", PaymentStates.waiting_period_selection)
async def confirm_payment_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """РџРѕРґС‚РІРµСЂР¶РґРµРЅРёРµ РѕРїР»Р°С‚С‹ вЂ” РїРµСЂРµС…РѕРґРёРј Рє РІС‹Р±РѕСЂСѓ РјРµС‚РѕРґР° РѕРїР»Р°С‚С‹."""
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

    # РџРѕРєР°Р·С‹РІР°РµРј РєР°СЂС‚РёРЅРєСѓ С‚Р°СЂРёС„Р° РµСЃР»Рё РµСЃС‚СЊ
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
