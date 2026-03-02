import logging
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.server import Server
from backend.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ServerRepository(BaseRepository[Server]):
    """Repository for Server model."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Server)

    async def get_by_name(self, name: str) -> Optional[Server]:
        """Get server by name."""
        try:
            stmt = select(Server).where(Server.name == name)
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error getting server by name: {e}")
            return None

    async def get_active_servers(self, skip: int = 0, limit: int = 100) -> List[Server]:
        """Get all active servers ordered by order_index."""
        try:
            stmt = (
                select(Server)
                .where(Server.is_active == True)
                .order_by(Server.order_index)
                .offset(skip)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting active servers: {e}")
            return []

    async def get_all_ordered(self) -> List[Server]:
        """Get all servers ordered by order_index."""
        try:
            stmt = select(Server).order_by(Server.order_index)
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting all ordered servers: {e}")
            return []

    async def get_by_country(self, country_name: str) -> List[Server]:
        """Get servers by country."""
        try:
            stmt = select(Server).where(
                and_(Server.country_name == country_name, Server.is_active == True)
            )
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting servers by country: {e}")
            return []
