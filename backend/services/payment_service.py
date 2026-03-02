import logging
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.payment import Payment
from backend.models.config import PlanPrice
from backend.repositories.payment_repo import PaymentRepository
from backend.repositories.user_repo import UserRepository
from sqlalchemy import select

logger = logging.getLogger(__name__)


class PaymentService:
    """Service for payment operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PaymentRepository(db)
        self.user_repo = UserRepository(db)

    async def create_payment(
        self,
        user_id: str,
        plan_name: str,
        period_days: int,
        device_limit: int,
        amount: Decimal,
        provider: str,
        provider_payment_id: str,
    ) -> Payment:
        """Create a new payment record."""
        payment = Payment(
            id=str(uuid4()),
            user_id=user_id,
            plan_name=plan_name,
            period_days=period_days,
            device_limit=device_limit,
            amount=amount,
            currency="RUB",
            provider=provider,
            provider_payment_id=provider_payment_id,
            status="pending",
        )
        logger.info(f"Creating payment {payment.id} for user {user_id}")
        return await self.repo.create(payment)

    async def get_payment(self, payment_id: str) -> Payment:
        """Get payment by ID."""
        return await self.repo.get_by_id(payment_id)

    async def get_payment_by_provider_id(self, provider_payment_id: str) -> Payment:
        """Get payment by provider payment ID."""
        return await self.repo.get_by_provider_id(provider_payment_id)

    async def mark_completed(self, payment_id: str) -> Payment:
        """Mark payment as completed."""
        logger.info(f"Marking payment {payment_id} as completed")
        return await self.repo.update(payment_id, {"status": "completed"})

    async def mark_failed(self, payment_id: str) -> Payment:
        """Mark payment as failed."""
        logger.info(f"Marking payment {payment_id} as failed")
        return await self.repo.update(payment_id, {"status": "failed"})

    async def get_user_payments(self, user_id: str, skip: int = 0, limit: int = 100) -> list:
        """Get payments for a user."""
        return await self.repo.get_user_payments(user_id, skip, limit)

    async def get_pending_payments(self) -> list:
        """Get all pending payments."""
        return await self.repo.get_pending_payments()

    async def get_total_revenue(self) -> Decimal:
        """Get total revenue."""
        return await self.repo.get_total_revenue()

    async def count_completed_payments(self) -> int:
        """Count completed payments."""
        return await self.repo.count_completed_payments()

    async def count_pending_payments(self) -> int:
        """Count pending payments."""
        return await self.repo.count_pending_payments()

    async def get_plan_price(self, plan_name: str, period_days: int) -> Decimal:
        """Get price for a plan and period."""
        try:
            stmt = select(PlanPrice).where(
                (PlanPrice.plan_name == plan_name) & (PlanPrice.period_days == period_days)
            )
            result = await self.db.execute(stmt)
            plan_price = result.scalars().first()
            return plan_price.price_rub if plan_price else None
        except Exception as e:
            logger.error(f"Error getting plan price: {e}")
            return None

    async def get_plan_details(self, plan_name: str) -> dict:
        """Get plan details (device limit, etc)."""
        plan_details = {
            "Solo": {"device_limit": 1, "traffic_gb": 100},
            "Family": {"device_limit": 5, "traffic_gb": 500},
        }
        return plan_details.get(plan_name)
