import logging
import os
import json
import traceback
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from backend.database import get_db
from backend.api.deps import get_admin_user
from backend.schemas.admin import (
    UserBalanceUpdate,
    UserBanUpdate,
    BroadcastCreate,
    PlanPriceCreate,
    PlanPriceUpdate,
    PlanPriceResponse,
    BotTextCreate,
    BotTextUpdate,
    BotTextResponse,
    StatsResponse,
    SystemSettingsUpdate,
    SystemSettingsResponse,
)
from backend.schemas.server import ServerCreate, ServerUpdate, ServerDetailResponse
from backend.schemas.user import UserListResponse
from backend.services.user_service import UserService
from backend.services.server_service import ServerService
from backend.services.payment_service import PaymentService
from backend.services.subscription_service import SubscriptionService
from backend.models.config import PlanPrice, BotText, Broadcast
from uuid import uuid4

logger = logging.getLogger(__name__)

router = APIRouter()

# Key used to store system-level settings (bot token, admin creds, etc.) in BotText table
SYSTEM_SETTINGS_KEY = "system_settings_json"
SETTINGS_KEY = "bot_settings_json"


# ── Redis cache invalidation helper ─────────────────────────────────────────
async def _invalidate_bot_cache(*keys: str) -> None:
    """
    Invalidate Redis cache keys used by the Telegram bot.
    Called after any admin PUT/POST/DELETE that changes bot-visible data.
    Silently ignores errors if Redis is unavailable.
    Uses redis-py async client (redis>=4.2) — compatible with modern versions.
    """
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    cache_keys = list(keys) if keys else ["bot:buttons", "bot:texts", "bot:settings", "bot:plans"]
    try:
        from redis.asyncio import from_url as redis_from_url  # redis>=4.2
        redis = await redis_from_url(redis_url, decode_responses=True)
        try:
            if cache_keys:
                await redis.delete(*cache_keys)
                logger.debug(f"Cache invalidated: {cache_keys}")
        finally:
            await redis.aclose()
    except ImportError:
        # redis-py не установлен — пробуем aioredis v2
        try:
            import aioredis  # type: ignore
            redis = aioredis.from_url(redis_url, decode_responses=True)
            await redis.delete(*cache_keys)
            await redis.close()
        except Exception as e2:
            logger.warning(f"Cache invalidation skipped (no redis client): {e2}")
    except Exception as e:
        logger.warning(f"Cache invalidation skipped (Redis unavailable?): {e}")


# ═══════════════════════════════════════════════════════════════
# SYSTEM SETTINGS (bot token, admin credentials — persistent in DB)
# ═══════════════════════════════════════════════════════════════

@router.get("/system-settings", response_model=SystemSettingsResponse)
async def get_system_settings(
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get system-level settings (bot token, admin credentials, etc.)."""
    try:
        stmt = select(BotText).where(BotText.key == SYSTEM_SETTINGS_KEY)
        result = await db.execute(stmt)
        row = result.scalars().first()
        if row:
            data = json.loads(row.value)
        else:
            data = {}
        # Also expose current env values as defaults if not overridden in DB
        return SystemSettingsResponse(
            bot_token=data.get("bot_token", os.getenv("BOT_TOKEN", "")),
            webhook_url=data.get("webhook_url", os.getenv("WEBHOOK_URL", "")),
            admin_username=data.get("admin_username", os.getenv("ADMIN_USERNAME", "admin")),
            min_withdrawal=data.get("min_withdrawal", 10),
            max_daily_withdrawal=data.get("max_daily_withdrawal", 1000),
            referral_percent=data.get("referral_percent", 10),
        )
    except Exception as e:
        logger.error(f"Error getting system settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system settings")


@router.put("/system-settings", response_model=SystemSettingsResponse)
async def update_system_settings(
    data: SystemSettingsUpdate,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Save system-level settings. Bot token is stored securely in DB and applied at runtime."""
    try:
        # Read existing settings first (to merge)
        stmt = select(BotText).where(BotText.key == SYSTEM_SETTINGS_KEY)
        result = await db.execute(stmt)
        row = result.scalars().first()
        existing = json.loads(row.value) if row else {}

        # Merge only provided fields
        update_dict = data.model_dump(exclude_unset=True)
        existing.update(update_dict)

        value = json.dumps(existing, ensure_ascii=False)
        if row:
            row.value = value
        else:
            row = BotText(id=str(uuid4()), key=SYSTEM_SETTINGS_KEY, value=value, description="system_settings")
            db.add(row)
        await db.commit()

        # Apply BOT_TOKEN to current process environment so broadcast works immediately
        if "bot_token" in existing and existing["bot_token"]:
            os.environ["BOT_TOKEN"] = existing["bot_token"]
            os.environ["TELEGRAM_BOT_TOKEN"] = existing["bot_token"]

        logger.info("System settings updated")
        return SystemSettingsResponse(
            bot_token=existing.get("bot_token", ""),
            webhook_url=existing.get("webhook_url", ""),
            admin_username=existing.get("admin_username", "admin"),
            min_withdrawal=existing.get("min_withdrawal", 10),
            max_daily_withdrawal=existing.get("max_daily_withdrawal", 1000),
            referral_percent=existing.get("referral_percent", 10),
        )
    except Exception as e:
        logger.error(f"Error saving system settings: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save system settings")


# ═══════════════════════════════════════════════════════════════
# DASHBOARD STATS
# ═══════════════════════════════════════════════════════════════

@router.get("/stats")
async def get_stats(
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard statistics — total users, active subscriptions, revenue, servers."""
    from backend.models.user import User
    from backend.models.subscription import Subscription
    from backend.models.payment import Payment
    from backend.models.server import Server
    from sqlalchemy import func, and_
    from datetime import timezone, timedelta

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    try:
        # Total users
        total_users_res = await db.execute(select(func.count()).select_from(User))
        total_users = total_users_res.scalar() or 0

        # Active subscriptions
        active_subs_res = await db.execute(
            select(func.count()).select_from(Subscription).where(
                Subscription.is_active == True,
                Subscription.expires_at > now
            )
        )
        active_subscriptions = active_subs_res.scalar() or 0

        # Revenue today
        rev_today_res = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.status == "completed",
                Payment.created_at >= today_start
            )
        )
        revenue_today = float(rev_today_res.scalar() or 0)

        # Revenue this month
        rev_month_res = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.status == "completed",
                Payment.created_at >= month_start
            )
        )
        revenue_month = float(rev_month_res.scalar() or 0)

        # Active servers
        active_servers_res = await db.execute(
            select(func.count()).select_from(Server).where(Server.is_active == True)
        )
        active_servers = active_servers_res.scalar() or 0

        # Pending payments
        pending_res = await db.execute(
            select(func.count()).select_from(Payment).where(Payment.status == "pending")
        )
        pending_payments = pending_res.scalar() or 0

        # Recent activity — last 5 payments
        recent_payments_res = await db.execute(
            select(Payment).order_by(Payment.created_at.desc()).limit(5)
        )
        recent_payments = recent_payments_res.scalars().all()
        recent_activity = []
        for p in recent_payments:
            ts = p.created_at
            if ts:
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                diff = now - ts
                if diff.seconds < 3600:
                    time_str = f"{diff.seconds // 60} мин назад"
                elif diff.days == 0:
                    time_str = f"{diff.seconds // 3600} ч назад"
                else:
                    time_str = f"{diff.days} д назад"
            else:
                time_str = "—"
            recent_activity.append({
                "description": f"Платёж {float(p.amount):.0f}₽ — {p.status}",
                "time": time_str,
            })

        # Servers list
        servers_res = await db.execute(select(Server).limit(10))
        servers = servers_res.scalars().all()
        servers_list = [{"name": s.name, "is_active": s.is_active} for s in servers]

        return {
            "total_users": total_users,
            "active_subscriptions": active_subscriptions,
            "revenue_today": revenue_today,
            "revenue_month": revenue_month,
            "active_servers": active_servers,
            "pending_payments": pending_payments,
            "recent_activity": recent_activity,
            "servers": servers_list,
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        return {
            "total_users": 0,
            "active_subscriptions": 0,
            "revenue_today": 0.0,
            "revenue_month": 0.0,
            "active_servers": 0,
            "pending_payments": 0,
            "recent_activity": [],
            "servers": [],
        }


# ═══════════════════════════════════════════════════════════════
# BOT TEXTS (key→value словарь, без перезагрузки бота)
# ═══════════════════════════════════════════════════════════════

DEFAULT_BOT_TEXTS = {
    "welcome": "👋 Привет! Я VPN бот.\n\nЗдесь ты можешь купить подписку и получить доступ к VPN.",
    "free_trial_success": "🎁 Пробный доступ активирован на 24 часа!\n\nНаслаждайтесь быстрым VPN.",
    "free_trial_used": "❌ Вы уже использовали бесплатный пробный период.",
    "subscription_required": "🔒 Для доступа к этой функции необходима активная подписка.",
    "referral_header": "👥 <b>Реферальная программа</b>\n\nПриглашайте друзей и получайте бонусные дни.",
    "referral_levels": "НОВИЧОК 🌱 — 1-4 реферала: +1 день за каждого\nПРОДВИНУТЫЙ ⭐ — 5-14 рефералов: +2 дня за каждого\nАМБАССАДОР 🏆 — 15+ рефералов: +3 дня за каждого",
    "cabinet_header": "🏠 <b>Личный кабинет</b>\n\nЗдесь вы можете управлять своей подпиской.",
    "support_text": "📩 Свяжитесь с поддержкой: @support",
    "channel_text": "📢 Подпишитесь на наш канал для получения новостей.",
    "payment_success": "✅ Оплата прошла успешно! Подписка активирована.",
    "payment_failed": "❌ Ошибка оплаты. Попробуйте снова или обратитесь в поддержку.",
    "subscription_expiring_24h": "⏰ Ваша подписка истекает через 24 часа. Продлите чтобы не потерять доступ.",
    "subscription_expiring_12h": "⏰ Ваша подписка истекает через 12 часов. Продлите чтобы не потерять доступ.",
    "subscription_expiring_1h": "⚠️ Ваша подписка истекает через 1 час!",
    "subscription_expired": "❌ Ваша подписка истекла. Оформите новую для продолжения работы.",
    "subscription_expired_3h": "❌ Ваша подписка истекла 3 часа назад. Продлите чтобы восстановить доступ.",

}

DEFAULT_BOT_BUTTONS = [
    {"text": "🎁 Бесплатный доступ", "callback_data": "free_trial", "url": "", "row": 0},
    {"text": "💸 Оплатить тариф", "callback_data": "buy_subscription", "url": "", "row": 1},
    {"text": "👤 Личный кабинет", "callback_data": "cabinet", "url": "", "row": 2},
    {"text": "🎁 Получить бесплатно", "callback_data": "get_free", "url": "", "row": 2},
    {"text": "🔗 Реферальная система", "callback_data": "partner", "url": "", "row": 3},
    {"text": "⚙️ Инструкция по подключению", "callback_data": "instructions", "url": "", "row": 3},
    {"text": "👨‍💻 Поддержка", "callback_data": "support", "url": "", "row": 4},
    {"text": "📢 Наш канал", "callback_data": "channel", "url": "", "row": 4},
]


@router.get("/bot-texts")
async def get_bot_texts_dict(
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Вернуть все тексты бота как dict {key: value} для редактора.
    Если записей нет — возвращает дефолтные тексты."""
    try:
        stmt = select(BotText).order_by(BotText.key)
        result = await db.execute(stmt)
        texts = result.scalars().all()
        # Merge: defaults first, then override with DB values
        merged = dict(DEFAULT_BOT_TEXTS)
        for t in texts:
            if t.key not in (SYSTEM_SETTINGS_KEY, SETTINGS_KEY) and not t.key.startswith("btn_"):
                merged[t.key] = t.value
        return merged
    except Exception as e:
        logger.error(f"Error listing bot texts: {e}")
        return dict(DEFAULT_BOT_TEXTS)


@router.put("/bot-texts/{key}")
async def upsert_bot_text_by_key(
    key: str,
    data: dict,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Создать или обновить текст бота по ключу. Изменения мгновенны."""
    value = data.get("value", "")
    try:
        stmt = select(BotText).where(BotText.key == key)
        result = await db.execute(stmt)
        existing = result.scalars().first()

        if existing:
            existing.value = value
        else:
            existing = BotText(id=str(uuid4()), key=key, value=value)
            db.add(existing)

        await db.commit()
        await db.refresh(existing)
        await _invalidate_bot_cache("bot:texts")
        logger.info(f"Bot text updated: {key}")
        return {"key": existing.key, "value": existing.value}
    except Exception as e:
        logger.error(f"Error upserting bot text {key}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save bot text")


@router.delete("/bot-texts/{key}")
async def delete_bot_text_by_key(
    key: str,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Удалить текст бота по ключу."""
    try:
        stmt = select(BotText).where(BotText.key == key)
        result = await db.execute(stmt)
        existing = result.scalars().first()
        if existing:
            await db.delete(existing)
            await db.commit()
            await _invalidate_bot_cache("bot:texts")
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting bot text {key}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete bot text")


# ═══════════════════════════════════════════════════════════════
# BOT BUTTONS (кнопки меню, без перезагрузки)
# ═══════════════════════════════════════════════════════════════

@router.get("/bot-buttons")
async def get_bot_buttons(
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить список кнопок главного меню из БД.
    Если кнопок нет — возвращает дефолтные кнопки бота."""
    try:
        stmt = select(BotText).where(BotText.key.like("btn_%")).order_by(BotText.key)
        result = await db.execute(stmt)
        rows = result.scalars().all()
        buttons = []
        for r in rows:
            try:
                btn = json.loads(r.value)
                btn["id"] = r.key
                buttons.append(btn)
            except Exception:
                pass
        # If no buttons in DB, return defaults so admin can see what bot currently uses
        if not buttons:
            buttons = [
                {"id": f"default_{i}", **btn}
                for i, btn in enumerate(DEFAULT_BOT_BUTTONS)
            ]
        return {"buttons": buttons}
    except Exception as e:
        logger.error(f"Error getting bot buttons: {e}")
        return {"buttons": [{"id": f"default_{i}", **btn} for i, btn in enumerate(DEFAULT_BOT_BUTTONS)]}


@router.post("/bot-buttons")
async def create_bot_button(
    data: dict,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Добавить новую кнопку меню. Если кнопок в БД нет — сначала сохраняем дефолтные, затем добавляем новую."""
    # Проверяем — есть ли уже кнопки в БД
    stmt = select(BotText).where(BotText.key.like("btn_%"))
    result = await db.execute(stmt)
    existing = result.scalars().all()

    # Если кнопок нет — сначала сохраняем дефолтные в БД (чтобы они не пропали)
    if not existing:
        for i, default_btn in enumerate(DEFAULT_BOT_BUTTONS):
            default_key = f"btn_{uuid4().hex[:8]}"
            default_value = json.dumps({
                "text": default_btn["text"],
                "callback_data": default_btn["callback_data"],
                "url": default_btn.get("url", ""),
                "row": default_btn["row"],
            }, ensure_ascii=False)
            db.add(BotText(id=str(uuid4()), key=default_key, value=default_value, description="menu_button"))
        await db.commit()

    # Теперь добавляем новую кнопку
    key = f"btn_{uuid4().hex[:8]}"
    btn_data = {
        "text": data.get("text", ""),
        "callback_data": data.get("callback_data", ""),
        "url": data.get("url", ""),
        "row": data.get("row", 0),
        "image_url": data.get("image_url", ""),
    }
    value = json.dumps(btn_data, ensure_ascii=False)
    btn = BotText(id=str(uuid4()), key=key, value=value, description="menu_button")
    db.add(btn)
    await db.commit()
    await _invalidate_bot_cache("bot:buttons")
    return {"id": key, **btn_data}


@router.put("/bot-buttons/{btn_id}")
async def update_bot_button(
    btn_id: str,
    data: dict,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Обновить кнопку меню (полная замена)."""
    stmt = select(BotText).where(BotText.key == btn_id)
    result = await db.execute(stmt)
    btn = result.scalars().first()
    if not btn:
        raise HTTPException(status_code=404, detail="Button not found")
    # Read existing data first to preserve fields not provided
    try:
        existing = json.loads(btn.value)
    except Exception:
        existing = {}
    existing.update({
        "text": data.get("text", existing.get("text", "")),
        "callback_data": data.get("callback_data", existing.get("callback_data", "")),
        "url": data.get("url", existing.get("url", "")),
        "row": data.get("row", existing.get("row", 0)),
        "image_url": data.get("image_url", existing.get("image_url", "")),
    })
    btn.value = json.dumps(existing, ensure_ascii=False)
    await db.commit()
    await _invalidate_bot_cache("bot:buttons")
    return {"success": True}


@router.patch("/bot-buttons/{btn_id}")
async def patch_bot_button(
    btn_id: str,
    data: dict,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Частичное обновление кнопки меню — обновляет только переданные поля, остальные сохраняются."""
    stmt = select(BotText).where(BotText.key == btn_id)
    result = await db.execute(stmt)
    btn = result.scalars().first()
    if not btn:
        raise HTTPException(status_code=404, detail="Button not found")
    # Load existing data
    try:
        existing = json.loads(btn.value)
    except Exception:
        existing = {}
    # Merge: only update fields that are explicitly provided in request
    for field in ("text", "callback_data", "url", "row", "image_url"):
        if field in data:
            existing[field] = data[field]
    btn.value = json.dumps(existing, ensure_ascii=False)
    await db.commit()
    await _invalidate_bot_cache("bot:buttons")
    logger.info(f"Bot button {btn_id} partially updated: {list(data.keys())}")
    return {"success": True, "id": btn_id, **existing}


@router.delete("/bot-buttons/{btn_id}")
async def delete_bot_button(
    btn_id: str,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Удалить кнопку меню."""
    stmt = select(BotText).where(BotText.key == btn_id)
    result = await db.execute(stmt)
    btn = result.scalars().first()
    if btn:
        await db.delete(btn)
        await db.commit()
        await _invalidate_bot_cache("bot:buttons")
    return {"success": True}


# ═══════════════════════════════════════════════════════════════
# BOT SETTINGS (настройки — поддержка, канал, медиа, реферал...)
# ═══════════════════════════════════════════════════════════════

@router.get("/settings")
async def get_bot_settings(
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить настройки бота как dict."""
    try:
        stmt = select(BotText).where(BotText.key == SETTINGS_KEY)
        result = await db.execute(stmt)
        row = result.scalars().first()
        if row:
            return json.loads(row.value)
        return {}
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        return {}


@router.put("/settings")
async def save_bot_settings(
    data: dict,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Сохранить настройки бота. Изменения применяются мгновенно."""
    try:
        value = json.dumps(data, ensure_ascii=False)
        stmt = select(BotText).where(BotText.key == SETTINGS_KEY)
        result = await db.execute(stmt)
        row = result.scalars().first()
        if row:
            row.value = value
        else:
            row = BotText(id=str(uuid4()), key=SETTINGS_KEY, value=value, description="bot_settings")
            db.add(row)
        await db.commit()
        await db.refresh(row)
        await _invalidate_bot_cache("bot:settings")
        return data
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save settings")


# ═══════════════════════════════════════════════════════════════
# UPLOAD IMAGE
# ═══════════════════════════════════════════════════════════════

# При запуске через uWSGI __file__ = .../vpnbot/backend/api/v1/endpoints/admin.py
# Идём вверх: endpoints → v1 → api → backend → vpnbot
_ENDPOINTS_DIR = os.path.dirname(os.path.abspath(__file__))   # .../backend/api/v1/endpoints
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(_ENDPOINTS_DIR)))  # .../backend
_ROOT_DIR = os.path.dirname(_BACKEND_DIR)                     # .../vpnbot
ROOT_STATIC_DIR = os.path.join(_ROOT_DIR, "static")
STATIC_DIR = ROOT_STATIC_DIR if os.path.isdir(ROOT_STATIC_DIR) else os.path.join(_BACKEND_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")

@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    current_user=Depends(get_admin_user),
):
    """Загрузить изображение для бота (welcome, plan, etc.)."""
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
        if ext not in ("jpg", "jpeg", "png", "gif", "webp"):
            raise HTTPException(status_code=400, detail="Unsupported file type")
        filename = f"{uuid4().hex}.{ext}"
        path = os.path.join(UPLOAD_DIR, filename)
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 5MB)")
        with open(path, "wb") as f:
            f.write(content)
        # Возвращаем полный URL (используем BACKEND_URL или строим из запроса)
        base_url = os.getenv("BACKEND_URL", "").rstrip("/")
        if base_url:
            url = f"{base_url}/static/uploads/{filename}"
        else:
            url = f"/static/uploads/{filename}"
        return {"url": url, "filename": filename, "relative_url": f"/static/uploads/{filename}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")


# ═══════════════════════════════════════════════════════════════
# BROADCAST (text + optional image)
# ═══════════════════════════════════════════════════════════════

@router.post("/broadcast")
@router.post("/broadcasts")
async def create_broadcast(
    data: BroadcastCreate,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Send broadcast message to users via Telegram Bot API."""
    import httpx as _httpx
    bot_token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        # Try to load from DB
        try:
            stmt = select(BotText).where(BotText.key == SYSTEM_SETTINGS_KEY)
            result = await db.execute(stmt)
            row = result.scalars().first()
            if row:
                sys_data = json.loads(row.value)
                bot_token = sys_data.get("bot_token", "")
        except Exception:
            pass
    if not bot_token:
        raise HTTPException(status_code=400, detail="BOT_TOKEN not configured")

    # Get target users
    from backend.models.user import User
    from backend.models.subscription import Subscription
    from datetime import timezone as _tz

    if data.user_ids:
        stmt = select(User).where(User.telegram_id.in_(data.user_ids))
    elif data.target == "active":
        now = datetime.now(_tz.utc)
        stmt = (
            select(User)
            .join(Subscription, Subscription.user_id == User.id)
            .where(Subscription.is_active == True, Subscription.expires_at > now)
        )
    elif data.target == "trial":
        stmt = select(User).where(User.free_trial_used == True)
    elif data.target == "expired":
        now = datetime.now(_tz.utc)
        stmt = (
            select(User)
            .join(Subscription, Subscription.user_id == User.id)
            .where(Subscription.is_active == False)
        )
    else:
        stmt = select(User).where(User.is_banned == False)

    result = await db.execute(stmt)
    users = result.scalars().all()

    sent = 0
    failed = 0
    tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    async with _httpx.AsyncClient(timeout=30) as http:
        for user in users:
            if not user.telegram_id:
                continue
            try:
                resp = await http.post(tg_url, json={
                    "chat_id": user.telegram_id,
                    "text": data.message,
                    "parse_mode": "HTML",
                })
                if resp.status_code == 200:
                    sent += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

    logger.info(f"Broadcast sent: {sent} ok, {failed} failed")
    return {"success": True, "sent_count": sent, "success_count": sent, "failed_count": failed}


async def _do_broadcast_image(
    bot_token: str,
    img_content: bytes,
    img_filename: str,
    img_content_type: str,
    message: Optional[str],
    telegram_ids: list,
) -> None:
    """Background task: send photo broadcast to all target users.
    Runs fully asynchronously after HTTP response has been returned (202 Accepted).
    """
    import httpx as _httpx
    import asyncio

    tg_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    sent = 0
    failed = 0

    async with _httpx.AsyncClient(timeout=30) as http:
        for tg_id in telegram_ids:
            if not tg_id:
                continue
            try:
                files = {"photo": (img_filename, img_content, img_content_type)}
                params = {"chat_id": tg_id, "parse_mode": "HTML"}
                if message:
                    params["caption"] = message
                resp = await http.post(tg_url, data=params, files=files)
                if resp.status_code == 200:
                    sent += 1
                else:
                    failed += 1
                    logger.warning(f"TG API error {resp.status_code} for {tg_id}: {resp.text[:200]}")
            except Exception as e:
                logger.error(f"Broadcast image send error to {tg_id}: {e}")
                failed += 1
            # Respect Telegram rate limit: ~30 msgs/sec
            await asyncio.sleep(0.04)

    logger.info(f"[background] Broadcast-image finished: {sent} sent, {failed} failed")


@router.post("/broadcast-image", status_code=202)
async def create_broadcast_image(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    message: Optional[str] = Form(default=None),
    target: str = Form(default="all"),
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept broadcast-with-image request and immediately return 202 Accepted.
    The actual sending is delegated to a BackgroundTask so the HTTP connection
    is never held open during large broadcasts (prevents ERR_CONNECTION_RESET).
    """
    # Resolve bot token
    bot_token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        try:
            stmt = select(BotText).where(BotText.key == SYSTEM_SETTINGS_KEY)
            result = await db.execute(stmt)
            row = result.scalars().first()
            if row:
                bot_token = json.loads(row.value).get("bot_token", "")
        except Exception:
            pass
    if not bot_token:
        raise HTTPException(status_code=400, detail="BOT_TOKEN not configured")

    # Read & validate image NOW (before response is sent)
    img_content = await image.read()
    if len(img_content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")
    img_filename = image.filename or "image.jpg"
    img_content_type = image.content_type or "image/jpeg"

    # Collect target user telegram_ids from DB
    from backend.models.user import User
    from backend.models.subscription import Subscription
    from datetime import timezone as _tz

    if target == "active":
        now = datetime.now(_tz.utc)
        stmt = (
            select(User.telegram_id)
            .join(Subscription, Subscription.user_id == User.id)
            .where(Subscription.is_active == True, Subscription.expires_at > now)
        )
    elif target == "expired":
        stmt = (
            select(User.telegram_id)
            .join(Subscription, Subscription.user_id == User.id)
            .where(Subscription.is_active == False)
        )
    elif target == "trial":
        stmt = select(User.telegram_id).where(User.free_trial_used == True)
    else:
        stmt = select(User.telegram_id).where(User.is_banned == False)

    result = await db.execute(stmt)
    telegram_ids = [row[0] for row in result.fetchall() if row[0]]

    logger.info(
        f"Broadcast-image queued: target={target!r}, users={len(telegram_ids)}, "
        f"message_len={len(message or '')}"
    )

    # Enqueue background task — response is returned immediately after this
    background_tasks.add_task(
        _do_broadcast_image,
        bot_token,
        img_content,
        img_filename,
        img_content_type,
        message,
        telegram_ids,
    )

    return JSONResponse(
        status_code=202,
        content={
            "success": True,
            "status": "accepted",
            "queued_users": len(telegram_ids),
            "message": f"Рассылка принята в обработку. Будет отправлена {len(telegram_ids)} пользователям.",
        },
    )


# ═══════════════════════════════════════════════════════════════
# ADD SUBSCRIPTION DAYS
# ═══════════════════════════════════════════════════════════════

@router.post("/users/{user_id}/add-days")
async def add_subscription_days(
    user_id: str,
    data: dict,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Добавить дни к активной подписке пользователя."""
    from datetime import timedelta
    days = int(data.get("days", 0))
    if days <= 0:
        raise HTTPException(status_code=400, detail="days must be > 0")

    user_service = UserService(db)
    user = await user_service.get_user(user_id)
    if not user:
        # Попробуем по telegram_id
        try:
            tg_id = int(user_id)
            user = await user_service.get_user_by_telegram_id(tg_id)
        except (ValueError, TypeError):
            pass
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sub_service = SubscriptionService(db)
    sub = await sub_service.get_active_user_subscription(user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription")

    new_expires = sub.expires_at + timedelta(days=days)
    await sub_service.repo.update(sub.id, {"expires_at": new_expires})
    logger.info(f"Added {days} days to user {user_id} subscription")
    return {"success": True, "days_added": days, "new_expires_at": new_expires.isoformat()}


# ============ Payments (admin) ============

@router.get("/payments")
async def list_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=1000),
    status: Optional[str] = Query(None),
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all payments (admin only)."""
    from backend.models.payment import Payment
    stmt = select(Payment).order_by(Payment.created_at.desc()).offset(skip).limit(limit)
    if status:
        stmt = select(Payment).where(Payment.status == status).order_by(Payment.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    payments = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "user_id": str(p.user_id),
            "amount": float(p.amount),
            "status": p.status,
            "payment_method": getattr(p, "payment_method", "unknown"),
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if hasattr(p, "updated_at") and p.updated_at else None,
        }
        for p in payments
    ]


@router.get("/payments/{payment_id}")
async def get_payment(
    payment_id: str,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get single payment (admin only)."""
    from backend.models.payment import Payment
    payment = await db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {
        "id": str(payment.id),
        "user_id": str(payment.user_id),
        "amount": float(payment.amount),
        "status": payment.status,
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
    }


# ============ Subscriptions (admin) ============

@router.get("/subscriptions")
async def list_subscriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=1000),
    status: Optional[str] = Query(None),
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all subscriptions (admin only)."""
    from backend.models.subscription import Subscription
    stmt = select(Subscription).order_by(Subscription.created_at.desc()).offset(skip).limit(limit)
    if status == "active":
        from datetime import timezone
        now = datetime.utcnow()
        stmt = select(Subscription).where(
            Subscription.is_active == True,
            Subscription.expires_at > now,
        ).order_by(Subscription.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    subs = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "user_id": str(s.user_id),
            "plan_name": getattr(s, "plan_name", ""),
            "is_active": s.is_active,
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "max_devices": getattr(s, "max_devices", 1),
        }
        for s in subs
    ]


@router.post("/subscriptions/{sub_id}/extend")
async def extend_subscription(
    sub_id: str,
    data: dict,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Extend subscription by days (admin only)."""
    from datetime import timedelta
    from backend.models.subscription import Subscription
    sub = await db.get(Subscription, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    days = int(data.get("days", 30))
    sub.expires_at = sub.expires_at + timedelta(days=days)
    await db.commit()
    return {"success": True, "days_added": days, "new_expires_at": sub.expires_at.isoformat()}


@router.post("/subscriptions/{sub_id}/cancel")
async def cancel_subscription(
    sub_id: str,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel subscription (admin only)."""
    from backend.models.subscription import Subscription
    sub = await db.get(Subscription, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    sub.is_active = False
    await db.commit()
    return {"success": True}


# ============ User Management ============

@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: str,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get single user detail (admin only). Accepts telegram_id or UUID."""
    service = UserService(db)
    user = None
    try:
        tg_id = int(user_id)
        user = await service.get_user_by_telegram_id(tg_id)
    except (ValueError, TypeError):
        pass
    if not user:
        user = await service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/users/{user_id}/subscriptions")
async def get_user_subscriptions(
    user_id: str,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user subscriptions (admin only)."""
    from backend.models.subscription import Subscription
    service = UserService(db)
    user = None
    try:
        tg_id = int(user_id)
        user = await service.get_user_by_telegram_id(tg_id)
    except (ValueError, TypeError):
        pass
    if not user:
        user = await service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id).order_by(Subscription.created_at.desc())
    )
    subs = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "plan_name": getattr(s, "plan_name", ""),
            "is_active": s.is_active,
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in subs
    ]


@router.get("/users/{user_id}/payments")
async def get_user_payments(
    user_id: str,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user payments (admin only)."""
    from backend.models.payment import Payment
    service = UserService(db)
    user = None
    try:
        tg_id = int(user_id)
        user = await service.get_user_by_telegram_id(tg_id)
    except (ValueError, TypeError):
        pass
    if not user:
        user = await service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    result = await db.execute(
        select(Payment).where(Payment.user_id == user.id).order_by(Payment.created_at.desc())
    )
    payments = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "amount": float(p.amount),
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in payments
    ]


@router.get("/users/{user_id}/referrals")
async def get_user_referrals(
    user_id: str,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user referrals (admin only)."""
    from backend.models.referral import Referral
    service = UserService(db)
    user = None
    try:
        tg_id = int(user_id)
        user = await service.get_user_by_telegram_id(tg_id)
    except (ValueError, TypeError):
        pass
    if not user:
        user = await service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    result = await db.execute(
        select(Referral).where(Referral.referrer_id == user.id).order_by(Referral.created_at.desc())
    )
    refs = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "referred_id": str(r.referred_id),
            "bonus_days": r.bonus_days,
            "is_paid": r.paid_at is not None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in refs
    ]


@router.get("/users", response_model=list[UserListResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100000),
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all users with pagination (admin only).
    """
    service = UserService(db)
    users = await service.get_all_users(skip, limit)
    return users


@router.get("/users/search")
async def search_users(
    query: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Search users by username, first_name, or telegram_id (admin only).
    """
    service = UserService(db)
    users = await service.search_users(query, skip, limit)
    return users


@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    data: UserBanUpdate,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Ban a user (admin only). Accepts telegram_id or internal UUID.
    """
    service = UserService(db)
    user = None
    try:
        tg_id = int(user_id)
        user = await service.get_user_by_telegram_id(tg_id)
    except (ValueError, TypeError):
        pass
    if not user:
        user = await service.get_user(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    updated = await service.ban_user(user.id)
    logger.info(f"User {user_id} banned by admin")
    return {"success": True, "user_id": user_id, "is_banned": True}


@router.post("/users/{user_id}/unban")
async def unban_user(
    user_id: str,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Unban a user (admin only). Accepts telegram_id or internal UUID.
    """
    service = UserService(db)
    user = None
    try:
        tg_id = int(user_id)
        user = await service.get_user_by_telegram_id(tg_id)
    except (ValueError, TypeError):
        pass
    if not user:
        user = await service.get_user(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    updated = await service.unban_user(user.id)
    logger.info(f"User {user_id} unbanned by admin")
    return {"success": True, "user_id": user_id, "is_banned": False}


@router.post("/users/{user_id}/balance")
async def update_user_balance(
    user_id: str,
    data: UserBalanceUpdate,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add or deduct balance from user account (admin only).
    Accepts telegram_id or internal UUID as user_id.
    """
    service = UserService(db)
    user = None
    # Try telegram_id first
    try:
        tg_id = int(user_id)
        user = await service.get_user_by_telegram_id(tg_id)
    except (ValueError, TypeError):
        pass
    if not user:
        user = await service.get_user(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    updated = await service.add_balance(user.id, data.amount)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update balance",
        )

    logger.info(f"User {user_id} balance updated by {data.amount}. Reason: {data.reason}")
    return updated


# ============ Server Management ============

@router.get("/servers", response_model=list[ServerDetailResponse])
async def list_servers(
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all VPN servers (admin only)."""
    service = ServerService(db)
    servers = await service.get_all_servers()
    return servers


@router.get("/servers/{server_id}", response_model=ServerDetailResponse)
async def get_server(
    server_id: str,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single VPN server (admin only)."""
    service = ServerService(db)
    server = await service.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.post("/servers/{server_id}/toggle-active")
async def toggle_server_active(
    server_id: str,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle server active status (admin only)."""
    service = ServerService(db)
    server = await service.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    updated = await service.update_server(server_id, is_active=not server.is_active)
    return {"success": True, "is_active": updated.is_active}


@router.post("/servers/{server_id}/test-connection")
async def test_server_connection(
    server_id: str,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Test connection to VPN server (admin only)."""
    service = ServerService(db)
    server = await service.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    try:
        result = await service.test_server_connection(server_id)
        return {"success": True, "status": "connected"}
    except Exception as e:
        return {"success": False, "status": "failed", "error": str(e)}


@router.post("/servers", response_model=ServerDetailResponse)
async def create_server(
    server_data: ServerCreate,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new VPN server (admin only).
    """
    service = ServerService(db)

    # Check if server with same name already exists
    existing = await service.get_server_by_name(server_data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server with this name already exists",
        )

    server = await service.create_server(
        name=server_data.name,
        country_emoji=server_data.country_emoji,
        country_name=server_data.country_name,
        host=server_data.host,
        port=server_data.port,
        panel_url=server_data.panel_url,
        panel_username=server_data.panel_username,
        panel_password=server_data.panel_password,
        inbound_id=server_data.inbound_id,
        bypass_ru_whitelist=server_data.bypass_ru_whitelist,
        order_index=server_data.order_index,
    )

    logger.info(f"Server {server.name} created by admin")
    return server


@router.put("/servers/{server_id}", response_model=ServerDetailResponse)
async def update_server(
    server_id: str,
    server_data: ServerUpdate,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a VPN server (admin only).
    """
    service = ServerService(db)
    server = await service.get_server(server_id)

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    # Check if new name already exists (if name is being changed)
    if server_data.name and server_data.name != server.name:
        existing = await service.get_server_by_name(server_data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Server with this name already exists",
            )

    update_data = {k: v for k, v in server_data.dict().items() if v is not None}
    updated = await service.update_server(server_id, **update_data)

    logger.info(f"Server {server_id} updated by admin")
    return updated


@router.delete("/servers/{server_id}")
async def delete_server(
    server_id: str,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a VPN server (admin only).
    """
    service = ServerService(db)
    server = await service.get_server(server_id)

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    await service.delete_server(server_id)
    logger.info(f"Server {server_id} deleted by admin")
    return {"detail": "Server deleted"}


# ============ Plan Pricing ============

@router.get("/plans", response_model=list[PlanPriceResponse])
async def list_plan_prices(
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all plan prices (admin only).
    """
    try:
        stmt = select(PlanPrice).order_by(PlanPrice.plan_name, PlanPrice.period_days)
        result = await db.execute(stmt)
        prices = result.scalars().all()
        return prices
    except Exception as e:
        logger.error(f"Error listing plan prices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list plans",
        )


@router.post("/plans", response_model=PlanPriceResponse)
async def create_plan_price(
    plan_data: PlanPriceCreate,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create or update a plan price (admin only).
    """
    try:
        # Check if already exists
        stmt = select(PlanPrice).where(
            (PlanPrice.plan_name == plan_data.plan_name)
            & (PlanPrice.period_days == plan_data.period_days)
        )
        result = await db.execute(stmt)
        existing = result.scalars().first()

        if existing:
            existing.price_rub = plan_data.price_rub
            if plan_data.name is not None:
                existing.name = plan_data.name
            if plan_data.device_limit is not None:
                existing.device_limit = plan_data.device_limit
            if plan_data.description is not None:
                existing.description = plan_data.description
            if plan_data.is_active is not None:
                existing.is_active = plan_data.is_active
            await db.commit()
            await db.refresh(existing)
            await _invalidate_bot_cache("bot:plans")
            logger.info(f"Plan price updated: {plan_data.plan_name} {plan_data.period_days}d")
            return existing

        # Create new
        plan_price = PlanPrice(
            id=str(uuid4()),
            plan_name=plan_data.plan_name,
            period_days=plan_data.period_days,
            price_rub=plan_data.price_rub,
            name=plan_data.name,
            device_limit=plan_data.device_limit if plan_data.device_limit is not None else 1,
            description=plan_data.description,
            is_active=plan_data.is_active if plan_data.is_active is not None else True,
        )
        db.add(plan_price)
        await db.commit()
        await db.refresh(plan_price)
        await _invalidate_bot_cache("bot:plans")
        logger.info(f"Plan price created: {plan_data.plan_name} {plan_data.period_days}d")
        return plan_price
    except Exception as e:
        logger.error(f"Error creating plan price: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create plan price: {str(e)}",
        )


@router.put("/plans/{plan_id}", response_model=PlanPriceResponse)
async def update_plan_price(
    plan_id: str,
    plan_data: PlanPriceUpdate,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a plan price by ID (admin only)."""
    try:
        plan = await db.get(PlanPrice, plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        if plan_data.plan_name is not None:
            plan.plan_name = plan_data.plan_name
        if plan_data.period_days is not None:
            plan.period_days = plan_data.period_days
        if plan_data.price_rub is not None:
            plan.price_rub = plan_data.price_rub
        if plan_data.name is not None:
            plan.name = plan_data.name
        if plan_data.device_limit is not None:
            plan.device_limit = plan_data.device_limit
        if plan_data.image_url is not None:
            plan.image_url = plan_data.image_url
        if plan_data.description is not None:
            plan.description = plan_data.description
        if plan_data.is_active is not None:
            plan.is_active = plan_data.is_active
        await db.commit()
        await db.refresh(plan)
        await _invalidate_bot_cache("bot:plans")
        logger.info(f"Plan price {plan_id} updated")
        return plan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating plan: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update plan price: {str(e)}")


@router.delete("/plans/{plan_id}")
async def delete_plan_price(
    plan_id: str,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a plan price (admin only).
    """
    try:
        plan = await db.get(PlanPrice, plan_id)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found",
            )

        await db.delete(plan)
        await db.commit()
        await _invalidate_bot_cache("bot:plans")
        logger.info(f"Plan price {plan_id} deleted")
        return {"detail": "Plan deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting plan: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete plan",
        )


# ============ Bot Configuration ============
# NOTE: GET /bot-texts is already defined above as a dict endpoint.
# The list endpoint below is kept only for internal use with a different path.


@router.post("/bot-texts", response_model=BotTextResponse)
async def create_bot_text(
    text_data: BotTextCreate,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create or update a bot text (admin only).
    """
    try:
        stmt = select(BotText).where(BotText.key == text_data.key)
        result = await db.execute(stmt)
        existing = result.scalars().first()

        if existing:
            existing.value = text_data.value
            if text_data.description:
                existing.description = text_data.description
            await db.commit()
            await db.refresh(existing)
            logger.info(f"Bot text updated: {text_data.key}")
            return existing

        bot_text = BotText(
            id=str(uuid4()),
            key=text_data.key,
            value=text_data.value,
            description=text_data.description,
        )
        db.add(bot_text)
        await db.commit()
        await db.refresh(bot_text)
        logger.info(f"Bot text created: {text_data.key}")
        return bot_text
    except Exception as e:
        logger.error(f"Error creating bot text: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create bot text",
        )


@router.put("/bot-texts/{text_id}", response_model=BotTextResponse)
async def update_bot_text(
    text_id: str,
    text_data: BotTextUpdate,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a bot text (admin only).
    """
    try:
        bot_text = await db.get(BotText, text_id)
        if not bot_text:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot text not found",
            )

        bot_text.value = text_data.value
        if text_data.description:
            bot_text.description = text_data.description

        await db.commit()
        await db.refresh(bot_text)
        logger.info(f"Bot text {text_id} updated")
        return bot_text
    except Exception as e:
        logger.error(f"Error updating bot text: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update bot text",
        )


@router.delete("/bot-texts/{text_id}")
async def delete_bot_text(
    text_id: str,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a bot text (admin only).
    """
    try:
        bot_text = await db.get(BotText, text_id)
        if not bot_text:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot text not found",
            )

        await db.delete(bot_text)
        await db.commit()
        logger.info(f"Bot text {text_id} deleted")
        return {"detail": "Bot text deleted"}
    except Exception as e:
        logger.error(f"Error deleting bot text: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete bot text",
        )


# ═══════════════════════════════════════════════════════════════
# STATISTICS
# ═══════════════════════════════════════════════════════════════

@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get system statistics (admin only).
    """
    from decimal import Decimal as D
    from datetime import date, timedelta
    from sqlalchemy import func
    from backend.models.payment import Payment
    from backend.models.subscription import Subscription
    from backend.models.server import Server
    from backend.models.referral import Referral
    from backend.models.user import User

    try:
        user_service = UserService(db)
        subscription_service = SubscriptionService(db)
        payment_service = PaymentService(db)

        total_users = await user_service.repo.count()
        banned_users = await user_service.repo.count_banned_users()
        active_subscriptions = await subscription_service.count_active_subscriptions()
        total_revenue = await payment_service.get_total_revenue()
        pending_payments = await payment_service.count_pending_payments()
        completed_payments = await payment_service.count_completed_payments()

        # Revenue today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        rev_today_res = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.status == "completed",
                Payment.created_at >= today_start,
            )
        )
        revenue_today = D(str(rev_today_res.scalar() or 0))

        # Revenue this month
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        rev_month_res = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.status == "completed",
                Payment.created_at >= month_start,
            )
        )
        revenue_month = D(str(rev_month_res.scalar() or 0))

        # Active servers
        servers_res = await db.execute(
            select(func.count(Server.id)).where(Server.is_active == True)
        )
        active_servers = servers_res.scalar() or 0

        # Free trials used
        trials_res = await db.execute(
            select(func.count(User.id)).where(User.free_trial_used == True)
        )
        free_trials_used = trials_res.scalar() or 0

        # Active referrals (paid)
        refs_res = await db.execute(
            select(func.count(Referral.id)).where(Referral.paid_at.isnot(None))
        )
        active_referrals = refs_res.scalar() or 0

        return StatsResponse(
            total_users=total_users,
            banned_users=banned_users,
            active_subscriptions=active_subscriptions,
            total_revenue=total_revenue,
            pending_payments=pending_payments,
            completed_payments=completed_payments,
            revenue_today=revenue_today,
            revenue_month=revenue_month,
            monthly_revenue=revenue_month,
            active_servers=active_servers,
            free_trials_used=free_trials_used,
            active_referrals=active_referrals,
        )
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics",
        )


# ═══════════════════════════════════════════════════════════════
# PATCH alias for bot-buttons (бот использует PATCH)
# ═══════════════════════════════════════════════════════════════

# PATCH /bot-buttons/{btn_id} — handled above (see patch_bot_button_admin at line ~494)


# ═══════════════════════════════════════════════════════════════
# SUBSCRIPTION PLANS — изменение цен
# ═══════════════════════════════════════════════════════════════

@router.get("/subscriptions/plans")
async def get_subscription_plans_admin(
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить все тарифные планы из PlanPrice (единый источник истины для бота и фронтенда)."""
    try:
        stmt = select(PlanPrice).where(PlanPrice.is_active == True).order_by(PlanPrice.plan_name, PlanPrice.period_days)
        result = await db.execute(stmt)
        plans = result.scalars().all()
        return [
            {
                "id": str(p.id),
                "plan_name": p.plan_name,
                "name": p.name or p.plan_name.capitalize(),
                "price_rub": float(p.price_rub),
                "price": float(p.price_rub),
                "period_days": p.period_days,
                "duration_days": p.period_days,
                "device_limit": p.device_limit if p.device_limit is not None else 1,
                "devices": p.device_limit if p.device_limit is not None else 1,
                "image_url": p.image_url or "",
                "description": p.description or "",
                "is_active": p.is_active,
            }
            for p in plans
        ]
    except Exception as e:
        logger.error(f"Error getting plans: {e}", exc_info=True)
        return []


@router.patch("/subscriptions/plans/{plan_id}")
async def update_subscription_plan_price(
    plan_id: str,
    data: dict,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Обновить цену и параметры тарифного плана. Принимает UUID или name."""
    from backend.models.subscription import SubscriptionPlan
    try:
        # Сначала ищем по id
        result = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        )
        plan = result.scalars().first()
        # Если не нашли по id — ищем по name
        if not plan:
            result = await db.execute(
                select(SubscriptionPlan).where(SubscriptionPlan.name == plan_id)
            )
            plan = result.scalars().first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        if "price" in data:
            plan.price = float(data["price"])
        if "name" in data:
            plan.name = data["name"]
        if "duration_days" in data:
            plan.duration_days = int(data["duration_days"])
        if "is_active" in data:
            plan.is_active = bool(data["is_active"])

        await db.commit()
        await db.refresh(plan)
        return {
            "id": str(plan.id),
            "name": plan.name,
            "price": float(plan.price),
            "duration_days": plan.duration_days,
            "is_active": plan.is_active,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating plan: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update plan: {e}")


# ═══════════════════════════════════════════════════════════════
# INSTRUCTIONS — управление шагами и изображениями
# ═══════════════════════════════════════════════════════════════

INSTRUCTION_STEPS_KEY_PREFIX = "instr_"


@router.get("/instructions/{device}/steps")
async def get_instruction_steps_admin(
    device: str,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить шаги инструкции для устройства."""
    key_prefix = f"{INSTRUCTION_STEPS_KEY_PREFIX}{device}_"
    try:
        result = await db.execute(
            select(BotText).where(BotText.key.like(f"{key_prefix}%")).order_by(BotText.key)
        )
        rows = result.scalars().all()
        steps = []
        for r in rows:
            try:
                step = json.loads(r.value)
                step["id"] = r.key
                steps.append(step)
            except Exception:
                pass
        return steps
    except Exception as e:
        logger.error(f"Error getting instruction steps: {e}")
        return []


@router.patch("/instructions/{device}/steps/{step_num}")
async def update_instruction_step(
    device: str,
    step_num: int,
    data: dict,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Обновить шаг инструкции (изображение и т.д.)."""
    key = f"{INSTRUCTION_STEPS_KEY_PREFIX}{device}_{step_num:03d}"
    try:
        result = await db.execute(select(BotText).where(BotText.key == key))
        existing = result.scalars().first()

        if existing:
            step_data = json.loads(existing.value)
            step_data.update(data)
            existing.value = json.dumps(step_data, ensure_ascii=False)
        else:
            step_data = {"step_number": step_num, "device": device, **data}
            existing = BotText(
                id=str(uuid4()),
                key=key,
                value=json.dumps(step_data, ensure_ascii=False),
                description=f"instruction_step_{device}_{step_num}"
            )
            db.add(existing)

        await db.commit()
        return {"success": True, "key": key, **step_data}
    except Exception as e:
        logger.error(f"Error updating instruction step: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update step: {e}")
