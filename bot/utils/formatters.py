"""Formatting utilities for bot messages — все тексты в правильной UTF-8 кодировке."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List


# ─── Дата и время ────────────────────────────────────────────────────────────

RUSSIAN_MONTHS = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}


def format_date(date_obj: Optional[datetime]) -> str:
    """Форматировать дату в читаемый русский формат."""
    if not date_obj:
        return "—"
    if date_obj.tzinfo is None:
        date_obj = date_obj.replace(tzinfo=timezone.utc)
    msk = timezone(timedelta(hours=3))
    date_obj = date_obj.astimezone(msk)
    month = RUSSIAN_MONTHS.get(date_obj.month, "")
    return f"{date_obj.day} {month} {date_obj.year}, {date_obj.hour:02d}:{date_obj.minute:02d}"


def format_date_short(date_obj: Optional[datetime]) -> str:
    """Форматировать дату в короткий формат ДД.ММ.ГГГГ."""
    if not date_obj:
        return "—"
    return f"{date_obj.day:02d}.{date_obj.month:02d}.{date_obj.year}"


def format_time_remaining(expire_date: Optional[datetime]) -> str:
    """Форматировать оставшееся время до истечения подписки."""
    if not expire_date:
        return "—"
    now = datetime.now(timezone.utc)
    if expire_date.tzinfo is None:
        expire_date = expire_date.replace(tzinfo=timezone.utc)
    if expire_date <= now:
        return "истекла"
    delta = expire_date - now
    days = delta.days
    hours = delta.seconds // 3600
    if days > 0:
        return f"{days} дн. {hours} ч."
    elif hours > 0:
        return f"{hours} ч."
    else:
        minutes = delta.seconds // 60
        return f"{minutes} мин."


# ─── Трафик ──────────────────────────────────────────────────────────────────

def format_traffic(bytes_amount: Optional[int]) -> str:
    """Форматировать байты в человекочитаемый формат."""
    if bytes_amount is None:
        return "Безлимит"
    if bytes_amount == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(bytes_amount)
    unit_index = 0
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.2f} {units[unit_index]}"


# ─── Цены ────────────────────────────────────────────────────────────────────

def format_price(amount: float, currency: str = "RUB") -> str:
    """Форматировать цену с символом валюты."""
    if currency == "RUB":
        return f"{amount:.0f} ₽"
    elif currency == "USD":
        return f"${amount:.2f}"
    elif currency == "XTR":
        return f"{int(amount)} ⭐"
    return f"{amount:.2f} {currency}"


# ─── Подписка ────────────────────────────────────────────────────────────────

PERIOD_LABELS = {
    7: "7 дней",
    14: "14 дней",
    30: "1 месяц",
    60: "2 месяца",
    90: "3 месяца",
    180: "6 месяцев",
    365: "12 месяцев",
}


def format_payment_confirmation(
    plan_name: str,
    period_days: int,
    price: float,
    currency: str = "RUB",
) -> str:
    """Форматировать сообщение подтверждения оплаты."""
    period_text = PERIOD_LABELS.get(int(period_days), f"{period_days} дней")
    return (
        f"<b>Подтверждение оплаты</b>\n\n"
        f"<b>Тариф:</b> {plan_name}\n"
        f"<b>Период:</b> {period_text}\n"
        f"<b>Стоимость:</b> {format_price(price, currency)}\n\n"
        f"Нажмите кнопку <b>Оплатить</b> для перехода к оплате."
    )


def format_subscription_info(subscription: Dict[str, Any]) -> str:
    """Форматировать информацию о подписке пользователя."""
    plan = subscription.get("plan_name", "VPN")
    is_active = subscription.get("is_active", False)
    expires_at_raw = subscription.get("expires_at")
    device_limit = subscription.get("device_limit", 1)

    status = "✅ Активна" if is_active else "❌ Неактивна"

    expires_str = "—"
    if expires_at_raw:
        try:
            if isinstance(expires_at_raw, str):
                expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
            else:
                expires_at = expires_at_raw
            expires_str = format_date(expires_at)
        except Exception:
            expires_str = str(expires_at_raw)

    return (
        f"<b>Ваша подписка:</b>\n\n"
        f"📦 Тариф: <b>{plan}</b>\n"
        f"📊 Статус: {status}\n"
        f"📅 Истекает: <b>{expires_str}</b>\n"
        f"💻 Устройств: <b>{device_limit}</b>"
    )


def format_plan_selection(plans: List[Dict[str, Any]]) -> str:
    """Форматировать список тарифов для выбора."""
    lines = ["<b>Выберите тариф:</b>\n"]
    for plan in plans:
        name = plan.get("name") or plan.get("plan_name", "VPN")
        description = plan.get("description", "")
        devices = int(plan.get("device_limit") or plan.get("devices") or 1)
        price = float(plan.get("price_rub") or plan.get("price") or 0)
        lines.append(f"<b>{name}</b> — {devices} уст. от {price:.0f} ₽")
        if description:
            lines.append(f"  {description}")
        lines.append("")
    return "\n".join(lines)


def format_period_selection(plan_name: str = "VPN", devices: int = 1) -> str:
    """Форматировать текст выбора периода подписки."""
    return (
        f"<b>Выберите период подписки</b>\n\n"
        f"Тариф: <b>{plan_name}</b>\n"
        f"Устройств: <b>{devices}</b>\n\n"
        "Чем дольше период — тем ниже цена! 💵"
    )


def format_referral_info(referral_data: Dict[str, Any]) -> str:
    """Форматировать информацию о реферальной программе."""
    referral_code = referral_data.get("referral_code", "—")
    referral_count = referral_data.get("referral_count", 0)
    bonus_days = referral_data.get("bonus_days", 0)

    return (
        f"🤝 <b>Реферальная программа</b>\n\n"
        f"Ваш код: <code>{referral_code}</code>\n"
        f"Приглашено друзей: <b>{referral_count}</b>\n"
        f"Бонусных дней заработано: <b>{bonus_days}</b>\n\n"
        f"Поделитесь кодом с друзьями и получайте бонусные дни к подписке!"
    )


def format_devices_list(devices: List[Dict[str, Any]]) -> str:
    """Форматировать список устройств пользователя."""
    if not devices:
        return "У вас нет подключённых устройств."
    lines = ["<b>Ваши подключённые устройства:</b>\n"]
    for idx, device in enumerate(devices, 1):
        server = device.get("server", "Unknown")
        added_date = device.get("added_date")
        device_id = device.get("id", "")
        date_str = format_date_short(datetime.fromisoformat(added_date)) if added_date else "—"
        lines.append(f"{idx}. <b>{server}</b> (добавлено: {date_str}) [ID: {device_id}]")
    return "\n".join(lines)


def get_fallback_texts() -> Dict[str, str]:
    """Резервные тексты бота на случай недоступности API."""
    return {
        "welcome": (
            "👋 <b>Добро пожаловать!</b>\n\n"
            "🚀 Быстрый и надёжный VPN на базе <b>Happ</b>\n\n"
            "Что умеет бот:\n"
            "🎁 Бесплатный период на 24 часа (1 устройство)\n"
            "💻 Тарифы: один и несколько устройств\n"
            "🌍 Серверы: Нидерланды, Германия, Финляндия и др.\n"
            "💳 Удобные способы оплаты с быстрой активацией\n"
            "📖 Пошаговые инструкции для любого: iOS, Android\n\n"
            "Выберите действие:"
        ),
        "free_trial_success": (
            "🎉 <b>Бесплатный период активирован!</b>\n\n"
            "Период: <b>24 часа</b> | Устройств: <b>1</b>\n\n"
            "Ссылка для подключения в <b>Happ</b>:\n"
        ),
        "free_trial_used": (
            "⚠️ <b>Бесплатный период уже использован</b>\n\n"
            "Вы можете выбрать платный тариф.\n\n"
            "💻 Оформите подписку для постоянного доступа:"
        ),
        "subscription_required": (
            "⚠️ <b>Требуется активная подписка</b>\n\n"
            "Оформите тариф для доступа к функциям."
        ),
        "referral_header": (
            "🤝 <b>Реферальная программа</b>\n\n"
            "Приглашайте друзей и получайте бонусные дни к подписке!"
        ),
        "cabinet_header": "🗂 <b>Личный кабинет</b>",
        "support_text": "🆘 <b>Поддержка</b>\n\nНажмите кнопку ниже чтобы написать нам:",
        "channel_text": "📢 <b>Наш канал</b>\n\nПодписывайтесь, чтобы не пропустить обновления:",
        "plan_selection": "⚡️ <b>Выберите тариф из предложенных</b>\n\nКаждый тариф позволяет подключить определённое количество устройств к VPN.",
    }
