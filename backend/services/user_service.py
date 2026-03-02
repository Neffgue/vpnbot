import logging
from decimal import Decimal
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User
from backend.repositories.user_repo import UserRepository
from backend.utils.security import generate_referral_code

logger = logging.getLogger(__name__)


class UserService:
    """Service for user operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    async def create_user(
        self, telegram_id: int, username: str = None, first_name: str = None, referred_by: str = None
    ) -> User:
        """Create a new user."""
        # Check if user already exists
        existing = await self.repo.get_by_telegram_id(telegram_id)
        if existing:
            logger.info(f"User {telegram_id} already exists")
            return existing

        # Generate unique referral code
        referral_code = generate_referral_code(str(uuid4()))
        
        # Ensure uniqueness
        while await self.repo.get_by_referral_code(referral_code):
            referral_code = generate_referral_code(str(uuid4()))

        user = User(
            id=str(uuid4()),
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            referral_code=referral_code,
            referred_by=referred_by,
        )

        return await self.repo.create(user)

    async def get_user(self, user_id: str) -> User:
        """Get user by ID."""
        return await self.repo.get_by_id(user_id)

    async def get_user_by_telegram_id(self, telegram_id: int) -> User:
        """Get user by Telegram ID."""
        return await self.repo.get_by_telegram_id(telegram_id)

    async def update_user(self, user_id: str, **kwargs) -> User:
        """Update user."""
        return await self.repo.update(user_id, kwargs)

    async def ban_user(self, user_id: str) -> User:
        """Ban a user."""
        logger.info(f"Banning user {user_id}")
        return await self.repo.update(user_id, {"is_banned": True})

    async def unban_user(self, user_id: str) -> User:
        """Unban a user."""
        logger.info(f"Unbanning user {user_id}")
        return await self.repo.update(user_id, {"is_banned": False})

    async def add_balance(self, user_id: str, amount: Decimal) -> User:
        """Add balance to user account."""
        user = await self.repo.get_by_id(user_id)
        if not user:
            return None

        new_balance = user.balance + amount
        logger.info(f"Adding {amount} to user {user_id} balance. New balance: {new_balance}")
        return await self.repo.update(user_id, {"balance": new_balance})

    async def deduct_balance(self, user_id: str, amount: Decimal) -> User:
        """Deduct balance from user account."""
        user = await self.repo.get_by_id(user_id)
        if not user:
            return None

        if user.balance < amount:
            logger.warning(f"Insufficient balance for user {user_id}")
            return None

        new_balance = user.balance - amount
        logger.info(f"Deducting {amount} from user {user_id} balance. New balance: {new_balance}")
        return await self.repo.update(user_id, {"balance": new_balance})

    async def mark_free_trial_used(self, user_id: str) -> User:
        """Mark free trial as used for user."""
        logger.info(f"Marking free trial as used for user {user_id}")
        return await self.repo.update(user_id, {"free_trial_used": True})

    async def search_users(self, query: str, skip: int = 0, limit: int = 100) -> list:
        """Search users."""
        return await self.repo.search_users(query, skip, limit)

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> list:
        """Get all users with pagination."""
        return await self.repo.get_all(skip, limit)
