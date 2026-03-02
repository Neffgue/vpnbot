"""Admin panel handler"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from bot.config import config
from bot.keyboards.main_menu import get_main_menu_with_admin
from bot.keyboards.admin_kb import get_admin_menu, get_admin_confirm_keyboard, get_admin_back_keyboard
from bot.states.admin_states import AdminStates
from bot.utils.api_client import APIClient

logger = logging.getLogger(__name__)

router = Router()


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in config.telegram.admin_ids


@router.message(Command("admin"))
async def admin_command(message: Message, state: FSMContext) -> None:
    """Handle /admin command (admin only)"""
    
    if not is_admin(message.from_user.id):
        await message.reply("❌ У вас нет доступа к этой команде.")
        return
    
    await state.clear()
    
    await message.answer(
        "⚙️ <b>Админ панель</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_menu()
    )


@router.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат в главное меню из админки"""
    await callback.answer()
    from bot.keyboards.main_menu import get_main_menu
    await state.clear()
    try:
        await callback.message.edit_text(
            "👋 <b>Главное меню</b>\n\nВыберите действие:",
            reply_markup=get_main_menu()
        )
    except Exception:
        await callback.message.answer(
            "👋 <b>Главное меню</b>\n\nВыберите действие:",
            reply_markup=get_main_menu()
        )


@router.callback_query(F.data == "admin_menu")
async def admin_menu_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат в меню админа (из статистики и т.д.)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    await callback.answer()
    await state.clear()
    try:
        await callback.message.edit_text(
            "⚙️ <b>Админ панель</b>\n\nВыберите действие:",
            reply_markup=get_admin_menu()
        )
    except Exception:
        await callback.message.answer(
            "⚙️ <b>Админ панель</b>\n\nВыберите действие:",
            reply_markup=get_admin_menu()
        )


@router.callback_query(F.data == "admin_users")
async def admin_users_list(callback: CallbackQuery, state: FSMContext) -> None:
    """Список последних пользователей."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    await callback.answer()
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            data = await client.get("/admin/users?limit=10")
            users = data if isinstance(data, list) else data.get("users", [])

        lines = ["👥 <b>Последние пользователи:</b>\n"]
        for u in users[:10]:
            tg = u.get("telegram_id", "?")
            name = u.get("first_name", "") or u.get("username", "—")
            banned = " 🚫" if u.get("is_banned") else ""
            sub = " ✅" if u.get("has_active_subscription") else ""
            lines.append(f"• <code>{tg}</code> {name}{banned}{sub}")

        try:
            await callback.message.edit_text(
                "\n".join(lines) or "Пользователей нет.",
                reply_markup=get_admin_back_keyboard()
            )
        except Exception:
            await callback.message.answer(
                "\n".join(lines) or "Пользователей нет.",
                reply_markup=get_admin_back_keyboard()
            )
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        try:
            await callback.message.edit_text("❌ Ошибка загрузки пользователей.", reply_markup=get_admin_back_keyboard())
        except Exception:
            await callback.message.answer("❌ Ошибка загрузки пользователей.", reply_markup=get_admin_back_keyboard())


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, state: FSMContext) -> None:
    """Show bot statistics"""
    
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    await callback.answer()
    
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            stats = await client.get_stats()
            
            stats_text = (
                f"📊 <b>Статистика бота</b>\n\n"
                f"👥 Всего пользователей: {stats.get('total_users', 0)}\n"
                f"✅ Активных подписок: {stats.get('active_subscriptions', 0)}\n"
                f"💰 Всего доход: {stats.get('total_revenue', 0)} ₽\n"
                f"📈 Доход за месяц: {stats.get('monthly_revenue', 0)} ₽\n"
                f"🚫 Заблокировано пользователей: {stats.get('banned_users', 0)}\n"
                f"🎁 Использованы пробные периоды: {stats.get('free_trials_used', 0)}\n"
                f"👥 Активные рефералы: {stats.get('active_referrals', 0)}"
            )
            
            try:
                await callback.message.edit_text(
                    stats_text,
                    reply_markup=get_admin_back_keyboard()
                )
            except Exception:
                await callback.message.answer(
                    stats_text,
                    reply_markup=get_admin_back_keyboard()
                )
    
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        
        try:
            await callback.message.edit_text(
                "❌ Ошибка при загрузке статистики",
                reply_markup=get_admin_back_keyboard()
            )
        except Exception:
            await callback.message.answer(
                "❌ Ошибка при загрузке статистики",
                reply_markup=get_admin_back_keyboard()
            )


@router.callback_query(F.data == "admin_ban_user")
async def admin_ban_user(callback: CallbackQuery, state: FSMContext) -> None:
    """Start ban user flow"""
    
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    await callback.answer()
    
    try:
        await callback.message.edit_text(
            "🚫 <b>Заблокировать пользователя</b>\n\n"
            "Введите ID пользователя для блокировки:"
        )
    except Exception:
        await callback.message.answer(
            "🚫 <b>Заблокировать пользователя</b>\n\n"
            "Введите ID пользователя для блокировки:"
        )
    
    await state.set_state(AdminStates.waiting_ban_user_id)


@router.message(AdminStates.waiting_ban_user_id)
async def get_ban_user_id(message: Message, state: FSMContext) -> None:
    """Get user ID to ban"""
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.reply("❌ Пожалуйста, введите корректный ID")
        return
    
    await message.reply("Введите причину блокировки:")
    await state.update_data(ban_user_id=user_id)
    await state.set_state(AdminStates.waiting_ban_reason)


@router.message(AdminStates.waiting_ban_reason)
async def get_ban_reason(message: Message, state: FSMContext) -> None:
    """Get ban reason and execute ban"""
    
    data = await state.get_data()
    user_id = data.get("ban_user_id")
    reason = message.text.strip()
    
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            result = await client.ban_user(user_id, reason)
            
            if result.get("success", False):
                await message.answer(f"✅ Пользователь {user_id} заблокирован\nПричина: {reason}")
            else:
                error = result.get("error", "Неизвестная ошибка")
                await message.answer(f"❌ Ошибка: {error}")
            
            await message.answer(
                "⚙️ <b>Админ панель</b>",
                reply_markup=get_admin_menu()
            )
            
            await state.clear()
    
    except Exception as e:
        logger.error(f"Error banning user: {e}")
        await message.answer(f"❌ Ошибка при блокировке: {e}")
        await state.clear()


@router.callback_query(F.data == "admin_add_balance")
async def admin_add_balance(callback: CallbackQuery, state: FSMContext) -> None:
    """Start add balance flow"""
    
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    await callback.answer()
    
    try:
        await callback.message.edit_text(
            "💰 <b>Добавить баланс</b>\n\n"
            "Введите ID пользователя:"
        )
    except Exception:
        await callback.message.answer(
            "💰 <b>Добавить баланс</b>\n\n"
            "Введите ID пользователя:"
        )
    
    await state.set_state(AdminStates.waiting_add_balance_user_id)


@router.message(AdminStates.waiting_add_balance_user_id)
async def get_balance_user_id(message: Message, state: FSMContext) -> None:
    """Get user ID for balance add"""
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.reply("❌ Пожалуйста, введите корректный ID")
        return
    
    await message.reply("Введите сумму для добавления (в рублях):")
    await state.update_data(balance_user_id=user_id)
    await state.set_state(AdminStates.waiting_add_balance_amount)


@router.message(AdminStates.waiting_add_balance_amount)
async def get_balance_amount(message: Message, state: FSMContext) -> None:
    """Get balance amount"""
    
    try:
        amount = float(message.text.strip())
    except ValueError:
        await message.reply("❌ Пожалуйста, введите корректную сумму")
        return
    
    await message.reply("Введите причину добавления баланса:")
    await state.update_data(balance_amount=amount)
    await state.set_state(AdminStates.waiting_add_balance_reason)


@router.message(AdminStates.waiting_add_balance_reason)
async def get_balance_reason(message: Message, state: FSMContext) -> None:
    """Get balance reason and execute add"""
    
    data = await state.get_data()
    user_id = data.get("balance_user_id")
    amount = data.get("balance_amount")
    reason = message.text.strip()
    
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            result = await client.add_balance(user_id, amount, reason)
            
            # Backend returns updated user object on success
            if result and (result.get("id") or result.get("balance") is not None or result.get("success")):
                new_balance = result.get("balance", "?")
                await message.answer(
                    f"✅ Баланс +{amount}₽ добавлен пользователю {user_id}\n"
                    f"💰 Новый баланс: {new_balance}₽\n"
                    f"📝 Причина: {reason}"
                )
            else:
                error = result.get("error", result.get("detail", "Неизвестная ошибка")) if result else "Нет ответа от сервера"
                await message.answer(f"❌ Ошибка: {error}")
            
            await message.answer(
                "⚙️ <b>Админ панель</b>",
                reply_markup=get_admin_menu()
            )
            
            await state.clear()
    
    except Exception as e:
        logger.error(f"Error adding balance: {e}")
        await message.answer(f"❌ Ошибка при добавлении баланса: {e}")
        await state.clear()


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """Start broadcast flow — поддержка текста, фото, фото+текст"""

    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    await callback.answer()

    try:
        await callback.message.edit_text(
            "📢 <b>Отправить рассылку</b>\n\n"
            "Отправьте:\n"
            "• <b>Текст</b> — для текстовой рассылки\n"
            "• <b>Фото</b> — для рассылки только с изображением\n"
            "• <b>Фото + подпись</b> — для рассылки с фото и текстом",
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            "📢 <b>Отправить рассылку</b>\n\n"
            "Отправьте:\n"
            "• <b>Текст</b> — для текстовой рассылки\n"
            "• <b>Фото</b> — для рассылки только с изображением\n"
            "• <b>Фото + подпись</b> — для рассылки с фото и текстом",
            parse_mode="HTML",
        )

    await state.set_state(AdminStates.waiting_broadcast_message)


@router.message(AdminStates.waiting_broadcast_message)
async def get_broadcast_message(message: Message, state: FSMContext) -> None:
    """Get broadcast message — text only or photo (with optional caption)"""

    # Определяем тип рассылки
    if message.photo:
        # Фото (с подписью или без)
        photo_id = message.photo[-1].file_id
        caption = message.caption or ""
        broadcast_text = caption
        broadcast_photo = photo_id
        preview = f"📷 Фото{f' + текст: {caption[:50]}...' if caption else ' (без текста)'}"
    elif message.text:
        # Только текст
        broadcast_text = message.text
        broadcast_photo = None
        preview = f"📝 Текст: {broadcast_text[:100]}..."
    else:
        await message.reply("❌ Пожалуйста, отправьте текст или фото.")
        return

    await state.update_data(
        broadcast_message=broadcast_text,
        broadcast_photo=broadcast_photo,
    )

    confirm_text = (
        f"📢 <b>Предпросмотр рассылки:</b>\n\n"
        f"{preview}\n\n"
        "Отправить эту рассылку всем незаблокированным пользователям?"
    )

    if broadcast_photo:
        # Показываем превью фото
        await message.reply_photo(
            photo=broadcast_photo,
            caption=confirm_text + f"\n\n{broadcast_text}" if broadcast_text else confirm_text,
            parse_mode="HTML",
            reply_markup=get_admin_confirm_keyboard(),
        )
    else:
        await message.reply(
            confirm_text,
            parse_mode="HTML",
            reply_markup=get_admin_confirm_keyboard(),
        )

    await state.set_state(AdminStates.waiting_broadcast_confirm)


@router.callback_query(F.data == "admin_action_confirm", AdminStates.waiting_broadcast_confirm)
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """Confirm and send broadcast — text / photo / photo+text"""
    await callback.answer()

    data = await state.get_data()
    broadcast_message = data.get("broadcast_message", "")
    broadcast_photo = data.get("broadcast_photo")

    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            # Получаем всех незаблокированных пользователей
            users_data = await client.get("/admin/users?limit=10000")
            users = users_data if isinstance(users_data, list) else users_data.get("users", [])
            user_ids = [
                int(u["telegram_id"])
                for u in users
                if u.get("telegram_id") and not u.get("is_banned")
            ]

        # Отправляем через Telegram Bot API напрямую (по user_id)
        from aiogram import Bot
        from bot.config import config as bot_config
        bot = Bot(token=bot_config.telegram.token)

        sent_count = 0
        failed_count = 0

        for uid in user_ids:
            try:
                if broadcast_photo:
                    await bot.send_photo(
                        chat_id=uid,
                        photo=broadcast_photo,
                        caption=broadcast_message or None,
                        parse_mode="HTML",
                    )
                else:
                    await bot.send_message(
                        chat_id=uid,
                        text=broadcast_message,
                        parse_mode="HTML",
                    )
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send broadcast to {uid}: {e}")
                failed_count += 1

        await bot.session.close()

        result_text = (
            f"✅ Рассылка завершена!\n\n"
            f"📤 Отправлено: {sent_count}\n"
            f"❌ Ошибок: {failed_count}"
        )

        try:
            await callback.message.edit_text(result_text, reply_markup=get_admin_menu())
        except Exception:
            await callback.message.answer(result_text, reply_markup=get_admin_menu())

        await state.clear()

    except Exception as e:
        logger.error(f"Error sending broadcast: {e}")
        try:
            await callback.message.edit_text(
                f"❌ Ошибка при отправке рассылки: {e}",
                reply_markup=get_admin_menu()
            )
        except Exception:
            await callback.message.answer(
                f"❌ Ошибка при отправке рассылки: {e}",
                reply_markup=get_admin_menu()
            )
        await state.clear()


@router.callback_query(F.data == "admin_action_cancel")
async def cancel_admin_action(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel admin action"""
    await callback.answer("Действие отменено")
    
    await state.clear()
    
    try:
        await callback.message.edit_text(
            "⚙️ <b>Админ панель</b>",
            reply_markup=get_admin_menu()
        )
    except Exception:
        await callback.message.answer(
            "⚙️ <b>Админ панель</b>",
            reply_markup=get_admin_menu()
        )


@router.callback_query(F.data == "admin_unban_user")
async def admin_unban_user(callback: CallbackQuery, state: FSMContext) -> None:
    """Unban user"""
    
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    await callback.answer()
    
    try:
        await callback.message.edit_text(
            "✅ <b>Разблокировать пользователя</b>\n\n"
            "Введите ID пользователя для разблокировки:"
        )
    except Exception:
        await callback.message.answer(
            "✅ <b>Разблокировать пользователя</b>\n\n"
            "Введите ID пользователя для разблокировки:"
        )
    
    await state.set_state(AdminStates.waiting_unban_user_id)


@router.message(AdminStates.waiting_unban_user_id)
async def unban_user_handler(message: Message, state: FSMContext) -> None:
    """Unban user handler"""
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.reply("❌ Пожалуйста, введите корректный ID")
        return
    
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            result = await client.unban_user(user_id)
            
            if result.get("success", False):
                await message.answer(f"✅ Пользователь {user_id} разблокирован")
            else:
                error = result.get("error", "Неизвестная ошибка")
                await message.answer(f"❌ Ошибка: {error}")
            
            await message.answer(
                "⚙️ <b>Админ панель</b>",
                reply_markup=get_admin_menu()
            )
            
            await state.clear()
    
    except Exception as e:
        logger.error(f"Error unbanning user: {e}")
        await message.answer(f"❌ Ошибка при разблокировке: {e}")
        await state.clear()
