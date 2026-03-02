"""Free trial activation handler"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.config import config
from bot.keyboards.main_menu import get_main_menu, get_dynamic_main_menu
from bot.keyboards.payment_kb import get_subscription_link_keyboard
from bot.utils.api_client import APIClient
from bot.utils.formatters import get_fallback_texts

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data == "free_trial")
async def free_trial_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handle free trial activation
    Check if user already used trial, activate if not
    """
    await callback.answer()
    
    user_id = callback.from_user.id
    
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            # Check if free trial was already used
            try:
                trial_status = await client.check_free_trial_used(user_id)
            except Exception as e:
                logger.error(f"Failed to check free trial status: {e}")
                try:
                    await callback.message.edit_text(
                        "❌ Не удалось проверить статус бесплатного доступа. Попробуйте позже.",
                        reply_markup=get_main_menu()
                    )
                except Exception:
                    await callback.message.answer(
                        "❌ Не удалось проверить статус бесплатного доступа. Попробуйте позже.",
                        reply_markup=get_main_menu()
                    )
                await callback.answer()
                return
            
            if trial_status.get("already_used", False):
                # Пробный период уже использован — просто показываем меню без кнопки,
                # НЕ отправляем никакого сообщения об этом (по ТЗ)
                menu_kb = get_main_menu(show_free_trial=False)
                try:
                    async with APIClient(config.api.base_url, config.api.api_key) as menu_client:
                        menu_kb = await get_dynamic_main_menu(menu_client, show_free_trial=False)
                except Exception:
                    pass
                try:
                    await callback.message.edit_reply_markup(reply_markup=menu_kb)
                except Exception:
                    pass
                return
            
            # Activate free trial
            try:
                trial_result = await client.activate_free_trial(user_id)
            except Exception as e:
                logger.error(f"Failed to activate free trial: {e}")
                try:
                    try:
                        await callback.message.edit_text(
                            "❌ Не удалось активировать бесплатный доступ. Попробуйте позже.",
                            reply_markup=get_main_menu()
                        )
                    except Exception:
                        await callback.message.answer(
                            "❌ Не удалось активировать бесплатный доступ. Попробуйте позже.",
                            reply_markup=get_main_menu()
                        )
                except Exception as edit_error:
                    logger.error(f"Failed to edit message on error: {edit_error}")
                    await callback.answer("❌ Ошибка при активации бесплатного доступа.")
                return
            
            if trial_result.get("success", False):
                # Пробный период успешно активирован
                subscription_link = trial_result.get("subscription_link", "")

                success_text = (
                    "✅ <b>Бесплатный доступ активирован!</b>\n\n"
                    "<blockquote>🎁 Каждый аккаунт может получить пробный доступ только один раз.\n"
                    "Срок действия: <b>24 часа</b> | Устройств: <b>1</b></blockquote>\n\n"
                    "Скопируйте ссылку ниже и вставьте в приложение <b>Happ</b> "
                    "(кнопка «＋» → «Из буфера»):\n\n"
                )

                try:
                    if subscription_link:
                        success_text += f"<blockquote>{subscription_link}</blockquote>"
                        try:
                            await callback.message.edit_text(
                                success_text,
                                parse_mode="HTML",
                                reply_markup=get_subscription_link_keyboard(subscription_link)
                            )
                        except Exception:
                            await callback.message.answer(
                                success_text,
                                parse_mode="HTML",
                                reply_markup=get_subscription_link_keyboard(subscription_link)
                            )
                    else:
                        try:
                            await callback.message.edit_text(
                                success_text,
                                parse_mode="HTML",
                                reply_markup=get_main_menu()
                            )
                        except Exception:
                            await callback.message.answer(
                                success_text,
                                parse_mode="HTML",
                                reply_markup=get_main_menu()
                            )
                except Exception as e:
                    logger.error(f"Failed to edit message after trial activation: {e}")
                    await callback.answer("❌ Не удалось отправить подтверждение активации.")
                    return

                logger.info(f"Free trial activated for user {user_id}")
            else:
                # Error activating trial
                error_message = trial_result.get("error", "Ошибка активации бесплатного доступа")
                try:
                    try:
                        await callback.message.edit_text(
                            f"❌ {error_message}",
                            reply_markup=get_main_menu()
                        )
                    except Exception:
                        await callback.message.answer(
                            f"❌ {error_message}",
                            reply_markup=get_main_menu()
                        )
                except Exception as e:
                    logger.error(f"Failed to edit message with error: {e}")
                    await callback.answer(f"❌ {error_message}")
                    return
    
    except Exception as e:
        logger.error(f"Unexpected error in free trial handler: {e}")
        
        try:
            try:
                await callback.message.edit_text(
                    "❌ Произошла ошибка при активации бесплатного доступа. Попробуйте позже.",
                    reply_markup=get_main_menu()
                )
            except Exception:
                await callback.message.answer(
                    "❌ Произошла ошибка при активации бесплатного доступа. Попробуйте позже.",
                    reply_markup=get_main_menu()
                )
        except Exception as edit_error:
            logger.error(f"Failed to edit message on unexpected error: {edit_error}")
            await callback.answer("❌ Ошибка системы. Попробуйте позже.")
