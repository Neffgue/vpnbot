import logging
from typing import Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User
from backend.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    """Repository for User model."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, User)

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        try:
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error getting user by telegram_id: {e}")
            return None

    async def get_by_referral_code(self, referral_code: str) -> Optional[User]:
        """Get user by referral code."""
        try:
            stmt = select(User).where(User.referral_code == referral_code)
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error getting user by referral_code: {e}")
            return None

    async def get_banned_users(self) -> list:
        """Get all banned users."""
        try:
            stmt = select(User).where(User.is_banned == True)
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting banned users: {e}")
            return []

    async def get_admin_users(self) -> list:
        """Get all admin users."""
        try:
            stmt = select(User).where(User.is_admin == True)
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting admin users: {e}")
            return []

    async def search_users(self, query: str, skip: int = 0, limit: int = 100) -> list:
        """Search users by username, first_name, or telegram_id."""
        try:
            # Try to convert query to int for telegram_id search
            telegram_id = None
            try:
                telegram_id = int(query)
            except ValueError:
                pass

            conditions = []
            if telegram_id:
                conditions.append(User.telegram_id == telegram_id)
            else:
                conditions.append(User.username.ilike(f"%{query}%"))
                conditions.append(User.first_name.ilike(f"%{query}%"))

            from sqlalchemy import or_
            stmt = select(User).where(or_(*conditions)).offset(skip).limit(limit)
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return []

    async def count_active_users(self) -> int:
        """Count users (total)."""
        return await self.count()

    async def count_banned_users(self) -> int:
        """Count banned users."""
        try:
            stmt = select(func.count(User.id)).where(User.is_banned == True)
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting banned users: {e}")
            return 0
