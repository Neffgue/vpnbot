"""Admin panel handler"""

import logging
import os
import uuid
import aiofiles
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from bot.config import config
from bot.keyboards.main_menu import get_main_menu_with_admin
from bot.keyboards.admin_kb import get_admin_menu, get_admin_confirm_keyboard, get_admin_back_keyboard
from bot.states.admin_states import AdminStates
from bot.utils.api_client import APIClient

UPLOAD_DIR = "/home/neffgue313/vpnbot/static/uploads"

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


# ═══════════════════════════════════════════════════════════════
# ТАРИФЫ И ЦЕНЫ
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin_prices")
async def admin_prices_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать список тарифов с ценами."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()

    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            plans = await client.get_subscription_plans()
    except Exception as e:
        plans = []
        logger.error(f"Error fetching plans: {e}")

    if not plans:
        text = "❌ Тарифы не найдены или ошибка получения данных."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu")]
        ])
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except Exception:
            await callback.message.answer(text, reply_markup=kb)
        return

    lines = ["💲 <b>Тарифы и цены</b>\n"]
    btns = []
    for plan in plans:
        pid = plan.get("id", "?")
        name = plan.get("name", "—")
        price = plan.get("price", "—")
        duration = plan.get("duration_days", "?")
        lines.append(f"<b>{name}</b> — {price} ₽ / {duration} дн. [ID: {pid}]")
        btns.append([InlineKeyboardButton(
            text=f"✏️ {name} ({price} ₽)",
            callback_data=f"admin_price_edit_{pid}"
        )])
    btns.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu")])

    text = "\n".join(lines) + "\n\nНажмите на тариф чтобы изменить цену:"
    kb = InlineKeyboardMarkup(inline_keyboard=btns)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("admin_price_edit_"))
async def admin_price_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбрать тариф для изменения цены."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()

    plan_id = callback.data.replace("admin_price_edit_", "")
    await state.update_data(price_plan_id=plan_id)
    await state.set_state(AdminStates.waiting_price_amount)

    try:
        await callback.message.edit_text(
            f"✏️ <b>Изменение цены тарифа ID: {plan_id}</b>\n\n"
            "Введите новую цену в рублях (только число, например: 299):"
        )
    except Exception:
        await callback.message.answer(
            f"✏️ <b>Изменение цены тарифа ID: {plan_id}</b>\n\n"
            "Введите новую цену в рублях (только число, например: 299):"
        )


@router.message(AdminStates.waiting_price_amount)
async def admin_price_set(message: Message, state: FSMContext) -> None:
    """Сохранить новую цену тарифа."""
    try:
        new_price = float(message.text.strip().replace(",", "."))
    except ValueError:
        await message.reply("❌ Введите корректную цену (например: 299 или 299.99)")
        return

    data = await state.get_data()
    plan_id = data.get("price_plan_id")
    await state.clear()

    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            result = await client.update_subscription_plan(plan_id, {"price": new_price})
        await message.answer(
            f"✅ Цена тарифа ID {plan_id} обновлена: <b>{new_price} ₽</b>",
            parse_mode="HTML",
            reply_markup=get_admin_menu()
        )
    except Exception as e:
        logger.error(f"Error updating plan price: {e}")
        await message.answer(
            f"❌ Ошибка обновления цены: {e}",
            reply_markup=get_admin_menu()
        )


# ═══════════════════════════════════════════════════════════════
# КНОПКИ МЕНЮ — ЗАГРУЗКА ИЗОБРАЖЕНИЙ
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin_btn_images")
async def admin_btn_images_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать список кнопок для загрузки изображений."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()

    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            buttons = await client.get_bot_buttons()
    except Exception as e:
        buttons = []
        logger.error(f"Error fetching buttons: {e}")

    if not buttons:
        text = "❌ Кнопки не найдены. Добавьте кнопки через веб-админку."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu")]
        ])
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except Exception:
            await callback.message.answer(text, reply_markup=kb)
        return

    lines = ["🖼 <b>Загрузка изображений для кнопок меню</b>\n"]
    btns = []
    for btn in buttons:
        btn_id = btn.get("id", "?")
        btn_text = btn.get("text", "—")
        has_img = "✅" if btn.get("image_url") else "❌"
        lines.append(f"{has_img} {btn_text} [ID: {btn_id}]")
        btns.append([InlineKeyboardButton(
            text=f"🖼 {btn_text}",
            callback_data=f"admin_btn_img_{btn_id}"
        )])
    btns.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu")])

    text = "\n".join(lines) + "\n\n✅ — есть изображение, ❌ — нет\nНажмите кнопку чтобы загрузить фото:"
    kb = InlineKeyboardMarkup(inline_keyboard=btns)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("admin_btn_img_"))
async def admin_btn_img_select(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбрать кнопку для загрузки изображения."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()

    btn_id = callback.data.replace("admin_btn_img_", "")
    await state.update_data(btn_image_id=btn_id)
    await state.set_state(AdminStates.waiting_btn_image_photo)

    try:
        await callback.message.edit_text(
            f"🖼 <b>Загрузка изображения для кнопки ID: {btn_id}</b>\n\n"
            "Отправьте фотографию (как фото, не как файл):",
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            f"🖼 <b>Загрузка изображения для кнопки ID: {btn_id}</b>\n\n"
            "Отправьте фотографию (как фото, не как файл):",
            parse_mode="HTML"
        )


@router.message(AdminStates.waiting_btn_image_photo, F.photo)
async def admin_btn_img_upload(message: Message, state: FSMContext) -> None:
    """Принять фото и загрузить как изображение кнопки."""
    data = await state.get_data()
    btn_id = data.get("btn_image_id")
    await state.clear()

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    ext = "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    await message.bot.download_file(file.file_path, destination=filepath)
    image_url = f"/static/uploads/{filename}"

    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            await client.update_bot_button(btn_id, {"image_url": image_url})
        await message.answer(
            f"✅ Изображение для кнопки ID {btn_id} сохранено!",
            reply_markup=get_admin_menu()
        )
    except Exception as e:
        logger.error(f"Error saving button image: {e}")
        await message.answer(
            f"❌ Ошибка сохранения: {e}",
            reply_markup=get_admin_menu()
        )


@router.message(AdminStates.waiting_btn_image_photo)
async def admin_btn_img_wrong(message: Message, state: FSMContext) -> None:
    """Если прислали не фото."""
    await message.reply("❌ Пожалуйста, отправьте фотографию (не файл).")


# ═══════════════════════════════════════════════════════════════
# ИНСТРУКЦИИ — ЗАГРУЗКА ИЗОБРАЖЕНИЙ К ШАГАМ
# ═══════════════════════════════════════════════════════════════

INSTRUCTION_DEVICES = {
    "windows": "Windows",
    "macos": "macOS",
    "android": "Android",
    "ios": "iOS",
}


@router.callback_query(F.data == "admin_instr_images")
async def admin_instr_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор устройства для управления шагами инструкции."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()

    btns = []
    for dev_key, dev_name in INSTRUCTION_DEVICES.items():
        btns.append([InlineKeyboardButton(
            text=f"📱 {dev_name}",
            callback_data=f"admin_instr_dev_{dev_key}"
        )])
    btns.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu")])

    try:
        await callback.message.edit_text(
            "📖 <b>Инструкции — загрузка изображений</b>\n\nВыберите устройство:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
        )
    except Exception:
        await callback.message.answer(
            "📖 <b>Инструкции — загрузка изображений</b>\n\nВыберите устройство:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
        )


@router.callback_query(F.data.startswith("admin_instr_dev_"))
async def admin_instr_device(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор шага инструкции для устройства."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()

    device = callback.data.replace("admin_instr_dev_", "")
    dev_name = INSTRUCTION_DEVICES.get(device, device)
    await state.update_data(instr_device=device)

    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            steps = await client.get_instruction_steps(device)
    except Exception as e:
        steps = []
        logger.error(f"Error fetching instruction steps: {e}")

    if not steps:
        text = f"❌ Шаги инструкции для {dev_name} не найдены."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_instr_images")]
        ])
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except Exception:
            await callback.message.answer(text, reply_markup=kb)
        return

    btns = []
    for step in steps:
        step_num = step.get("step_number", "?")
        caption = step.get("caption", "")[:30]
        has_img = "✅" if step.get("image_url") else "❌"
        btns.append([InlineKeyboardButton(
            text=f"{has_img} Шаг {step_num}: {caption}",
            callback_data=f"admin_instr_step_{device}_{step_num}"
        )])
    btns.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_instr_images")])

    text = f"📖 <b>Инструкция {dev_name}</b>\n\nВыберите шаг для загрузки изображения:\n✅ — есть фото, ❌ — нет"
    try:
        await callback.message.edit_text(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
        )
    except Exception:
        await callback.message.answer(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
        )


@router.callback_query(F.data.startswith("admin_instr_step_"))
async def admin_instr_step_select(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор шага инструкции для загрузки фото."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()

    parts = callback.data.replace("admin_instr_step_", "").split("_", 1)
    device = parts[0]
    step_num = parts[1] if len(parts) > 1 else "1"
    dev_name = INSTRUCTION_DEVICES.get(device, device)

    await state.update_data(instr_device=device, instr_step_num=step_num)
    await state.set_state(AdminStates.waiting_instr_step_photo)

    try:
        await callback.message.edit_text(
            f"📖 <b>{dev_name} — Шаг {step_num}</b>\n\n"
            "Отправьте фотографию для этого шага (как фото, не как файл):",
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            f"📖 <b>{dev_name} — Шаг {step_num}</b>\n\n"
            "Отправьте фотографию для этого шага (как фото, не как файл):",
            parse_mode="HTML"
        )


@router.message(AdminStates.waiting_instr_step_photo, F.photo)
async def admin_instr_step_upload(message: Message, state: FSMContext) -> None:
    """Принять фото и сохранить как изображение шага инструкции."""
    data = await state.get_data()
    device = data.get("instr_device")
    step_num = data.get("instr_step_num")
    await state.clear()

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(UPLOAD_DIR, filename)

    await message.bot.download_file(file.file_path, destination=filepath)
    image_url = f"/static/uploads/{filename}"

    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            await client.update_instruction_step(device, int(step_num), {"image_url": image_url})
        await message.answer(
            f"✅ Изображение для {INSTRUCTION_DEVICES.get(device, device)} шаг {step_num} сохранено!",
            reply_markup=get_admin_menu()
        )
    except Exception as e:
        logger.error(f"Error saving instruction image: {e}")
        await message.answer(
            f"❌ Ошибка сохранения: {e}",
            reply_markup=get_admin_menu()
        )


@router.message(AdminStates.waiting_instr_step_photo)
async def admin_instr_step_wrong(message: Message, state: FSMContext) -> None:
    """Если прислали не фото."""
    await message.reply("❌ Пожалуйста, отправьте фотографию (не файл).")
