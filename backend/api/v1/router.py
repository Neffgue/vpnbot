import os
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.api.v1.endpoints import auth, users, subscriptions, servers, payments, referrals, admin, vpn_config
from backend.api.deps import get_admin_user
from backend.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def _invalidate_plans_cache() -> None:
    """Инвалидация кэша тарифов в Redis после изменений через веб-панель."""
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        from redis.asyncio import from_url as redis_from_url
        r = await redis_from_url(redis_url, decode_responses=True)
        try:
            await r.delete("bot:plans", "subscriptions:plans")
        finally:
            await r.aclose()
    except Exception as e:
        logger.warning(f"Plans cache invalidation skipped: {e}")

api_router = APIRouter(prefix="/api/v1")

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
api_router.include_router(servers.router, prefix="/servers", tags=["servers"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(referrals.router, prefix="/referrals", tags=["referrals"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(vpn_config.router, prefix="/vpn", tags=["vpn"])


# ── Compatibility aliases for compiled frontend JS ──────────────────────────
# The compiled admin-panel JS uses /api/v1/settings and /api/v1/stats/dashboard
# These aliases forward to the correct /admin/* endpoints.

@api_router.get("/settings", tags=["compat"])
async def settings_get_compat(
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Alias: GET /settings → GET /admin/system-settings"""
    from backend.api.v1.endpoints.admin import get_system_settings
    return await get_system_settings(current_user=current_user, db=db)


@api_router.put("/settings", tags=["compat"])
async def settings_put_compat(
    request: Request,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Alias: PUT /settings → PUT /admin/system-settings"""
    from backend.api.v1.endpoints.admin import update_system_settings
    from backend.schemas.admin import SystemSettingsUpdate
    body = await request.json()
    data = SystemSettingsUpdate(**body)
    return await update_system_settings(data=data, current_user=current_user, db=db)


@api_router.get("/stats/dashboard", tags=["compat"])
async def stats_dashboard_compat(
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Alias: GET /stats/dashboard → GET /admin/stats"""
    from backend.api.v1.endpoints.admin import get_stats
    return await get_stats(current_user=current_user, db=db)


@api_router.get("/auth/profile", tags=["compat"])
async def auth_profile_compat(
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current admin user profile (used by compiled frontend)."""
    # Resolve the real admin UUID and username for web panel admin
    _FIXED_ADMIN_UUID = "00000000-0000-0000-0000-000000000001"
    user_id = str(current_user.id)
    if user_id in ("bot-admin", _FIXED_ADMIN_UUID):
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        return {
            "id": _FIXED_ADMIN_UUID,
            "username": admin_username,
            "first_name": "Admin",
            "is_admin": True,
            "telegram_id": -1,
            "balance": 0.0,
            "created_at": None,
        }
    return {
        "id": user_id,
        "username": current_user.username or "admin",
        "first_name": current_user.first_name or "Admin",
        "is_admin": current_user.is_admin,
        "telegram_id": current_user.telegram_id,
        "balance": float(current_user.balance) if current_user.balance else 0.0,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }


@api_router.post("/auth/logout", tags=["compat"])
async def auth_logout_compat(
    current_user=Depends(get_admin_user),
):
    """Logout endpoint — client removes tokens from localStorage."""
    return {"message": "Logged out successfully"}


@api_router.get("/subscriptions/plans", tags=["compat"])
async def subscriptions_plans_compat(
    db: AsyncSession = Depends(get_db),
):
    """Public alias: GET /subscriptions/plans — returns full plan prices list.
    Включает image_url, name, device_limit для синхронизации с ботом.
    """
    from backend.models.config import PlanPrice
    from sqlalchemy import select
    try:
        result = await db.execute(
            select(PlanPrice)
            .where(PlanPrice.is_active == True)
            .order_by(PlanPrice.plan_name, PlanPrice.period_days)
        )
        plans = result.scalars().all()
        return [
            {
                "id": str(p.id),
                "plan_name": p.plan_name,
                "name": p.name or p.plan_name,
                "period_days": int(p.period_days),
                "price_rub": float(p.price_rub),
                "price": float(p.price_rub),
                "device_limit": int(p.device_limit or 1),
                "devices": int(p.device_limit or 1),
                "image_url": p.image_url or "",
                "description": p.description or "",
                "is_active": bool(p.is_active),
            }
            for p in plans
        ]
    except Exception as e:
        logger.error(f"subscriptions_plans_compat error: {e}", exc_info=True)
        return []


@api_router.get("/admin/plans", tags=["compat"])
async def get_admin_plans(
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Alias: GET /admin/plans — returns plan prices for PlanPrices.jsx (all fields)."""
    from backend.models.config import PlanPrice
    from sqlalchemy import select
    try:
        result = await db.execute(select(PlanPrice).order_by(PlanPrice.plan_name, PlanPrice.period_days))
        plans = result.scalars().all()
        return [
            {
                "id": str(p.id),
                "plan_name": p.plan_name,
                "name": p.name or p.plan_name,
                "period_days": int(p.period_days),
                "price_rub": float(p.price_rub),
                "price": float(p.price_rub),
                "device_limit": int(p.device_limit or 1),
                "devices": int(p.device_limit or 1),
                "image_url": p.image_url or "",
                "description": p.description or "",
                "is_active": bool(p.is_active) if p.is_active is not None else True,
            }
            for p in plans
        ]
    except Exception as e:
        logger.error(f"get_admin_plans error: {e}", exc_info=True)
        return []


@api_router.post("/admin/plans", tags=["compat"])
async def create_admin_plan(
    data: dict,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Alias: POST /admin/plans — create new plan price entry."""
    from backend.models.config import PlanPrice
    import uuid as _uuid
    try:
        plan = PlanPrice(
            id=str(_uuid.uuid4()),
            plan_name=data.get("plan_name", "Solo"),
            period_days=int(data.get("period_days", 30)),
            price_rub=float(data.get("price_rub", 299)),
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        return {"id": str(plan.id), "plan_name": plan.plan_name, "period_days": plan.period_days, "price_rub": float(plan.price_rub)}
    except Exception as e:
        await db.rollback()
        logger.error(f"create_admin_plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.put("/admin/plans/{plan_id}", tags=["compat"])
async def update_admin_plan(
    plan_id: str,
    data: dict,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Alias: PUT /admin/plans/{id} — update plan price. Accepts UUID or plan_name."""
    from backend.models.config import PlanPrice
    from sqlalchemy import select, or_
    try:
        result = await db.execute(
            select(PlanPrice).where(
                or_(PlanPrice.id == plan_id, PlanPrice.plan_name == plan_id)
            )
        )
        plan = result.scalars().first()
        if not plan:
            # Создаём новый если не найден
            import uuid as _uuid
            plan = PlanPrice(
                id=str(_uuid.uuid4()),
                plan_name=data.get("plan_name", plan_id),
                period_days=int(data.get("period_days", 30)),
                price_rub=float(data.get("price_rub", 299)),
            )
            db.add(plan)
            await db.commit()
            await db.refresh(plan)
            return {"id": str(plan.id), "plan_name": plan.plan_name, "period_days": plan.period_days, "price_rub": float(plan.price_rub)}
        if "plan_name" in data:
            plan.plan_name = str(data["plan_name"])
        if "name" in data:
            plan.name = str(data["name"])
        if "period_days" in data:
            plan.period_days = int(data["period_days"])
        if "price_rub" in data:
            plan.price_rub = float(data["price_rub"])
        if "price" in data:
            plan.price_rub = float(data["price"])
        if "device_limit" in data:
            plan.device_limit = int(data["device_limit"])
        if "devices" in data:
            plan.device_limit = int(data["devices"])
        if "image_url" in data:
            plan.image_url = str(data["image_url"]) if data["image_url"] else None
        if "description" in data:
            plan.description = str(data["description"]) if data["description"] else None
        if "is_active" in data:
            plan.is_active = bool(data["is_active"])
        await db.commit()
        await db.refresh(plan)
        await _invalidate_plans_cache()
        return {
            "id": str(plan.id),
            "plan_name": str(plan.plan_name),
            "name": plan.name or plan.plan_name,
            "period_days": int(plan.period_days),
            "price_rub": float(plan.price_rub),
            "price": float(plan.price_rub),
            "device_limit": int(plan.device_limit or 1),
            "devices": int(plan.device_limit or 1),
            "image_url": plan.image_url or "",
            "description": plan.description or "",
            "is_active": bool(plan.is_active),
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"update_admin_plan error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.patch("/admin/subscriptions/plans/{plan_id}", tags=["compat"])
async def patch_subscription_plan(
    plan_id: str,
    data: dict,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """PATCH /admin/subscriptions/plans/{plan_id} — partial update of plan price."""
    from backend.models.config import PlanPrice
    from sqlalchemy import select, or_
    try:
        result = await db.execute(
            select(PlanPrice).where(
                or_(PlanPrice.id == plan_id, PlanPrice.plan_name == plan_id)
            )
        )
        plan = result.scalars().first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        if "plan_name" in data:
            plan.plan_name = data["plan_name"]
        if "period_days" in data:
            plan.period_days = int(data["period_days"])
        if "price_rub" in data:
            plan.price_rub = float(data["price_rub"])
        if "price" in data:
            plan.price_rub = float(data["price"])
        await db.commit()
        return {"id": str(plan.id), "plan_name": plan.plan_name, "period_days": plan.period_days, "price_rub": float(plan.price_rub)}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"patch_subscription_plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.delete("/admin/plans/{plan_id}", tags=["compat"])
async def delete_admin_plan(
    plan_id: str,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Alias: DELETE /admin/plans/{id} — delete plan price entry."""
    from backend.models.config import PlanPrice
    from sqlalchemy import select, or_
    try:
        result = await db.execute(
            select(PlanPrice).where(
                or_(PlanPrice.id == plan_id, PlanPrice.plan_name == plan_id)
            )
        )
        plan = result.scalars().first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        await db.delete(plan)
        await db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"delete_admin_plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/users", tags=["compat"])
async def users_list_compat(
    request: Request,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Alias: GET /users?page=N&limit=N → GET /admin/users with pagination."""
    from backend.services.user_service import UserService
    params = dict(request.query_params)
    page = int(params.get("page", 1))
    limit = int(params.get("limit", 20))
    search = params.get("search", "").strip()
    skip = (page - 1) * limit

    service = UserService(db)
    if search:
        users = await service.search_users(search, skip=skip, limit=limit)
    else:
        users = await service.get_all_users(skip=skip, limit=limit)

    total = await service.repo.count()
    return {
        "users": [
            {
                "id": str(u.id),
                "telegram_id": u.telegram_id,
                "username": u.username,
                "first_name": u.first_name,
                "balance": float(u.balance) if u.balance else 0.0,
                "is_banned": u.is_banned,
                "is_admin": u.is_admin,
                "free_trial_used": u.free_trial_used,
                "referral_code": u.referral_code,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if limit else 1,
    }



# ── Public bot endpoints (no auth needed — used by the bot itself) ─────────
# These allow the bot process to fetch texts, settings, and buttons without admin auth.
# We query DB directly here instead of calling FastAPI endpoint functions (which have Depends).

@api_router.get("/admin/bot-texts", tags=["compat"])
async def get_admin_bot_texts(
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """GET /admin/bot-texts — returns all bot texts as key:value dict."""
    import json as _json
    from sqlalchemy import select as _select
    from backend.models.config import BotText as _BotText
    try:
        result = await db.execute(_select(_BotText))
        rows = result.scalars().all()
        return {r.key: r.value for r in rows}
    except Exception:
        return {}


@api_router.put("/admin/bot-texts/{key}", tags=["compat"])
async def update_admin_bot_text(
    key: str,
    data: dict,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """PUT /admin/bot-texts/{key} — create or update a bot text entry."""
    import uuid as _uuid
    from sqlalchemy import select as _select
    from backend.models.config import BotText as _BotText
    try:
        result = await db.execute(_select(_BotText).where(_BotText.key == key))
        existing = result.scalars().first()
        value = data.get("value", "")
        if existing:
            existing.value = value
        else:
            db.add(_BotText(id=str(_uuid.uuid4()), key=key, value=value, description=""))
        await db.commit()
        return {"key": key, "value": value}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/bot-texts/public", tags=["public"])
async def bot_texts_public(db: AsyncSession = Depends(get_db)):
    """Public: Get all bot texts (for the bot process, no auth)."""
    import json as _json
    from sqlalchemy import select as _select
    from backend.models.config import BotText as _BotText
    try:
        stmt = _select(_BotText).order_by(_BotText.key)
        result = await db.execute(stmt)
        rows = result.scalars().all()
        out = {}
        # Пропускаем служебные ключи, остальные — тексты бота
        SKIP_KEYS = {"bot_settings_json", "bot_buttons_json", "system_settings_json"}
        for row in rows:
            if row.key in SKIP_KEYS:
                continue
            # Значение — всегда строка (текст сообщения)
            out[row.key] = row.value
        return out
    except Exception as e:
        return {}


@api_router.get("/bot-settings/public", tags=["public"])
async def bot_settings_public(db: AsyncSession = Depends(get_db)):
    """Public: Get bot settings (welcome image, etc.) for the bot process."""
    import json as _json
    from sqlalchemy import select as _select
    from backend.models.config import BotText as _BotText
    BOT_SETTINGS_KEY = "bot_settings_json"
    try:
        stmt = _select(_BotText).where(_BotText.key == BOT_SETTINGS_KEY)
        result = await db.execute(stmt)
        row = result.scalars().first()
        if row:
            try:
                return _json.loads(row.value)
            except Exception:
                return {}
        return {}
    except Exception:
        return {}


@api_router.get("/bot-buttons/public", tags=["public"])
async def bot_buttons_public(db: AsyncSession = Depends(get_db)):
    """Public: Get bot menu buttons for the bot process.
    Buttons are stored as individual btn_* keys in BotText table.
    """
    import json as _json
    from sqlalchemy import select as _select
    from backend.models.config import BotText as _BotText
    try:
        stmt = _select(_BotText).where(_BotText.key.like("btn_%")).order_by(_BotText.key)
        result = await db.execute(stmt)
        rows = result.scalars().all()
        buttons = []
        for r in rows:
            try:
                btn = _json.loads(r.value)
                btn["id"] = r.key
                buttons.append(btn)
            except Exception:
                pass
        return {"buttons": buttons}
    except Exception:
        return {"buttons": []}


@api_router.get("/instructions/public", tags=["public"])
async def instructions_public(db: AsyncSession = Depends(get_db)):
    """Public: Get all instruction steps for all devices (for the bot process, no auth)."""
    import json as _json
    from sqlalchemy import select as _select
    from backend.models.config import BotText as _BotText
    INSTR_PREFIXES = (
        "instructions_android_steps",
        "instructions_ios_steps",
        "instructions_windows_steps",
        "instructions_macos_steps",
        "instructions_linux_steps",
        "instructions_android_tv_steps",
    )
    try:
        stmt = _select(_BotText).where(_BotText.key.in_(list(INSTR_PREFIXES)))
        result = await db.execute(stmt)
        rows = result.scalars().all()
        out = {}
        for row in rows:
            try:
                out[row.key] = _json.loads(row.value)
            except Exception:
                out[row.key] = row.value
        return out
    except Exception:
        return {}


@api_router.get("/payments", tags=["compat"])
async def payments_list_compat(
    request: Request,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Alias: GET /payments?page=N&limit=N&status=X → GET /admin/payments."""
    from backend.models.payment import Payment
    from sqlalchemy import select, func
    params = dict(request.query_params)
    page = int(params.get("page", 1))
    limit = int(params.get("limit", 20))
    status_filter = params.get("status", "all")
    skip = (page - 1) * limit

    stmt = select(Payment).order_by(Payment.created_at.desc()).offset(skip).limit(limit)
    if status_filter and status_filter != "all":
        stmt = select(Payment).where(Payment.status == status_filter).order_by(Payment.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    payments = result.scalars().all()

    count_stmt = select(func.count(Payment.id))
    if status_filter and status_filter != "all":
        count_stmt = select(func.count(Payment.id)).where(Payment.status == status_filter)
    total = (await db.execute(count_stmt)).scalar() or 0

    return {
        "payments": [
            {
                "id": str(p.id),
                "user_id": str(p.user_id),
                "amount": float(p.amount),
                "status": p.status,
                "payment_method": getattr(p, "payment_method", "unknown"),
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in payments
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if limit else 1,
    }
