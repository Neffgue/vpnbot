import logging
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from backend.models.referral import Referral
from backend.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)


class ReferralService:
    """Service for referral operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def create_referral(self, referrer_id: str, referred_id: str, bonus_days: int = 7) -> Referral:
        """Create a referral record with anti-abuse checks."""
        # Anti-abuse: cannot refer yourself
        if referrer_id == referred_id:
            logger.warning(f"Self-referral attempt blocked: {referrer_id}")
            return None

        # Anti-abuse: user can only be referred once
        existing = await self.get_pending_referral(referred_id)
        if existing:
            logger.warning(f"Duplicate referral attempt blocked: {referred_id} already has pending referral")
            return existing

        # Anti-abuse: check if referred_id is already in referrals table (paid or not)
        stmt = select(Referral).where(Referral.referred_id == referred_id)
        result = await self.db.execute(stmt)
        if result.scalars().first():
            logger.warning(f"Duplicate referral blocked: {referred_id} already referred")
            return None

        referral = Referral(
            id=str(uuid4()),
            referrer_id=referrer_id,
            referred_id=referred_id,
            bonus_days=bonus_days,
        )
        self.db.add(referral)
        await self.db.commit()
        await self.db.refresh(referral)
        logger.info(f"Created referral: {referrer_id} -> {referred_id}")
        return referral

    async def mark_referral_paid(self, referral_id: str) -> Referral:
        """Mark referral bonus as paid."""
        try:
            referral = await self.db.get(Referral, referral_id)
            if referral:
                referral.paid_at = datetime.now(timezone.utc)
                await self.db.commit()
                await self.db.refresh(referral)
                logger.info(f"Marked referral {referral_id} as paid")
                return referral
        except Exception as e:
            logger.error(f"Error marking referral as paid: {e}")
            await self.db.rollback()
        return None

    async def get_referral(self, referral_id: str) -> Referral:
        """Get referral by ID."""
        try:
            return await self.db.get(Referral, referral_id)
        except Exception as e:
            logger.error(f"Error getting referral: {e}")
            return None

    async def get_pending_referral(self, referred_id: str) -> Referral:
        """Get pending (unpaid) referral for a user."""
        try:
            stmt = select(Referral).where(
                and_(Referral.referred_id == referred_id, Referral.paid_at == None)
            )
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error getting pending referral: {e}")
            return None

    async def get_referrer_stats(self, referrer_id: str) -> dict:
        """Get referral statistics for a referrer."""
        try:
            stmt = select(func.count(Referral.id)).where(Referral.referrer_id == referrer_id)
            result = await self.db.execute(stmt)
            total_referrals = result.scalar() or 0

            stmt = select(func.count(Referral.id)).where(
                and_(Referral.referrer_id == referrer_id, Referral.paid_at != None)
            )
            result = await self.db.execute(stmt)
            paid_referrals = result.scalar() or 0

            total_bonus_days = 0
            stmt = select(func.sum(Referral.bonus_days)).where(
                and_(Referral.referrer_id == referrer_id, Referral.paid_at != None)
            )
            result = await self.db.execute(stmt)
            total_bonus_days = result.scalar() or 0

            return {
                "total_referrals": total_referrals,
                "paid_referrals": paid_referrals,
                "pending_referrals": total_referrals - paid_referrals,
                "total_bonus_days": total_bonus_days,
            }
        except Exception as e:
            logger.error(f"Error getting referrer stats: {e}")
            return {
                "total_referrals": 0,
                "paid_referrals": 0,
                "pending_referrals": 0,
                "total_bonus_days": 0,
            }
