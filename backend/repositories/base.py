import logging
from typing import Generic, List, Optional, Type, TypeVar
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository with common database operations."""

    def __init__(self, db: AsyncSession, model: Type[T]):
        self.db = db
        self.model = model

    async def get_by_id(self, id: str) -> Optional[T]:
        """Get entity by ID."""
        try:
            stmt = select(self.model).where(self.model.id == id)
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by id: {e}")
            return None

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all entities with pagination."""
        try:
            stmt = select(self.model).offset(skip).limit(limit)
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting all {self.model.__name__}: {e}")
            return []

    async def create(self, obj: T) -> T:
        """Create a new entity."""
        try:
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise

    async def update(self, id: str, data: dict) -> Optional[T]:
        """Update an entity."""
        try:
            obj = await self.get_by_id(id)
            if not obj:
                return None

            for key, value in data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating {self.model.__name__}: {e}")
            raise

    async def delete(self, id: str) -> bool:
        """Delete an entity."""
        try:
            obj = await self.get_by_id(id)
            if not obj:
                return False

            await self.db.delete(obj)
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting {self.model.__name__}: {e}")
            raise

    async def count(self) -> int:
        """Count total entities."""
        try:
            stmt = select(func.count(self.model.id))
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            return 0
