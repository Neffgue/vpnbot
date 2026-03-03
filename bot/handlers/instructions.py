"""Обработчик инструкций по подключению — Happ VPN"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.utils.media_group import MediaGroupBuilder

from bot.config import config
from bot.utils.api_client import APIClient

logger = logging.getLogger(__name__)
router = Router()


def _make_download_keyboard(buttons: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру со ссылками для скачивания."""
    rows = [[InlineKeyboardButton(text=text, url=url)] for text, url in buttons]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# Кнопки скачивания для каждой платформы
DOWNLOAD_BUTTONS = {
    "android": [
        ("📥 Скачать из Google Play", "https://play.google.com/store/apps/details?id=com.happproxy"),
        ("📦 Скачать APK", "https://github.com/Happ-proxy/happ-android/releases/latest/download/Happ.apk"),
    ],
    "ios": [
        ("🇷🇺 Happ (Россия — App Store)", "https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973"),
        ("🌍 Happ (Зарубежный — App Store)", "https://apps.apple.com/us/app/happ-proxy-utility/id6504287215"),
    ],
    "windows": [
        ("💻 Скачать Happ для Windows", "https://github.com/Happ-proxy/happ-desktop/releases/download/1.2.4/setup-Happ.x64.exe"),
    ],
    "macos": [
        ("🇷🇺 Happ (Россия — App Store)", "https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973"),
        ("🌍 Happ (Запасная ссылка)", "https://apps.apple.com/us/app/happ-proxy-utility/id6504287215"),
    ],
    "linux": [
        ("🐧 Скачать Happ для Linux", "https://github.com/Happ-proxy/happ-desktop/releases/"),
    ],
    "tv": [
        ("📺 Скачать из Google Play", "https://play.google.com/store/apps/details?id=com.happproxy"),
    ],
}

# Маппинг device key → ключ шагов в БД
DEVICE_STEPS_KEYS = {
    "android": "instructions_android_steps",
    "ios": "instructions_ios_steps",
    "windows": "instructions_windows_steps",
    "macos": "instructions_macos_steps",
    "linux": "instructions_linux_steps",
    "tv": "instructions_android_tv_steps",
    "android_tv": "instructions_android_tv_steps",
}

# Маппинг device key → legacy text key (fallback)
DEVICE_LEGACY_KEYS = {
    "android": "instructions_android",
    "ios": "instructions_ios",
    "windows": "instructions_windows",
    "macos": "instructions_macos",
    "linux": "instructions_linux",
    "tv": "instructions_tv",
    "android_tv": "instructions_tv",
}


def _back_to_instructions() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад к выбору устройства", callback_data="instructions")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")],
    ])


def _device_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🤖 Android", callback_data="instr_android"),
            InlineKeyboardButton(text="🍏 iOS", callback_data="instr_ios"),
        ],
        [
            InlineKeyboardButton(text="🪟 Windows", callback_data="instr_windows"),
            InlineKeyboardButton(text="🍎 MacOS", callback_data="instr_macos"),
        ],
        [
            InlineKeyboardButton(text="🐧 Linux", callback_data="instr_linux"),
            InlineKeyboardButton(text="📺 Android TV", callback_data="instr_tv"),
        ],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")],
    ])


# ── Тексты инструкций ────────────────────────────────────────────────────────

INSTRUCTIONS = {
    "android": (
        "📱 <b>Подключение на Android</b>\n\n"
        "<b>Шаг 1.</b> Скачайте приложение <b>Happ</b> (кнопки ниже 👇)\n\n"
        "<b>Шаг 2.</b> Откройте бота → <b>Личный кабинет</b> → скопируйте VPN-ключ\n\n"
        "<b>Шаг 3.</b> В приложении Happ нажмите <b>«＋»</b> или <b>«Из буфера»</b> и вставьте скопированный ключ\n\n"
        "<b>Шаг 4.</b> Нажмите центральную кнопку в Happ — VPN запустится\n\n"
        "<b>Шаг 5.</b> При появлении запроса на VPN-соединение нажмите <b>«Разрешить»</b>\n\n"
        "✅ Готово! Кнопка загорится — соединение установлено.\n\n"
        "💡 В приложении появится список серверов — выберите нужный и переключайтесь без ввода нового ключа."
    ),
    "ios": (
        "🍏 <b>Подключение на iOS (iPhone / iPad)</b>\n\n"
        "<b>Шаг 1.</b> Скачайте приложение <b>Happ</b> (кнопки ниже 👇)\n\n"
        "<b>Шаг 2.</b> Откройте бота → <b>Личный кабинет</b> → скопируйте VPN-ключ\n\n"
        "<b>Шаг 3.</b> В приложении Happ нажмите <b>«＋»</b> → <b>«Из буфера»</b> и вставьте ключ\n\n"
        "<b>Шаг 4.</b> Нажмите центральную кнопку — VPN запустится\n\n"
        "<b>Шаг 5.</b> Разрешите добавление VPN-конфигурации при запросе iOS\n\n"
        "✅ Готово! Соединение установлено.\n\n"
        "💡 В списке появятся все доступные серверы — переключайтесь между странами в один клик."
    ),
    "windows": (
        "🪟 <b>Подключение на Windows</b>\n\n"
        "<b>Шаг 1.</b> Скачайте приложение <b>Happ</b> для Windows (кнопка ниже 👇)\n\n"
        "<b>Шаг 2.</b> Установите приложение и запустите его\n\n"
        "<b>Шаг 3.</b> Откройте бота → <b>Личный кабинет</b> → скопируйте VPN-ключ\n\n"
        "<b>Шаг 4.</b> В приложении нажмите <b>«＋»</b> или <b>«Импорт из буфера»</b>\n\n"
        "<b>Шаг 5.</b> Нажмите кнопку подключения\n\n"
        "✅ Готово! VPN активен.\n\n"
        "⚠️ <i>Перед оплатой отключайте VPN, чтобы банк не заблокировал платёж.</i>"
    ),
    "macos": (
        "🍎 <b>Подключение на MacOS</b>\n\n"
        "<b>Шаг 1.</b> Скачайте приложение <b>Happ</b> (кнопки ниже 👇)\n\n"
        "<b>Шаг 2.</b> Установите и запустите приложение\n\n"
        "<b>Шаг 3.</b> Откройте бота → <b>Личный кабинет</b> → скопируйте VPN-ключ\n\n"
        "<b>Шаг 4.</b> В Happ нажмите <b>«＋»</b> → вставьте ключ из буфера\n\n"
        "<b>Шаг 5.</b> Нажмите кнопку подключения и разрешите VPN-конфигурацию\n\n"
        "✅ Готово! Все серверы доступны в списке приложения.\n\n"
        "💡 Переключайтесь между серверами прямо в приложении."
    ),
    "linux": (
        "🐧 <b>Подключение на Linux</b>\n\n"
        "<b>Шаг 1.</b> Скачайте клиент Happ для Linux (кнопка ниже 👇)\n\n"
        "<b>Шаг 2.</b> Распакуйте архив и запустите:\n"
        "<code>chmod +x happ\n./happ</code>\n\n"
        "<b>Шаг 3.</b> Откройте бота → <b>Личный кабинет</b> → скопируйте VPN-ключ\n\n"
        "<b>Шаг 4.</b> В интерфейсе Happ нажмите <b>«＋»</b> и вставьте ключ\n\n"
        "<b>Шаг 5.</b> Нажмите «Подключить»\n\n"
        "✅ Готово! VPN активен.\n\n"
        "🔧 <i>Поддерживаются Ubuntu 20.04+, Debian 11+, Fedora 36+</i>"
    ),
    "tv": (
        "📺 <b>Подключение на Android TV</b>\n\n"
        "<b>Шаг 1.</b> Откройте Google Play на вашем Android TV и установите <b>Happ</b> (кнопка ниже 👇)\n\n"
        "<b>Шаг 2.</b> На телефоне откройте бота → <b>Личный кабинет</b> → скопируйте VPN-ключ\n\n"
        "<b>Шаг 3.</b> Перенесите ключ на TV через:\n"
        "   • QR-код (если поддерживается)\n"
        "   • Общий буфер обмена (Google аккаунт)\n"
        "   • Ввод вручную через пульт\n\n"
        "<b>Шаг 4.</b> В приложении Happ вставьте ключ и нажмите «Подключить»\n\n"
        "✅ Готово! Теперь весь трафик TV идёт через VPN.\n\n"
        "💡 <i>Для удобства используйте Bluetooth-клавиатуру для ввода ключа.</i>"
    ),
}


def _is_valid_url(url: str) -> bool:
    """Проверить что URL валидный для Telegram кнопки."""
    if not url:
        return False
    return url.startswith("http://") or url.startswith("https://") or url.startswith("tg://")


def _step_keyboard(
    device: str,
    step_idx: int,
    total_steps: int,
    include_downloads: bool = False,
    extra_buttons: list[dict] | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура навигации по шагам инструкции.
    Если include_downloads=True — добавляет кнопки скачивания для данного устройства.
    extra_buttons — список кнопок-ссылок [{"text": "...", "url": "..."}]."""
    buttons = []

    # Кнопки скачивания (для первого шага или если указано явно)
    if include_downloads and device in DOWNLOAD_BUTTONS:
        for text, url in DOWNLOAD_BUTTONS[device]:
            if _is_valid_url(url):
                buttons.append([InlineKeyboardButton(text=text, url=url)])

    # Кнопки-ссылки для шага — строго валидируем URL
    if extra_buttons:
        for btn in extra_buttons:
            text = (btn or {}).get("text", "").strip()
            url = (btn or {}).get("url", "").strip()
            if text and _is_valid_url(url):
                buttons.append([InlineKeyboardButton(text=text, url=url)])

    # Навигация назад/вперёд
    nav_row = []
    if step_idx > 0:
        nav_row.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"instr_step_{device}_{step_idx - 1}"
        ))
    if step_idx < total_steps - 1:
        nav_row.append(InlineKeyboardButton(
            text="Далее ▶️",
            callback_data=f"instr_step_{device}_{step_idx + 1}"
        ))
    if nav_row:
        buttons.append(nav_row)

    if step_idx == total_steps - 1:
        buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_menu")])
    else:
        buttons.append([InlineKeyboardButton(text="◀️ К выбору устройства", callback_data="instructions")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def _load_steps(device_key: str) -> list:
    """Загрузить шаги инструкции из БД или вернуть текст из INSTRUCTIONS."""
    import json
    steps = []
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            texts = await client.get_all_bot_texts()
            steps_key = DEVICE_STEPS_KEYS.get(device_key)
            if steps_key and texts.get(steps_key):
                raw = texts[steps_key]
                try:
                    steps = json.loads(raw)
                except Exception:
                    pass
            # Fallback: legacy single text
            if not steps:
                legacy_key = DEVICE_LEGACY_KEYS.get(device_key)
                if legacy_key and texts.get(legacy_key):
                    steps = [{"step": 1, "text": texts[legacy_key], "image_url": ""}]
    except Exception:
        pass

    # Финальный fallback: хардкод
    if not steps:
        fallback_text = INSTRUCTIONS.get(device_key, "Инструкция недоступна.")
        steps = [{"step": 1, "text": fallback_text, "image_url": ""}]

    return steps


async def _send_step(callback: CallbackQuery, device: str, step_idx: int) -> None:
    """Отправить/показать один шаг инструкции."""
    steps = await _load_steps(device)
    if not steps:
        await callback.answer("❌ Инструкция недоступна.")
        return

    step_idx = max(0, min(step_idx, len(steps) - 1))
    step = steps[step_idx]
    total = len(steps)

    text = step.get("text", "")
    image_url = step.get("image_url", "")
    step_num = step.get("step", step_idx + 1)

    header = f"📖 <b>Шаг {step_num} из {total}</b>\n\n"
    full_text = header + text

    # Показываем кнопки скачивания на первом шаге (или если в тексте есть упоминание «кнопки ниже»)
    include_downloads = step_idx == 0 and device in DOWNLOAD_BUTTONS
    keyboard = _step_keyboard(
        device,
        step_idx,
        total,
        include_downloads=include_downloads,
        extra_buttons=step.get("buttons") or [],
    )

    # Если есть картинка — отправляем с фото
    if image_url:
        # Формируем полный URL если путь относительный
        if image_url.startswith("/"):
            base = config.api.base_url.replace("/api/v1", "")
            image_url = base + image_url
        try:
            await callback.message.delete()
        except Exception:
            pass
        try:
            await callback.bot.send_photo(
                chat_id=callback.from_user.id,
                photo=image_url,
                caption=full_text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            return
        except Exception as e:
            logger.warning(f"Failed to send photo for step, falling back to text: {e}")

    # Текстовый режим
    try:
        await callback.message.edit_text(
            full_text,
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )
    except Exception:
        try:
            await callback.message.answer(
                full_text,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.error(f"Failed to send instruction step: {e}")


@router.callback_query(F.data == "instructions")
async def instructions_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает меню выбора устройства."""
    await callback.answer()
    try:
        try:
            await callback.message.edit_text(
                "📖 <b>Инструкция по подключению</b>\n\n"
                "Выберите устройство, на котором хотите подключить VPN",
                parse_mode="HTML",
                reply_markup=_device_keyboard(),
            )
        except Exception:
            await callback.message.answer(
                "📖 <b>Инструкция по подключению</b>\n\n"
                "Выберите устройство, на котором хотите подключить VPN",
                parse_mode="HTML",
                reply_markup=_device_keyboard(),
            )
    except Exception as e:
        logger.error(f"Failed to edit message in instructions handler: {e}")
        await callback.answer("❌ Не удалось загрузить инструкции.")


@router.callback_query(F.data == "instr_android")
async def instr_android(callback: CallbackQuery) -> None:
    await callback.answer()
    await _send_step(callback, "android", 0)


@router.callback_query(F.data == "instr_ios")
async def instr_ios(callback: CallbackQuery) -> None:
    await callback.answer()
    await _send_step(callback, "ios", 0)


@router.callback_query(F.data == "instr_windows")
async def instr_windows(callback: CallbackQuery) -> None:
    await callback.answer()
    await _send_step(callback, "windows", 0)


@router.callback_query(F.data == "instr_macos")
async def instr_macos(callback: CallbackQuery) -> None:
    await callback.answer()
    await _send_step(callback, "macos", 0)


@router.callback_query(F.data == "instr_linux")
async def instr_linux(callback: CallbackQuery) -> None:
    await callback.answer()
    await _send_step(callback, "linux", 0)


@router.callback_query(F.data == "instr_tv")
async def instr_tv(callback: CallbackQuery) -> None:
    await callback.answer()
    await _send_step(callback, "tv", 0)


@router.callback_query(F.data.startswith("instr_step_"))
async def instr_step_handler(callback: CallbackQuery) -> None:
    """Навигация по шагам: instr_step_{device}_{idx}"""
    await callback.answer()
    parts = callback.data.split("_")
    # Формат: instr_step_{device}_{idx}
    # parts = ['instr', 'step', device, idx]  — но device может быть 'android_tv'
    # Надёжнее: отрезать 'instr_step_' и split последний '_'
    payload = callback.data[len("instr_step_"):]
    # payload = "android_2" или "android_tv_2"
    last_underscore = payload.rfind("_")
    device = payload[:last_underscore]
    try:
        step_idx = int(payload[last_underscore + 1:])
    except ValueError:
        step_idx = 0
    await _send_step(callback, device, step_idx)
