import logging
import os
from typing import Optional
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.api.deps import get_current_user
from backend.schemas.user import UserResponse, UserDetailResponse, UserUpdate
from backend.services.user_service import UserService
from backend.services.subscription_service import SubscriptionService
from backend.services.payment_service import PaymentService
from backend.models.config import PlanPrice
from backend.models.referral import Referral

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/me", response_model=UserDetailResponse)
async def get_me(
    current_user=Depends(get_current_user),
):
    """Get current user profile."""
    return current_user


@router.put("/me", response_model=UserDetailResponse)
async def update_me(
    user_update: UserUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile."""
    service = UserService(db)
    user = await service.update_user(
        current_user.id,
        username=user_update.username,
        first_name=user_update.first_name,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        )
    logger.info(f"User {current_user.id} updated")
    return user


# ── Статичные маршруты ВСЕГДА должны идти ДО динамических /{user_id} ──────

@router.post("/register")
async def register_user(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Register or get existing user (called by bot middleware).
    Accepts: telegram_id, username, first_name, referral_code (optional).
    Returns user info.
    """
    telegram_id = data.get("telegram_id")
    if not telegram_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="telegram_id required")

    service = UserService(db)

    # Return existing user or create new one
    existing = await service.get_user_by_telegram_id(telegram_id)
    if existing:
        return {
            "id": existing.id,
            "telegram_id": existing.telegram_id,
            "username": existing.username,
            "first_name": existing.first_name,
            "referral_code": existing.referral_code,
            "balance": float(existing.balance),
            "is_banned": existing.is_banned,
            "is_admin": existing.is_admin,
            "free_trial_used": existing.free_trial_used,
        }

    # Handle referral code if provided
    referred_by = None
    referral_code = data.get("referral_code")
    if referral_code:
        # Strip prefix if present (e.g. "REF_XXXXX" -> "XXXXX")
        clean_code = referral_code.replace("REF_", "") if referral_code.startswith("REF_") else referral_code
        referrer = await service.repo.get_by_referral_code(clean_code)
        if referrer and referrer.telegram_id != telegram_id:
            referred_by = referrer.id

    user = await service.create_user(
        telegram_id=telegram_id,
        username=data.get("username", ""),
        first_name=data.get("first_name", ""),
        referred_by=referred_by,
    )
    logger.info(f"New user registered via bot: {telegram_id}")

    # Create referral record if referred
    if referred_by:
        try:
            from backend.services.referral_service import ReferralService
            ref_service = ReferralService(db)
            await ref_service.create_referral(
                referrer_id=referred_by,
                referred_id=user.id,
                bonus_days=7,
            )
            logger.info(f"Referral created: referrer={referred_by} -> new user={user.id}")
        except Exception as ref_err:
            logger.error(f"Failed to create referral record: {ref_err}")
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "referral_code": user.referral_code,
        "balance": float(user.balance),
        "is_banned": user.is_banned,
        "is_admin": user.is_admin,
        "free_trial_used": user.free_trial_used,
    }


@router.get("/by-referral/{referral_code}", response_model=UserResponse)
async def get_user_by_referral_code(
    referral_code: str,
    db: AsyncSession = Depends(get_db),
):
    """Get user by referral code (public endpoint)."""
    service = UserService(db)
    user = await service.repo.get_by_referral_code(referral_code)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить пользователя по Telegram ID или внутреннему UUID.
    Сначала пробует telegram_id (целое число), затем UUID.
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def patch_user(
    user_id: str,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update user by Telegram ID or internal UUID (for bot use).
    Can update username, first_name, email.
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Update fields if provided
    update_data = {}
    if user_update.username is not None:
        update_data['username'] = user_update.username
    if user_update.first_name is not None:
        update_data['first_name'] = user_update.first_name
    if user_update.email is not None:
        update_data['email'] = user_update.email

    if update_data:
        updated_user = await service.update_user(user.id, **update_data)
    else:
        updated_user = user

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        )
    logger.info(f"User {user_id} updated")
    return updated_user


@router.get("/{user_id}/ban-status")
async def get_ban_status(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Check if user is banned. user_id can be telegram_id or internal UUID."""
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
        return {"is_banned": False, "reason": ""}

    return {"is_banned": user.is_banned, "reason": ""}


@router.get("/{user_id}/subscription")
async def get_user_subscription(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get active subscription for a user (by telegram_id or UUID)."""
    user_service = UserService(db)
    user = None
    try:
        tg_id = int(user_id)
        user = await user_service.get_user_by_telegram_id(tg_id)
    except (ValueError, TypeError):
        pass
    if not user:
        user = await user_service.get_user(user_id)
    if not user:
        return {}

    sub_service = SubscriptionService(db)
    sub = await sub_service.get_active_user_subscription(user.id)
    if not sub:
        return {}

    return {
        "id": sub.id,
        "plan_name": sub.plan_name,
        "device_limit": sub.device_limit,
        "traffic_gb": sub.traffic_gb,
        "expires_at": sub.expires_at.isoformat(),
        "expire_date": sub.expires_at.isoformat(),
        "is_active": sub.is_active,
        "xui_client_uuid": sub.xui_client_uuid,
        "devices_count": 0,
    }


@router.get("/{user_id}/free-trial-status")
async def get_free_trial_status(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Check if user has already used free trial."""
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
        return {"already_used": False}
    return {"already_used": user.free_trial_used}


@router.post("/{user_id}/free-trial")
async def activate_free_trial(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Activate 24h free trial for user."""
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.free_trial_used:
        return {"success": False, "error": "Бесплатный доступ уже был использован ранее."}

    # Create 24h subscription (mock mode — no real VPN server needed)
    sub_service = SubscriptionService(db)
    sub = await sub_service.create_subscription(
        user_id=user.id,
        plan_name="Trial",
        period_days=1,
        device_limit=1,
        traffic_gb=10,
    )
    await service.mark_free_trial_used(user.id)

    # Generate mock subscription link
    subscription_link = f"happ://import/trial-{sub.xui_client_uuid}"

    logger.info(f"Free trial activated for user {user_id}")
    return {
        "success": True,
        "subscription_link": subscription_link,
        "expires_at": sub.expires_at.isoformat(),
    }


@router.get("/{user_id}/referral")
async def get_referral_info(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get referral info for user."""
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Count referrals
    stmt = select(Referral).where(Referral.referrer_id == user.id)
    result = await db.execute(stmt)
    referrals = result.scalars().all()
    bonus_days = sum(r.bonus_days for r in referrals if r.paid_at)

    bot_username = (
        os.getenv("BOT_USERNAME")
        or os.getenv("TELEGRAM_BOT_USERNAME")
        or ""
    ).lstrip("@")

    if bot_username:
        referral_link = f"https://t.me/{bot_username}?start=REF_{user.referral_code}"
    else:
        # Fallback: используем telegram_id как реферальный код (бот обработает ref{tg_id})
        referral_link = f"https://t.me/bot?start=REF_{user.referral_code}"

    return {
        "referral_code": user.referral_code,
        "referral_link": referral_link,
        "referrals_count": len(referrals),
        "bonus_days": bonus_days,
        "level": "АМБАССАДОР" if len(referrals) >= 10 else ("ПРОДВИНУТЫЙ" if len(referrals) >= 5 else "НОВИЧОК 🐣"),
    }


@router.get("/{user_id}/devices")
async def get_user_devices(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get list of devices for user (mock — uses subscription servers)."""
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
        return {"devices": []}

    sub_service = SubscriptionService(db)
    sub = await sub_service.get_active_user_subscription(user.id)
    if not sub:
        return {"devices": []}

    # In mock mode, represent servers as "devices"
    devices = []
    for server in sub.servers:
        devices.append({
            "id": server.id,
            "server": server.name,
            "country": server.country_name,
            "added_date": sub.created_at.isoformat(),
        })
    return {"devices": devices}


@router.post("/{user_id}/devices")
async def add_device(
    user_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Add device for user (mock — returns subscription link)."""
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
        return {"success": False, "error": "Пользователь не найден"}

    sub_service = SubscriptionService(db)
    sub = await sub_service.get_active_user_subscription(user.id)
    if not sub:
        return {"success": False, "error": "Нет активной подписки"}

    device_name = data.get("device_name", "Device")
    device_id = str(uuid4())
    subscription_link = f"happ://import/{sub.xui_client_uuid}"

    return {
        "success": True,
        "device_id": device_id,
        "device_name": device_name,
        "subscription_link": subscription_link,
    }


@router.delete("/{user_id}/devices/{device_id}")
async def delete_device(
    user_id: str,
    device_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete device (mock)."""
    return {"success": True, "device_id": device_id}


@router.post("/{user_id}/reissue-key")
async def reissue_vpn_key(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Перевыпустить VPN-ключ: создаёт новый xui_client_uuid для активной подписки."""
    from uuid import uuid4
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    sub_service = SubscriptionService(db)
    sub = await sub_service.get_active_user_subscription(user.id)
    if not sub:
        return {"success": False, "error": "Нет активной подписки"}

    new_uuid = str(uuid4())
    await sub_service.repo.update(sub.id, {"xui_client_uuid": new_uuid})

    new_link = f"happ://import/{new_uuid}"
    logger.info(f"VPN key reissued for user {user_id}, new uuid={new_uuid}")
    return {"success": True, "subscription_link": new_link}


@router.get("/{user_id}/payments")
async def get_user_payments(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Получить историю платежей пользователя."""
    from sqlalchemy import select
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
        return {"payments": []}

    stmt = select(Payment).where(Payment.user_id == user.id).order_by(Payment.created_at.desc()).limit(20)
    result = await db.execute(stmt)
    payments = result.scalars().all()

    return {
        "payments": [
            {
                "id": p.id,
                "plan_name": p.plan_name,
                "amount": float(p.amount),
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in payments
        ]
    }


@router.post("/{user_id}/create-payment")
async def create_payment_for_user(
    user_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Create payment link for user."""
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    plan_id = str(data.get("plan_id", ""))
    period_days = int(data.get("period_days", 30))

    payment_service = PaymentService(db)
    plan_details = await payment_service.get_plan_details(plan_id)
    if not plan_details:
        # Fallback defaults
        plan_details = {"device_limit": 1, "traffic_gb": 100}

    price = await payment_service.get_plan_price(plan_id, period_days)
    if price is None:
        price = 299.0

    provider_payment_id = str(uuid4())
    payment = await payment_service.create_payment(
        user_id=user.id,
        plan_name=plan_id,
        period_days=period_days,
        device_limit=plan_details["device_limit"],
        amount=price,
        provider="telegram_stars",
        provider_payment_id=provider_payment_id,
    )

    invoice_payload = payment.id
    yookassa_link = ""  # No real YooKassa in mock mode

    return {
        "success": True,
        "payment_id": payment.id,
        "invoice_payload": invoice_payload,
        "yookassa_link": yookassa_link,
        "amount": float(price),
    }


@router.post("/{user_id}/confirm-payment")
async def confirm_payment_for_user(
    user_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Confirm payment and activate subscription."""
    payment_id = data.get("payment_id", "")
    payment_service = PaymentService(db)
    payment = await payment_service.get_payment(payment_id)
    if not payment:
        return {"success": False, "error": "Платёж не найден"}

    await payment_service.mark_completed(payment_id)

    sub_service = SubscriptionService(db)
    plan_details = await payment_service.get_plan_details(payment.plan_name)
    if not plan_details:
        plan_details = {"device_limit": 1, "traffic_gb": 100}

    sub = await sub_service.create_subscription(
        user_id=payment.user_id,
        plan_name=payment.plan_name,
        period_days=payment.period_days,
        device_limit=plan_details["device_limit"],
        traffic_gb=plan_details["traffic_gb"],
    )
    subscription_link = f"happ://import/{sub.xui_client_uuid}"
    return {"success": True, "subscription_link": subscription_link}
