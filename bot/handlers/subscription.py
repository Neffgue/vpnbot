"""Subscription and renewal handler"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.config import config
from bot.keyboards.main_menu import get_main_menu
from bot.keyboards.subscription_kb import get_subscription_keyboard
from bot.utils.api_client import APIClient
from bot.utils.formatters import format_subscription_info, get_fallback_texts

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data == "renew_subscription")
async def renew_subscription(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handle subscription renewal
    Redirect to payment flow
    """
    await callback.answer()
    
    try:
        try:
            await callback.message.edit_text(
                "♻️ <b>Продление подписки</b>\n\n"
                "Вы будете перенаправлены к выбору тарифа и периода.",
                reply_markup=get_main_menu()
            )
        except Exception:
            await callback.message.answer(
                "♻️ <b>Продление подписки</b>\n\n"
                "Вы будете перенаправлены к выбору тарифа и периода.",
                reply_markup=get_main_menu()
            )
    except Exception as e:
        logger.error(f"Failed to edit message in renew_subscription: {e}")
        await callback.answer("❌ Не удалось загрузить страницу продления подписки.")
        return
    
    # The user can then select "Оплатить тариф" from main menu
    # Or we can directly redirect to plan selection


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handle cancel action - clear state and return to menu
    """
    await callback.answer()
    
    await state.clear()
    
    user_id = callback.from_user.id
    from bot.keyboards.main_menu import get_main_menu_with_admin
    
    keyboard = (
        get_main_menu_with_admin() if user_id in config.telegram.admin_ids else get_main_menu()
    )
    
    try:
        try:
            await callback.message.edit_text(
                "Действие отменено. Вы в главном меню.",
                reply_markup=keyboard
            )
        except Exception:
            await callback.message.answer(
                "Действие отменено. Вы в главном меню.",
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"Failed to edit message in cancel_action: {e}")
        await callback.answer("❌ Не удалось отправить сообщение.")
        return
