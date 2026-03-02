import logging
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.subscription import Subscription
from backend.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class SubscriptionRepository(BaseRepository[Subscription]):
    """Repository for Subscription model."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Subscription)

    async def get_by_uuid(self, xui_client_uuid: str) -> Optional[Subscription]:
        """Get subscription by XUI client UUID."""
        try:
            stmt = (
                select(Subscription)
                .where(Subscription.xui_client_uuid == xui_client_uuid)
                .options(selectinload(Subscription.servers))
            )
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error getting subscription by UUID: {e}")
            return None

    async def get_user_subscriptions(self, user_id: str) -> List[Subscription]:
        """Get all subscriptions for a user."""
        try:
            stmt = (
                select(Subscription)
                .where(Subscription.user_id == user_id)
                .options(selectinload(Subscription.servers))
            )
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting user subscriptions: {e}")
            return []

    async def get_active_subscriptions(self) -> List[Subscription]:
        """Get all active subscriptions."""
        try:
            stmt = select(Subscription).where(Subscription.is_active == True)
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting active subscriptions: {e}")
            return []

    async def get_expiring_subscriptions(self, hours: int = 24) -> List[Subscription]:
        """Get subscriptions expiring within specified hours."""
        try:
            from datetime import timedelta
            now = datetime.now(timezone.utc)
            expiry_time = now + timedelta(hours=hours)

            stmt = select(Subscription).where(
                and_(
                    Subscription.expires_at <= expiry_time,
                    Subscription.expires_at > now,
                    Subscription.is_active == True,
                )
            )
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting expiring subscriptions: {e}")
            return []

    async def count_active_subscriptions(self) -> int:
        """Count active subscriptions."""
        try:
            stmt = select(func.count(Subscription.id)).where(Subscription.is_active == True)
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting active subscriptions: {e}")
            return 0
