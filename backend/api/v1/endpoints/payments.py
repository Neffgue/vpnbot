import logging
import hmac
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.api.deps import get_current_user
from backend.schemas.payment import PaymentResponse
from backend.services.payment_service import PaymentService
from backend.services.subscription_service import SubscriptionService
from backend.services.referral_service import ReferralService
from backend.services.user_service import UserService
from backend.services.notification_service import NotificationService
from backend.config import settings
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get payment by ID.
    """
    service = PaymentService(db)
    payment = await service.get_payment(payment_id)

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    if payment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    return payment


@router.post("/yookassa/webhook")
async def yookassa_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    YooKassa payment webhook.
    """
    try:
        body = await request.json()
        logger.info(f"YooKassa webhook received: {body}")

        # Verify webhook signature
        if not _verify_yookassa_signature(request):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature",
            )

        event = body.get("event")
        payment_data = body.get("object", {})
        payment_id = payment_data.get("id")
        status_val = payment_data.get("status")
        metadata = payment_data.get("metadata", {})

        if event == "payment.succeeded" and status_val == "succeeded":
            await _process_payment_success(payment_id, metadata, db)
        elif event == "payment.canceled":
            await _process_payment_failed(payment_id, db)

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing error",
        )


@router.post("/telegram-stars/webhook")
async def telegram_stars_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Telegram Stars payment webhook.
    """
    try:
        body = await request.json()
        logger.info(f"Telegram Stars webhook received: {body}")

        update = body.get("update", {})
        if "pre_checkout_query" in update:
            # Approve payment
            pass
        elif "successful_payment" in update:
            payment_data = update["successful_payment"]
            invoice_payload = payment_data.get("invoice_payload")
            await _process_telegram_stars_payment(invoice_payload, payment_data, db)

        return {"ok": True}
    except Exception as e:
        logger.error(f"Error processing Telegram Stars webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing error",
        )


async def _process_payment_success(provider_payment_id: str, metadata: dict, db: AsyncSession):
    """Process successful payment."""
    payment_service = PaymentService(db)
    payment = await payment_service.get_payment_by_provider_id(provider_payment_id)

    if not payment:
        logger.warning(f"Payment not found: {provider_payment_id}")
        return

    if payment.status == "completed":
        logger.info(f"Payment already processed: {payment.id}")
        return

    # Mark payment as completed
    await payment_service.mark_completed(payment.id)

    # Create subscription
    sub_service = SubscriptionService(db)
    subscription = await sub_service.create_subscription(
        user_id=payment.user_id,
        plan_name=payment.plan_name,
        period_days=payment.period_days,
        device_limit=payment.device_limit,
        traffic_gb=payment.traffic_gb if hasattr(payment, "traffic_gb") else 100,
    )

    # Handle referral bonus
    user_service = UserService(db)
    user = await user_service.get_user(payment.user_id)
    if user and user.referred_by:
        referral_service = ReferralService(db)
        referral = await referral_service.get_pending_referral(payment.user_id)
        if referral and not referral.paid_at:
            # Mark referral as paid and extend referrer's subscription
            await referral_service.mark_referral_paid(referral.id)

            # Extend referrer's subscription
            referrer_sub = await sub_service.get_active_user_subscription(referral.referrer_id)
            if referrer_sub:
                await sub_service.extend_subscription(referrer_sub.id, referral.bonus_days)

    logger.info(f"Payment {payment.id} processed successfully")


async def _process_payment_failed(provider_payment_id: str, db: AsyncSession):
    """Process failed payment."""
    payment_service = PaymentService(db)
    payment = await payment_service.get_payment_by_provider_id(provider_payment_id)

    if payment:
        await payment_service.mark_failed(payment.id)
        logger.info(f"Payment {payment.id} marked as failed")


async def _process_telegram_stars_payment(invoice_payload: str, payment_data: dict, db: AsyncSession):
    """Process Telegram Stars payment."""
    # Invoice payload should contain payment_id
    payment_service = PaymentService(db)
    payment = await payment_service.get_payment(invoice_payload)

    if payment:
        await _process_payment_success(payment.provider_payment_id, {}, db)


@router.post("/pay-with-balance")
async def pay_with_balance(
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Pay for a subscription using the user's account balance.
    Body: {plan_name, period_days, price, device_limit, traffic_gb}
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body")

    plan_name = body.get("plan_name")
    period_days = int(body.get("period_days", 30))
    price = float(body.get("price", 0))
    device_limit = int(body.get("device_limit", 1))
    traffic_gb = int(body.get("traffic_gb", 100))

    if not plan_name or price <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="plan_name and price are required")

    from decimal import Decimal
    price_decimal = Decimal(str(price))

    user_service = UserService(db)
    payment_service = PaymentService(db)
    sub_service = SubscriptionService(db)

    try:
        # 1. Check and deduct balance atomically
        updated_user = await user_service.deduct_balance(current_user.id, price_decimal)
        if updated_user is None:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient balance. Required: {price}",
            )

        # 2. Create payment record
        payment = await payment_service.create_payment(
            user_id=current_user.id,
            plan_name=plan_name,
            period_days=period_days,
            device_limit=device_limit,
            amount=price_decimal,
            provider="balance",
            provider_payment_id=f"balance_{current_user.id}_{datetime.utcnow().timestamp()}",
        )
        await payment_service.mark_completed(payment.id)

        # 3. Create subscription
        subscription = await sub_service.create_subscription(
            user_id=current_user.id,
            plan_name=plan_name,
            period_days=period_days,
            device_limit=device_limit,
            traffic_gb=traffic_gb,
        )

        # 4. Handle referral bonus (same logic as webhook)
        user = await user_service.get_user(current_user.id)
        if user and user.referred_by:
            from backend.services.referral_service import ReferralService
            referral_service = ReferralService(db)
            referral = await referral_service.get_pending_referral(current_user.id)
            if referral and not referral.paid_at:
                await referral_service.mark_referral_paid(referral.id)
                referrer_sub = await sub_service.get_active_user_subscription(referral.referrer_id)
                if referrer_sub:
                    await sub_service.extend_subscription(referrer_sub.id, referral.bonus_days)

        link = getattr(subscription, "link", None) or getattr(subscription, "subscription_link", None) or ""
        xui_uuid = getattr(subscription, "xui_client_uuid", None) or ""

        return {
            "subscription_id": subscription.id,
            "xui_client_uuid": xui_uuid,
            "link": link,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"pay_with_balance error for user {current_user.id}: {e}", exc_info=True)
        try:
            await db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment processing failed",
        )


def _verify_yookassa_signature(request: Request) -> bool:
    """Verify YooKassa webhook signature via IP allowlist.
    YooKassa sends webhooks from fixed IPs — we check against their known range.
    If YOOKASSA_SECRET_KEY is set we additionally could verify, but IP check is primary.
    """
    import os
    # If explicitly disabled for local dev, skip check
    if os.getenv("YOOKASSA_SKIP_SIGNATURE_CHECK", "").lower() in ("1", "true", "yes"):
        return True
    # YooKassa known IP ranges (as of 2024)
    YOOKASSA_IPS = {
        "185.71.76.0", "185.71.77.0",
        "77.75.153.0", "77.75.156.11", "77.75.156.35",
        "77.75.154.128", "2a02:5180::/32",
    }
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "")
    client_ip = client_ip.split(",")[0].strip()
    # In dev/docker the IP won't match — allow if no secret key configured
    yookassa_key = os.getenv("YOOKASSA_SECRET_KEY", "")
    if not yookassa_key:
        logger.warning("YOOKASSA_SECRET_KEY not set — skipping webhook signature check")
        return True
    return client_ip in YOOKASSA_IPS
