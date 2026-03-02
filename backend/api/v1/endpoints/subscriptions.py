import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.api.deps import get_current_user
from backend.schemas.subscription import SubscriptionResponse, SubscriptionCreate
from backend.schemas.payment import PaymentCreate
from backend.services.subscription_service import SubscriptionService
from backend.services.payment_service import PaymentService
from backend.models.config import PlanPrice

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/plans")
async def get_subscription_plans(db: AsyncSession = Depends(get_db)):
    """
    Get all available subscription plans with prices.
    Returns plans for the bot's payment flow.
    """
    try:
        stmt = select(PlanPrice).order_by(PlanPrice.plan_name, PlanPrice.period_days)
        result = await db.execute(stmt)
        prices = result.scalars().all()

        # Group by plan_name
        plan_map: dict = {}
        for p in prices:
            if p.plan_name not in plan_map:
                plan_map[p.plan_name] = {
                    "id": p.plan_name,
                    "name": p.plan_name,
                    "price": float(p.price_rub),
                    "periods": [],
                }
            plan_map[p.plan_name]["periods"].append({
                "days": p.period_days,
                "price": float(p.price_rub),
            })

        plans = list(plan_map.values())

        # If no plans configured yet, return defaults (mock mode)
        if not plans:
            plans = [
                {
                    "id": "Solo",
                    "name": "Solo",
                    "description": "1 устройство, 100 ГБ трафика",
                    "price": 299.0,
                    "periods": [
                        {"days": 7, "price": 99.0},
                        {"days": 30, "price": 299.0},
                        {"days": 90, "price": 799.0},
                        {"days": 180, "price": 1499.0},
                        {"days": 365, "price": 2699.0},
                    ],
                },
                {
                    "id": "Family",
                    "name": "Family",
                    "description": "5 устройств, 500 ГБ трафика",
                    "price": 499.0,
                    "periods": [
                        {"days": 7, "price": 149.0},
                        {"days": 30, "price": 499.0},
                        {"days": 90, "price": 1299.0},
                        {"days": 180, "price": 2499.0},
                        {"days": 365, "price": 4499.0},
                    ],
                },
            ]

        return {"plans": plans}
    except Exception as e:
        logger.error(f"Error getting subscription plans: {e}")
        # Return defaults on error
        return {
            "plans": [
                {"id": "Solo", "name": "Solo", "price": 299.0, "periods": []},
                {"id": "Family", "name": "Family", "price": 499.0, "periods": []},
            ]
        }


@router.get("", response_model=list[SubscriptionResponse])
async def get_my_subscriptions(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all subscriptions for current user.
    """
    service = SubscriptionService(db)
    subscriptions = await service.get_user_subscriptions(current_user.id)
    return subscriptions


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get subscription by ID.
    """
    service = SubscriptionService(db)
    subscription = await service.get_subscription(subscription_id)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    if subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this subscription",
        )

    return subscription


@router.post("/purchase", response_model=dict)
async def purchase_subscription(
    payment_data: PaymentCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate subscription purchase.
    Returns payment details and payment link/ID to complete payment.
    """
    payment_service = PaymentService(db)

    # Get plan price
    price = await payment_service.get_plan_price(payment_data.plan_name, payment_data.period_days)
    if price is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    # Get plan details
    plan_details = await payment_service.get_plan_details(payment_data.plan_name)
    if not plan_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    # Create payment record
    from uuid import uuid4
    provider_payment_id = str(uuid4())

    payment = await payment_service.create_payment(
        user_id=current_user.id,
        plan_name=payment_data.plan_name,
        period_days=payment_data.period_days,
        device_limit=plan_details["device_limit"],
        amount=price,
        provider="telegram_stars",  # Default provider
        provider_payment_id=provider_payment_id,
    )

    logger.info(f"Payment created: {payment.id} for user {current_user.id}")

    return {
        "payment_id": payment.id,
        "amount": float(price),
        "currency": "RUB",
        "provider": "telegram_stars",
    }


@router.post("/{subscription_id}/extend")
async def extend_subscription(
    subscription_id: str,
    days: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Extend subscription (admin/system endpoint).
    """
    service = SubscriptionService(db)
    subscription = await service.get_subscription(subscription_id)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    if subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    updated = await service.extend_subscription(subscription_id, days)
    logger.info(f"Subscription {subscription_id} extended by {days} days")
    return updated
