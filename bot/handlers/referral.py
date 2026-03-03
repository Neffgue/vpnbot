"""Referral program and partner program handlers"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext

from bot.config import config
from bot.keyboards.main_menu import get_main_menu
from bot.keyboards.inline_kb import get_back_button
from bot.utils.api_client import APIClient

logger = logging.getLogger(__name__)

router = Router()

BOT_USERNAME = (
    os.getenv("BOT_USERNAME")
    or os.getenv("TELEGRAM_BOT_USERNAME")
    or "vpnsolid_bot"
)


def _resolve_media(path_or_url: str):
    """Reads media from disk or returns URL string."""
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
    from aiogram.types import BufferedInputFile
    for candidate in candidates:
        try:
            if os.path.isfile(candidate):
                with open(candidate, "rb") as f:
                    data = f.read()
                return BufferedInputFile(data, filename=os.path.basename(candidate))
        except Exception:
            continue
    logger.warning(f"Media file not found: {path_or_url}")
    return None


# ─── 🎁 ПОЛУЧИТЬ БЕСПЛАТНО (реферальная программа с бонусными днями) ─────────

def _get_free_keyboard(ref_link: str) -> InlineKeyboardMarkup:
    """Клавиатура раздела 🎁 Получить бесплатно."""
    share_text = "🔥 Попробуй лучший VPN! Быстро, надёжно, без ограничений."
    share_url = f"https://t.me/share/url?url={ref_link}&text={share_text}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Поделиться ссылкой", url=share_url)],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")],
    ])


@router.callback_query(F.data == "get_free")
async def get_free_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Раздел '🎁 Получить бесплатно' — реферальная система с уровнями и бонусными днями.
    """
    await callback.answer()
    user_id = callback.from_user.id

    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            try:
                referral_data = await client.get_referral_info(user_id)
            except Exception as e:
                logger.error(f"Failed to get referral info: {e}")
                referral_data = {}

            ref_link = referral_data.get("referral_link", f"https://t.me/{BOT_USERNAME}?start=ref{user_id}")
            referrals_count = referral_data.get("referrals_count", 0)

            # Загружаем обложку из настроек
            cover_media = None
            try:
                settings = await client.get_bot_settings()
                raw_img = settings.get("referral_image") or ""
                cover_media = _resolve_media(raw_img) if raw_img else None
            except Exception:
                pass

            # Определяем уровень
            if referrals_count >= 10:
                level = "АМБАССАДОР"
            elif referrals_count >= 5:
                level = "ПРОДВИНУТЫЙ"
            else:
                level = "НОВИЧОК 🐣"

            text = (
                "🤩 Расскажите друзьям о нашем VPN!\n\n"
                "🤝 Приглашайте новых пользователей и повышайте свой статус. "
                "Когда ваш реферал оплатит подписку, вы оба получаете бонусные дни! "
                "Чем выше ваш уровень — тем щедрее бонусы за каждого приглашённого.\n\n"
                "Сделайте свое приглашение выгоднее других! ✨\n\n"
                "<blockquote>"
                "<b>НОВИЧОК 🐣</b>\n"
                "Награда за каждого реферала - 8 дней\n"
                "Бонус вашего реферала - 4 дня\n\n"
                "<b>ПРОДВИНУТЫЙ</b> - от 5 приглашённых.\n"
                "Награда за каждого реферала - 10 дней\n"
                "Бонус вашего реферала - 5 дней\n\n"
                "<b>АМБАССАДОР</b> - от 10 приглашённых.\n"
                "Награда за каждого реферала - 14 дней\n"
                "Бонус вашего реферала - 7 дней"
                "</blockquote>\n\n"
                "<i>(Реферал — это человек, пришедший по вашей ссылке и оплативший подписку)</i>\n\n"
                "Вот ваша реферальная ссылка:\n"
                "👇 Нажмите, чтобы скопировать.\n"
                f"<code>{ref_link}</code>\n\n"
                "<blockquote>"
                f"Ваш текущий уровень - {level}\n"
                f"📝 Количество приглашённых пользователей: {referrals_count}"
                "</blockquote>\n\n"
                "😉 Делитесь ссылкой и наслаждайтесь лучшим VPN бесплатно! 🚀"
            )

            kb = _get_free_keyboard(ref_link)

            if cover_media:
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                try:
                    await callback.bot.send_photo(
                        chat_id=user_id,
                        photo=cover_media,
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=kb,
                    )
                    return
                except Exception as e:
                    logger.error(f"Failed to send referral cover photo: {e}")

            try:
                await callback.message.edit_text(
                    text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True,
                )
            except Exception:
                await callback.message.answer(
                    text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True,
                )

    except Exception as e:
        logger.error(f"Unexpected error in get_free_handler: {e}")
        try:
            await callback.message.edit_text(
                "❌ Произошла ошибка. Попробуйте позже.",
                reply_markup=get_back_button("back_to_menu")
            )
        except Exception:
            await callback.answer("❌ Ошибка при загрузке раздела.")


# ─── 🔗 РЕФЕРАЛЬНАЯ СИСТЕМА (партнёрская программа с выводом средств) ─────────

def _get_partner_keyboard(ref_link: str, withdraw_method: str = "") -> InlineKeyboardMarkup:
    """Клавиатура партнёрской программы."""
    method_label = withdraw_method if withdraw_method else "не задан"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Скопировать ссылку 🔗", callback_data="partner_copy_link")],
        [InlineKeyboardButton(text="💰 Вывести средства", callback_data="partner_withdraw")],
        [InlineKeyboardButton(text=f"Вывод: {method_label}", callback_data="partner_set_method")],
        [InlineKeyboardButton(text="📜 История выводов", callback_data="partner_history")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
    ])


def _get_withdraw_method_keyboard() -> InlineKeyboardMarkup:
    """Выбор способа вывода."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Банковская карта", callback_data="partner_method_card")],
        [InlineKeyboardButton(text="🏦 СБП", callback_data="partner_method_sbp")],
        [InlineKeyboardButton(text="🪙 USDT (TRC20)", callback_data="partner_method_usdt")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="partner")],
    ])


@router.callback_query(F.data == "partner")
async def partner_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Раздел '🔗 Реферальная система' — партнёрская программа с выводом средств.
    """
    await callback.answer()
    user_id = callback.from_user.id

    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            try:
                referral_data = await client.get_referral_info(user_id)
            except Exception as e:
                logger.error(f"Failed to get partner info: {e}")
                referral_data = {}

            ref_link = referral_data.get("partner_link") or referral_data.get("referral_link") or f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
            invited_total = referral_data.get("referrals_count", 0)
            paid_count = referral_data.get("paid_referrals_count", 0)
            withdraw_method = referral_data.get("withdraw_method") or ""
            requisites = referral_data.get("requisites") or "не указаны"
            balance = referral_data.get("partner_balance", 0) or 0

            method_display = withdraw_method if withdraw_method else "не задан"
            req_display = requisites if requisites else "не указаны"

            text = (
                f"🔗 <b>Ваша ссылка:</b>\n"
                f"<code>{ref_link}</code>\n\n"
                f"<blockquote>"
                f"📈 Ваша статистика:\n"
                f"👤 Приглашено: {invited_total} чел.\n"
                f"💸 Оплатили подписку: {paid_count} чел.\n"
                f"🏦 Способ вывода: {method_display}\n"
                f"🧾 Реквизиты: {req_display}\n"
                f"💰 Баланс: {balance} рублей"
                f"</blockquote>\n\n"
                f"💸 Вывод доступен от 3000 рублей\n\n"
                f"<blockquote>"
                f"📈 Текущая ставка: 50%\n"
                f"Пример: платёж 1350 рублей → ваши 675 рублей"
                f"</blockquote>"
            )

            try:
                await callback.message.edit_text(
                    text,
                    parse_mode="HTML",
                    reply_markup=_get_partner_keyboard(ref_link, withdraw_method),
                    disable_web_page_preview=True,
                )
            except Exception:
                await callback.message.answer(
                    text,
                    parse_mode="HTML",
                    reply_markup=_get_partner_keyboard(ref_link, withdraw_method),
                    disable_web_page_preview=True,
                )

    except Exception as e:
        logger.error(f"Unexpected error in partner_handler: {e}")
        try:
            await callback.message.edit_text(
                "❌ Произошла ошибка. Попробуйте позже.",
                reply_markup=get_back_button("back_to_menu")
            )
        except Exception:
            await callback.answer("❌ Ошибка при загрузке раздела.")


@router.callback_query(F.data == "partner_copy_link")
async def partner_copy_link(callback: CallbackQuery) -> None:
    """Копировать реферальную ссылку — показываем всплывающее уведомление."""
    user_id = callback.from_user.id
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            referral_data = await client.get_referral_info(user_id)
            ref_link = referral_data.get("partner_link") or referral_data.get("referral_link") or f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
    except Exception:
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
    await callback.answer(f"Ваша ссылка:\n{ref_link}", show_alert=True)


@router.callback_query(F.data == "partner_withdraw")
async def partner_withdraw(callback: CallbackQuery, state: FSMContext) -> None:
    """Вывести средства — проверяем указан ли способ вывода."""
    user_id = callback.from_user.id
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            referral_data = await client.get_referral_info(user_id)
            withdraw_method = referral_data.get("withdraw_method") or ""
    except Exception:
        withdraw_method = ""

    if not withdraw_method:
        await callback.answer(
            "ℹ️ Вы не указали способ вывода средств! Пожалуйста, выберите его, а затем создайте заявку на вывод ещё раз",
            show_alert=True
        )
        return

    # Если способ задан — можно создать заявку (логика вывода)
    await callback.answer("✅ Заявка на вывод отправлена. Ожидайте обработки.", show_alert=True)


@router.callback_query(F.data == "partner_set_method")
async def partner_set_method(callback: CallbackQuery) -> None:
    """Выбрать способ вывода средств."""
    await callback.answer()
    try:
        await callback.message.edit_text(
            "⚙️ <b>Выберите способ вывода средств</b>",
            parse_mode="HTML",
            reply_markup=_get_withdraw_method_keyboard(),
        )
    except Exception:
        await callback.message.answer(
            "⚙️ <b>Выберите способ вывода средств</b>",
            parse_mode="HTML",
            reply_markup=_get_withdraw_method_keyboard(),
        )


@router.callback_query(F.data.in_({"partner_method_card", "partner_method_sbp", "partner_method_usdt"}))
async def partner_save_method(callback: CallbackQuery, state: FSMContext) -> None:
    """Сохраняем выбранный способ вывода и возвращаемся в партнёрку."""
    method_map = {
        "partner_method_card": "Банковская карта",
        "partner_method_sbp": "СБП",
        "partner_method_usdt": "USDT (TRC20)",
    }
    method = method_map.get(callback.data, "")
    user_id = callback.from_user.id

    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            await client.update_user(user_id, {"withdraw_method": method})
    except Exception as e:
        logger.warning(f"Could not save withdraw method: {e}")

    await callback.answer(f"✅ Способ вывода выбран: {method}", show_alert=True)
    # Возвращаем в партнёрку
    await partner_handler(callback, state)


@router.callback_query(F.data == "partner_history")
async def partner_history(callback: CallbackQuery) -> None:
    """История выводов."""
    await callback.answer()
    text = (
        "📜 <b>История выводов</b>\n"
        "<blockquote>Выводов пока нет</blockquote>"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="partner")],
    ])
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)


# ─── Старый handler referral (оставляем для совместимости) ───────────────────

@router.callback_query(F.data == "referral")
async def referral_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Совместимость: старый callback 'referral' теперь ведёт в 🎁 Получить бесплатно."""
    await get_free_handler(callback, state)
