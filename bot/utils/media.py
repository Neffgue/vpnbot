"""Единый хелпер для работы с медиафайлами в боте.

Устраняет дублирование _resolve_media() из 4 файлов (start.py, support.py, channel.py, cabinet.py).
Логика: если path_or_url — https:// ссылка — возвращаем как есть (Telegram скачает сам).
Если локальный путь — ищем файл на диске и возвращаем BufferedInputFile.
"""
import logging
import os

logger = logging.getLogger(__name__)

# Корневая директория проекта — определяется автоматически
# Universal media resolver for Docker and local environments
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))          # .../bot/utils
_BOT_DIR = os.path.dirname(_THIS_DIR)                           # .../bot
_ROOT_DIR = os.path.dirname(_BOT_DIR)                           # .../vpnbot


async def get_section_media(client, settings_key: str, callback_data: str):
    """Получить медиа для раздела: сначала из settings, потом из image_url кнопки.
    
    Args:
        client: APIClient
        settings_key: ключ в bot_settings (например 'cabinet_image')
        callback_data: callback_data кнопки (например 'cabinet')
    Returns:
        resolved media (URL str или BufferedInputFile) или None
    """
    raw = None
    try:
        settings = await client.get_bot_settings()
        raw = (settings or {}).get(settings_key) or ""
    except Exception:
        pass

    if not raw:
        try:
            raw = await client.get_button_image_url(callback_data) or ""
        except Exception:
            pass

    return resolve_media(raw) if raw else None


def resolve_media(path_or_url: str):
    """Разрешить путь к медиафайлу.

    Возвращает:
    - str (URL) если path_or_url начинается с http:// или https://
    - BufferedInputFile если найден локальный файл
    - None если ничего не найдено
    """
    from aiogram.types import BufferedInputFile

    if not path_or_url:
        return None

    # HTTP/HTTPS ссылки — Telegram скачивает сам, просто возвращаем строку
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url

    # Локальный путь — ищем файл по нескольким возможным расположениям
    candidates = [
        path_or_url,
        os.path.join(_ROOT_DIR, path_or_url.lstrip("/")),
        os.path.join(_ROOT_DIR, "static", "uploads", os.path.basename(path_or_url)),
        os.path.join("/app", path_or_url.lstrip("/")),
        os.path.join("/app", "static", "uploads", os.path.basename(path_or_url)),
        "/app" + (path_or_url if path_or_url.startswith("/") else "/" + path_or_url),
    ]

    for candidate in candidates:
        try:
            if os.path.isfile(candidate):
                with open(candidate, "rb") as f:
                    data = f.read()
                return BufferedInputFile(data, filename=os.path.basename(candidate))
        except Exception:
            continue

    logger.warning(f"Media file not found for path: {path_or_url}")
    return None
