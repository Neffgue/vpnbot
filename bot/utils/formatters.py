"""Formatting utilities for bot messages"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import locale

try:
    locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, "ru_RU")
    except locale.Error:
        pass


# Russian month names for fallback
RUSSIAN_MONTHS = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

RUSSIAN_WEEKDAYS = {
    0: "пн", 1: "вт", 2: "ср", 3: "чт", 4: "пт", 5: "сб", 6: "вс"
}


def format_date(date_obj: Optional[datetime]) -> str:
    """Format datetime to Russian readable format"""
    if not date_obj:
        return "—"
    
    try:
        # Try using locale
        return date_obj.strftime("%d %B %Y, %H:%M")
    except:
        # Fallback format
        month = RUSSIAN_MONTHS.get(date_obj.month, "")
        return f"{date_obj.day} {month} {date_obj.year}, {date_obj.hour:02d}:{date_obj.minute:02d}"


def format_date_short(date_obj: Optional[datetime]) -> str:
    """Format datetime to short Russian format"""
    if not date_obj:
        return "—"
    
    try:
        return date_obj.strftime("%d.%m.%Y")
    except:
        month = RUSSIAN_MONTHS.get(date_obj.month, "")
        return f"{date_obj.day:02d}.{date_obj.month:02d}.{date_obj.year}"


def format_time_remaining(expire_date: Optional[datetime]) -> str:
    """Format remaining time until expiration"""
    if not expire_date:
        return "—"
    
    now = datetime.now(timezone.utc)
    # make expire_date timezone-aware if it's naive
    if expire_date.tzinfo is None:
        expire_date = expire_date.replace(tzinfo=timezone.utc)
    if expire_date <= now:
        return "Истекла"
    
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


def format_traffic(bytes_amount: Optional[int]) -> str:
    """Format bytes to human readable format"""
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
    else:
        return f"{size:.2f} {units[unit_index]}"


def format_price(price: float, currency: str = "RUB") -> str:
    """Format price"""
    if currency == "RUB":
        return f"{price:.2f}₽"
    elif currency == "USD":
        return f"${price:.2f}"
    else:
        return f"{price:.2f} {currency}"


def format_subscription_info(subscription: Dict[str, Any]) -> str:
    """Format subscription information to readable text"""
    if not subscription:
        return "❌ Нет активной подписки"
    
    lines = [
        "✅ <b>Подписка активна</b>",
    ]
    
    if device_limit := subscription.get('device_limit'):
        lines.append(f"🧑‍💻 Доступ для {device_limit} устройств")
    
    expire_date = subscription.get('expire_date') or subscription.get('expires_at')
    if expire_date:
        expire_dt = datetime.fromisoformat(expire_date.replace('Z', '+00:00')) if isinstance(expire_date, str) else expire_date
        # Format as DD.MM.YYYY HH:MM по МСК
        formatted_date = expire_dt.strftime('%d.%m.%Y %H:%M')
        lines.append(f"Закончится {formatted_date} по МСК")
    
    # email отображается в шапке личного кабинета — здесь не дублируем
    
    if traffic := subscription.get('traffic_remaining'):
        total_traffic = subscription.get('traffic_limit', '∞')
        if isinstance(total_traffic, (int, float)) and total_traffic is not None:
            lines.append(f"🚦 Трафик: {format_traffic(traffic)} / {format_traffic(total_traffic)}")
        else:
            lines.append(f"🚦 Трафик: {format_traffic(traffic)} / ∞")
    else:
        lines.append(f"🚦 Трафик: 0 B / ∞")
    
    if vpn_key := subscription.get('vpn_key') or subscription.get('key'):
        lines.append(f"🔗 Ваш ключ: {vpn_key}")
    
    return "\n".join(lines)


def format_referral_info(referral_data: Dict[str, Any]) -> str:
    """Format referral information"""
    lines = [
        f"👥 <b>Программа партнёрства</b>",
        f"",
        f"<b>Ваша реферальная ссылка:</b>",
        f"<code>{referral_data.get('referral_link', 'Ссылка не доступна')}</code>",
        f"",
        f"<b>Статистика:</b>",
        f"Приглашено пользователей: {referral_data.get('referrals_count', 0)}",
        f"Бонус дней накоплено: {referral_data.get('bonus_days', 0)}",
    ]
    
    return "\n".join(lines)


def format_device_list(devices: list[Dict[str, Any]]) -> str:
    """Format list of connected devices"""
    if not devices:
        return "Нет подключенных устройств"
    
    lines = ["<b>Подключённые устройства:</b>", ""]
    
    for idx, device in enumerate(devices, 1):
        server = device.get('server', 'Unknown')
        added_date = device.get('added_date')
        device_id = device.get('id', '')
        
        date_str = format_date_short(datetime.fromisoformat(added_date)) if added_date else "—"
        lines.append(f"{idx}. <b>{server}</b> (добавлено: {date_str}) [ID: {device_id}]")
    
    return "\n".join(lines)


def format_plan_selection(plans: list[Dict[str, Any]]) -> str:
    """Format subscription plans for selection"""
    lines = ["<b>Доступные тарифы:</b>", ""]
    
    for plan in plans:
        name = plan.get('name', 'Unknown')
        description = plan.get('description', '')
        lines.append(f"<b>{name}</b>")
        if description:
            lines.append(f"{description}")
        lines.append("")
    
    return "\n".join(lines)


def format_period_selection() -> str:
    """Format period selection text"""
    return (
        "<b>Выберите период подписки:</b>\n\n"
        "7 дней — пробный период\n"
        "1 месяц — месячная подписка\n"
        "3 месяца — квартальная подписка (скидка)\n"
        "6 месяцев — полугодовая подписка (скидка)\n"
        "12 месяцев — годовая подписка (максимальная скидка)"
    )


def format_payment_confirmation(
    plan_name: str,
    period_days: int,
    price: float,
    currency: str = "RUB"
) -> str:
    """Format payment confirmation message"""
    period_text = {
        7: "7 дней",
        30: "1 месяц",
        90: "3 месяца",
        180: "6 месяцев",
        365: "12 месяцев",
    }.get(period_days, f"{period_days} дней")
    
    return (
        f"<b>Подтверждение платежа</b>\n\n"
        f"<b>Тариф:</b> {plan_name}\n"
        f"<b>Период:</b> {period_text}\n"
        f"<b>Сумма:</b> {format_price(price, currency)}\n\n"
        f"Нажмите кнопку <b>Оплатить</b> для перехода к оплате."
    )


def get_fallback_texts() -> Dict[str, str]:
    """Возвращает тексты бота на русском языке."""
    return {
        "welcome": (
            "👋 <b>Добро пожаловать!</b>\\n\\n"
            "🔐 Быстрый и надёжный VPN через приложение <b>Happ</b>\\n\\n"
            "Что умеет бот:\\n"
            "🎁 Бесплатный доступ на 24 часа (1 раз)\\n"
            "💸 Тарифы Соло и Семейный\\n"
            "🌍 Серверы: Нидерланды, Германия, Турция и др.\\n"
            "👥 Реферальная программа с бонусными днями\\n"
            "📖 Инструкции по подключению для всех устройств\\n\\n"
            "Выберите действие:"
        ),
        "free_trial_success": (
            "✅ <b>Бесплатный доступ активирован!</b>\\n\\n"
            "Срок: <b>24 часа</b> | Устройств: <b>1</b>\\n\\n"
            "Ваша ссылка для приложения <b>Happ</b>:\\n"
        ),
        "free_trial_used": (
            "❌ <b>Бесплатный доступ уже использован</b>\\n\\n"
            "Каждый аккаунт может получить пробный доступ только один раз.\\n\\n"
            "💸 Оформите подписку для продолжения:"
        ),
        "subscription_required": (
            "❌ <b>Требуется активная подписка</b>\\n\\n"
            "Оформите тариф для доступа к этому разделу."
        ),
        "referral_header": "🤝 Приглашайте новых пользователей и повышайте свой статус. Когда ваш реферал оплатит подписку, вы оба получаете бонусные дни! Чем выше ваш уровень — тем щедрее бонусы за каждого приглашённого.\\n\\nСделайте свое приглашение выгоднее других! ✨\\n\\nНОВИЧОК 🐣\\nНаграда за каждого реферала - 8 дней\\nБонус вашего реферала - 4 дня\\n\\nПРОДВИНУТЫЙ - от 5 приглашённых.\\nНаграда за каждого реферала - 10 дней\\nБонус вашего реферала - 5 дней\\n\\nАМБАССАДОР - от 10 приглашённых.\\nНаграда за каждого реферала - 14 дней\\nБонус вашего реферала - 7 дней\\n(Реферал — это человек, пришедший по вашей ссылке и оплативший подписку)",
        "cabinet_header": "👤 <b>Личный кабинет</b>",
        "support_text": "💬 <b>Поддержка</b>\\n\\nЕсли у вас возникли вопросы — напишите нам:",
        "channel_text": "📢 <b>Наш канал</b>\\n\\nПодпишитесь, чтобы не пропустить обновления:",
        "plan_selection": "⚡️ Выберите тариф из предложенных\\n\\nКаждый тариф позволяет подключить определённое количество устройств к VPN.",
    }
