import logging
from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.payment import Payment
from backend.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class PaymentRepository(BaseRepository[Payment]):
    """Repository for Payment model."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Payment)

    async def get_by_provider_id(self, provider_payment_id: str) -> Optional[Payment]:
        """Get payment by provider payment ID."""
        try:
            stmt = select(Payment).where(Payment.provider_payment_id == provider_payment_id)
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error getting payment by provider_id: {e}")
            return None

    async def get_user_payments(self, user_id: str, skip: int = 0, limit: int = 100) -> List[Payment]:
        """Get payments for a user."""
        try:
            stmt = (
                select(Payment)
                .where(Payment.user_id == user_id)
                .order_by(Payment.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting user payments: {e}")
            return []

    async def get_pending_payments(self) -> List[Payment]:
        """Get all pending payments."""
        try:
            stmt = select(Payment).where(Payment.status == "pending")
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting pending payments: {e}")
            return []

    async def get_completed_payments(self, skip: int = 0, limit: int = 100) -> List[Payment]:
        """Get completed payments."""
        try:
            stmt = (
                select(Payment)
                .where(Payment.status == "completed")
                .order_by(Payment.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting completed payments: {e}")
            return []

    async def get_total_revenue(self) -> Decimal:
        """Get total revenue from completed payments."""
        try:
            stmt = select(func.sum(Payment.amount)).where(Payment.status == "completed")
            result = await self.db.execute(stmt)
            total = result.scalar()
            return total or Decimal("0.00")
        except Exception as e:
            logger.error(f"Error getting total revenue: {e}")
            return Decimal("0.00")

    async def count_pending_payments(self) -> int:
        """Count pending payments."""
        try:
            stmt = select(func.count(Payment.id)).where(Payment.status == "pending")
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting pending payments: {e}")
            return 0

    async def count_completed_payments(self) -> int:
        """Count completed payments."""
        try:
            stmt = select(func.count(Payment.id)).where(Payment.status == "completed")
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting completed payments: {e}")
            return 0
