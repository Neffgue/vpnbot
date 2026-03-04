"""Personal cabinet handler"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

import os

from bot.config import config
from bot.keyboards.main_menu import get_main_menu
from bot.keyboards.subscription_kb import get_cabinet_keyboard, get_device_keyboard, get_add_device_keyboard
from bot.states.payment_states import DeviceStates, EmailStates
from bot.utils.api_client import APIClient
from bot.utils.formatters import format_subscription_info, format_devices_list, get_fallback_texts


logger = logging.getLogger(__name__)


def _resolve_media(path_or_url: str):
    """Читает медиа-файл с диска или возвращает URL как есть."""
    if not path_or_url:
        return None
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    _project_root = "/home/neffgue313/vpnbot"
    candidates = [
        path_or_url,
        os.path.join(_project_root, path_or_url.lstrip("/")),
        os.path.join(_project_root, "static", "uploads", os.path.basename(path_or_url)),
        "/app" + path_or_url,
        os.path.join("/app", path_or_url.lstrip("/")),
    ]
    for candidate in candidates:
        try:
            if os.path.isfile(candidate):
                with open(candidate, "rb") as f:
                    return f.read()
        except Exception:
            continue
    logger.warning(f"Media file not found: {path_or_url}")
    return None

router = Router()


@router.callback_query(F.data == "cabinet")
async def cabinet_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handle personal cabinet request
    Show subscription info and options
    """
    # Отвечаем на callback СРАЗУ — до любых API запросов
    # Иначе Telegram выдаёт "query is too old" если запросы занимают > нескольких секунд
    await callback.answer()

    user_id = callback.from_user.id
    
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            # Get subscription info
            subscription = await client.get_subscription(user_id)
            
            # Get user info (returns {} if user not found)
            user_info = await client.get_user(user_id)
            if not user_info:
                # User not registered yet — register them now
                user_info = await client.register_user(
                    user_id=user_id,
                    username=callback.from_user.username or "",
                    first_name=callback.from_user.first_name or "",
                )
            else:
                # Обновляем имя и username из Telegram при каждом входе в кабинет
                tg_first_name = callback.from_user.first_name or ""
                tg_username = callback.from_user.username or ""
                needs_update = (
                    tg_first_name and user_info.get("first_name") != tg_first_name
                ) or (
                    tg_username and user_info.get("username") != tg_username
                )
                if needs_update:
                    try:
                        await client.update_user(user_id, {
                            "first_name": tg_first_name,
                            "username": tg_username,
                        })
                        user_info["first_name"] = tg_first_name
                        user_info["username"] = tg_username
                    except Exception as upd_err:
                        logger.warning(f"Could not update user profile: {upd_err}")

            # Загружаем текст кабинета из БД (или fallback)
            cabinet_header = None
            cabinet_image = None
            try:
                texts = await client.get_all_bot_texts()
                cabinet_header = texts.get("cabinet_header")
            except Exception:
                pass
            try:
                settings = await client.get_bot_settings()
                raw_img = settings.get("cabinet_image") or settings.get("cabinet_photo") or ""
                # Читаем файл с диска если это локальный путь
                cabinet_image = _resolve_media(raw_img) if raw_img else None
            except Exception:
                pass

            # Формируем текст кабинета по ТЗ
            first_name = user_info.get('first_name') or callback.from_user.first_name or '.'
            balance = user_info.get('balance', 0) or 0

            # Данные подписки
            sub_link = subscription.get('vpn_key') or subscription.get('key') or subscription.get('subscription_link') or ''
            plan_group = subscription.get('plan_name') or subscription.get('group_name') or '—'
            plan_period = subscription.get('plan_period') or subscription.get('period') or '—'
            device_limit = subscription.get('device_limit') or '—'
            device_count = subscription.get('device_count') or subscription.get('connected_devices') or '—'

            # Форматируем дату окончания по МСК
            expire_str = '—'
            expire_raw = subscription.get('expire_date') or subscription.get('expires_at')
            if expire_raw:
                from datetime import timezone, timedelta
                try:
                    if isinstance(expire_raw, str):
                        from datetime import datetime as _dt
                        expire_dt = _dt.fromisoformat(expire_raw.replace('Z', '+00:00'))
                    else:
                        expire_dt = expire_raw
                    if expire_dt.tzinfo is None:
                        expire_dt = expire_dt.replace(tzinfo=timezone.utc)
                    msk = expire_dt.astimezone(timezone(timedelta(hours=3)))
                    month_name = {
                        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
                        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
                        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
                    }[msk.month]
                    expire_str = f"{msk.day} {month_name} {msk.year} года, {msk.hour:02d}:{msk.minute:02d} (МСК)"
                except Exception:
                    expire_str = str(expire_raw)

            cabinet_text = (
                f"<b>👤 Профиль:</b>\n"
                f"<blockquote>"
                f"Имя: {first_name}\n"
                f"ID: {user_id}\n"
                f"💳 Баланс: {balance} ₽"
                f"</blockquote>\n\n"
            )

            if sub_link:
                cabinet_text += f"<b>🔑 Ваша подписка:</b>\n{sub_link}\n\n"

            if subscription:
                cabinet_text += (
                    f"<b>📦 Информация о тарифе:</b>\n"
                    f"<blockquote>"
                    f"📋 Группа: {plan_group}\n"
                    f"💎 Тариф: {plan_period}\n"
                    f"📱 Лимит устройств: {device_limit}\n"
                    f"🔄 Привязанных устройств: {device_count}"
                    f"</blockquote>\n\n"
                    f"📆 Срок действия: {expire_str}"
                )
            else:
                cabinet_text += "❌ Нет активной подписки"
            
            # Показываем с картинкой, если есть
            if cabinet_image:
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                try:
                    await callback.bot.send_photo(
                        chat_id=user_id,
                        photo=cabinet_image,
                        caption=cabinet_text,
                        parse_mode="HTML",
                        reply_markup=get_cabinet_keyboard()
                    )
                    return
                except Exception as e:
                    logger.error(f"Failed to send cabinet photo: {e}")

            # Show cabinet with options (text only)
            try:
                await callback.message.edit_text(
                    cabinet_text,
                    parse_mode="HTML",
                    reply_markup=get_cabinet_keyboard()
                )
            except Exception:
                # edit_text fails if original message is a photo or already deleted
                await callback.message.answer(
                    cabinet_text,
                    parse_mode="HTML",
                    reply_markup=get_cabinet_keyboard()
                )
    
    except Exception as e:
        logger.error(f"Error in cabinet_handler: {e}", exc_info=True)
        
        try:
            await callback.message.edit_text(
                "❌ Произошла ошибка при загрузке личного кабинета.",
                reply_markup=get_main_menu()
            )
        except Exception:
            await callback.message.answer(
                "❌ Произошла ошибка при загрузке личного кабинета.",
                reply_markup=get_main_menu()
            )


@router.callback_query(F.data == "manage_devices")
async def manage_devices(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handle device management request
    Show list of devices — формат по ТЗ
    """
    await callback.answer()
    user_id = callback.from_user.id

    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            devices_data = await client.get_user_devices(user_id)
            devices = devices_data.get("devices", [])

            # Получаем HWID из данных пользователя/подписки если есть
            hwid = devices_data.get("hwid") or devices_data.get("client_id") or ""

            # Формируем текст по ТЗ
            lines = []
            if hwid:
                lines.append("💻 <b>HWID устройства</b>")
                lines.append(f"🔑 <code>{hwid}</code>")
                lines.append("")

            lines.append(f"Привязано: {len(devices)}")

            for idx, device in enumerate(devices, 1):
                model = device.get("model") or device.get("name") or device.get("server") or "—"
                platform = device.get("platform") or device.get("os") or "—"
                user_agent = device.get("user_agent") or device.get("app") or "—"
                created = device.get("created_at") or device.get("added_date") or "—"
                updated = device.get("updated_at") or device.get("last_seen") or "—"

                lines.append(f"{idx}.")
                lines.append(f"└ 📱 Модель: {model}")
                lines.append(f"└ 🤖 Платформа: {platform}")
                lines.append(f"└ 🌐 User-Agent: {user_agent}")
                lines.append(f"└ 🕒 Создано: {created}")
                lines.append(f"└ 🔄 Обновлено: {updated}")

            if not devices:
                lines.append("Нет подключённых устройств")

            message = "\n".join(lines)

            try:
                await callback.message.edit_text(
                    message,
                    parse_mode="HTML",
                    reply_markup=get_device_keyboard(devices)
                )
            except Exception:
                await callback.message.answer(
                    message,
                    parse_mode="HTML",
                    reply_markup=get_device_keyboard(devices)
                )

            await state.update_data(devices=devices)

    except Exception as e:
        logger.error(f"Error in manage_devices: {e}")
        try:
            await callback.message.edit_text(
                "❌ Произошла ошибка при загрузке устройств.",
                reply_markup=get_cabinet_keyboard()
            )
        except Exception:
            await callback.message.answer(
                "❌ Произошла ошибка при загрузке устройств.",
                reply_markup=get_cabinet_keyboard()
            )


@router.callback_query(F.data == "add_device")
async def add_device_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handle add device request
    Show device type selection
    """
    
    await callback.message.edit_text(
        "📱 <b>Добавить устройство</b>\n\n"
        "Выберите тип вашего устройства:\n\n"
        "Это поможет нам подобрать правильные инструкции для подключения.",
        reply_markup=get_add_device_keyboard()
    )
    
    await state.set_state(DeviceStates.waiting_device_type)
    await callback.answer()


@router.callback_query(F.data.startswith("device_"), DeviceStates.waiting_device_type)
async def select_device_type(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handle device type selection
    Add device and get config
    """
    
    device_type = callback.data.replace("device_", "")
    device_names = {
        "ios": "iPhone/iPad",
        "android": "Android",
        "windows": "Windows",
        "macos": "macOS",
        "linux": "Linux",
    }
    device_name = device_names.get(device_type, device_type)
    
    user_id = callback.from_user.id
    
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            # Add new device
            device_result = await client.add_device(user_id, device_name)
            
            if not device_result.get("success", False):
                error_msg = device_result.get("error", "Неизвестная ошибка")
                await callback.message.edit_text(
                    f"❌ Ошибка при добавлении устройства: {error_msg}",
                    reply_markup=get_cabinet_keyboard()
                )
                await callback.answer()
                return
            
            # Get subscription link (config)
            subscription_link = device_result.get("subscription_link", "")
            device_id = device_result.get("device_id", "")
            
            success_message = (
                f"✅ <b>Устройство {device_name} добавлено</b>\n\n"
                f"<b>ID устройства:</b> <code>{device_id}</code>\n\n"
                f"Ниже вы найдёте ссылку для подключения в приложении Happ:"
            )
            
            if subscription_link:
                success_message += f"\n<blockquote>{subscription_link}</blockquote>"
            
            from bot.keyboards.payment_kb import get_subscription_link_keyboard
            
            await callback.message.edit_text(
                success_message,
                parse_mode="HTML",
                reply_markup=get_subscription_link_keyboard(subscription_link) if subscription_link else get_cabinet_keyboard()
            )
            
            await state.clear()
            await callback.answer()
    
    except Exception as e:
        logger.error(f"Error in select_device_type: {e}")
        
        await callback.message.edit_text(
            "❌ Произошла ошибка при добавлении устройства.",
            reply_markup=get_cabinet_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data.startswith("delete_device_"))
async def delete_device(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handle device deletion
    Delete/unlink device from server
    """
    
    device_id = callback.data.replace("delete_device_", "")
    user_id = callback.from_user.id
    
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            # Delete device
            result = await client.delete_device(user_id, device_id)
            
            if result.get("success", False):
                await callback.message.edit_text(
                    f"✅ Устройство удалено успешно.",
                    reply_markup=get_cabinet_keyboard()
                )
            else:
                error_msg = result.get("error", "Неизвестная ошибка")
                await callback.message.edit_text(
                    f"❌ Ошибка при удалении устройства: {error_msg}",
                    reply_markup=get_cabinet_keyboard()
                )
            
            await callback.answer()
    
    except Exception as e:
        logger.error(f"Error in delete_device: {e}")
        
        await callback.message.edit_text(
            "❌ Произошла ошибка при удалении устройства.",
            reply_markup=get_cabinet_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data == "back_to_cabinet")
async def back_to_cabinet(callback: CallbackQuery, state: FSMContext) -> None:
    """Go back to cabinet"""
    await state.clear()
    await cabinet_handler(callback, state)


@router.callback_query(F.data == "back_to_devices")
async def back_to_devices(callback: CallbackQuery, state: FSMContext) -> None:
    """Go back to device list from device type selection"""
    await manage_devices(callback, state)


@router.callback_query(F.data == "back_to_device_types")
async def back_to_device_types(callback: CallbackQuery, state: FSMContext) -> None:
    """Go back to device type selection from device confirmation"""
    
    await callback.message.edit_text(
        "📱 <b>Добавить устройство</b>\n\n"
        "Выберите тип вашего устройства:\n\n"
        "Это поможет нам подобрать правильные инструкции для подключения.",
        reply_markup=get_add_device_keyboard()
    )
    await state.set_state(DeviceStates.waiting_device_type)
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_device_"))
async def confirm_device(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle device type confirmation — add device"""
    
    device_type = callback.data.replace("confirm_device_", "")
    device_names = {
        "ios": "iPhone/iPad",
        "android": "Android",
        "windows": "Windows",
        "macos": "macOS",
        "linux": "Linux",
    }
    device_name = device_names.get(device_type, device_type)
    user_id = callback.from_user.id

    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            device_result = await client.add_device(user_id, device_name)

            if not device_result.get("success", False):
                error_msg = device_result.get("error", "Неизвестная ошибка")
                await callback.message.edit_text(
                    f"❌ Ошибка при добавлении устройства: {error_msg}",
                    reply_markup=get_cabinet_keyboard()
                )
                await callback.answer()
                return

            subscription_link = device_result.get("subscription_link", "")
            device_id = device_result.get("device_id", "")

            success_message = (
                f"✅ <b>Устройство {device_name} добавлено!</b>\n\n"
                f"<b>ID устройства:</b> <code>{device_id}</code>\n\n"
                f"Ниже — ссылка для подключения в приложении <b>Happ</b>:"
            )

            if subscription_link:
                success_message += f"\n\n<code>{subscription_link}</code>"

            from bot.keyboards.payment_kb import get_subscription_link_keyboard
            await callback.message.edit_text(
                success_message,
                reply_markup=get_subscription_link_keyboard(subscription_link) if subscription_link else get_cabinet_keyboard()
            )

            await state.clear()
            await callback.answer()

    except Exception as e:
        logger.error(f"Error in confirm_device: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при добавлении устройства.",
            reply_markup=get_cabinet_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data == "copy_subscription_link")
async def copy_subscription_link(callback: CallbackQuery) -> None:
    """Показывает подсказку по копированию ссылки."""
    await callback.answer(
        "Нажмите на ссылку выше чтобы скопировать её, затем вставьте в Happ → «＋» → «Из буфера».",
        show_alert=True
    )


@router.callback_query(F.data == "reissue_key")
async def reissue_key_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает предупреждение перед перевыпуском ключа."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ Да, перевыпустить ключ", callback_data="reissue_key_confirm")],
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="back_to_cabinet")],
    ])
    await callback.message.edit_text(
        "⚠️ <b>Перевыпуск VPN-ключа</b>\n\n"
        "При перевыпуске ключа:\n"
        "• Все текущие соединения будут разорваны\n"
        "• Старый ключ деактивируется\n"
        "• Новый ключ нужно будет заново вставить в Happ\n\n"
        "Вы уверены, что хотите продолжить?",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "reissue_key_confirm")
async def reissue_key_execute(callback: CallbackQuery, state: FSMContext) -> None:
    """Выполняет перевыпуск VPN-ключа."""
    user_id = callback.from_user.id
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            result = await client.reissue_vpn_key(user_id)

            if result.get("success", False):
                new_link = result.get("subscription_link", "")
                text = (
                    "✅ <b>VPN-ключ успешно перевыпущен!</b>\n\n"
                    "Вставьте новый ключ в приложение <b>Happ</b> "
                    "(кнопка «＋» → «Из буфера»):\n\n"
                )
                if new_link:
                    text += f"<code>{new_link}</code>"

                from bot.keyboards.payment_kb import get_subscription_link_keyboard
                await callback.message.edit_text(
                    text,
                    reply_markup=get_subscription_link_keyboard(new_link) if new_link else get_cabinet_keyboard()
                )
            else:
                error = result.get("error", "Ошибка перевыпуска ключа")
                await callback.message.edit_text(
                    f"❌ {error}",
                    reply_markup=get_cabinet_keyboard()
                )
    except Exception as e:
        logger.error(f"Error in reissue_key_execute: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при перевыпуске ключа.",
            reply_markup=get_cabinet_keyboard()
        )
    await callback.answer()


@router.callback_query(F.data == "my_payments")
async def my_payments(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает историю платежей пользователя."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    user_id = callback.from_user.id
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            payments_data = await client.get_user_payments(user_id)
            payments = payments_data.get("payments", []) if isinstance(payments_data, dict) else []

        if not payments:
            text = (
                "💳 <b>Мои платежи</b>\n\n"
                "Платежей пока нет.\n\n"
                "Оформите подписку, чтобы увидеть историю оплат."
            )
        else:
            from bot.utils.formatters import format_date_short
            from datetime import datetime
            lines = ["💳 <b>История платежей</b>\n"]
            for p in payments[:10]:  # Последние 10
                amount = p.get("amount", 0)
                plan = p.get("plan_name", "—")
                status = "✅" if p.get("status") == "completed" else "⏳"
                date_str = p.get("created_at", "")
                if date_str:
                    try:
                        dt = datetime.fromisoformat(date_str)
                        date_str = format_date_short(dt)
                    except Exception:
                        pass
                lines.append(f"{status} {date_str} | {plan} | {amount:.0f}₽")
            text = "\n".join(lines)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ В личный кабинет", callback_data="back_to_cabinet")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in my_payments: {e}")
        await callback.message.edit_text(
            "❌ Не удалось загрузить историю платежей.",
            reply_markup=get_cabinet_keyboard()
        )
    await callback.answer()


@router.callback_query(F.data == "cabinet_settings")
async def cabinet_settings(callback: CallbackQuery, state: FSMContext) -> None:
    """Настройки личного кабинета (email, перевыпуск ключа)."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Перевыпустить VPN-ключ", callback_data="reissue_key")],
        [InlineKeyboardButton(text="◀️ В личный кабинет", callback_data="back_to_cabinet")],
    ])
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        "Здесь вы можете перевыпустить VPN-ключ.\n\n"
        "⚠️ При перевыпуске ключа все текущие устройства отключатся.",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "add_email")
async def add_email_handler(callback: CallbackQuery, state: FSMContext) -> None:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    await callback.answer()
    await callback.message.edit_text(
        "📧 <b>Добавить email</b>\n\nВведите ваш адрес электронной почты:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_cabinet")]
        ])
    )
    await state.set_state(EmailStates.waiting_email)


@router.message(EmailStates.waiting_email)
async def process_email(message, state: FSMContext) -> None:
    email = message.text.strip()
    import re
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        await message.answer('❌ Неверный формат email. Попробуйте ещё раз:')
        return
    user_id = message.from_user.id
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            await client.update_user(user_id, {'email': email})
        await message.answer('✅ Email сохранён!')
    except Exception:
        await message.answer('❌ Не удалось сохранить email.')
    await state.clear()
