import logging
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.server import Server
from backend.repositories.server_repo import ServerRepository

logger = logging.getLogger(__name__)


class ServerService:
    """Service for VPN server operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ServerRepository(db)

    async def create_server(
        self,
        name: str,
        country_emoji: str,
        country_name: str,
        host: str,
        port: int,
        panel_url: str,
        panel_username: str,
        panel_password: str,
        inbound_id: int,
        bypass_ru_whitelist: bool = False,
        order_index: int = 0,
    ) -> Server:
        """Create a new server."""
        server = Server(
            id=str(uuid4()),
            name=name,
            country_emoji=country_emoji,
            country_name=country_name,
            host=host,
            port=port,
            panel_url=panel_url,
            panel_username=panel_username,
            panel_password=panel_password,
            inbound_id=inbound_id,
            bypass_ru_whitelist=bypass_ru_whitelist,
            order_index=order_index,
        )
        logger.info(f"Creating server: {name}")
        return await self.repo.create(server)

    async def get_server(self, server_id: str) -> Server:
        """Get server by ID."""
        return await self.repo.get_by_id(server_id)

    async def get_server_by_name(self, name: str) -> Server:
        """Get server by name."""
        return await self.repo.get_by_name(name)

    async def update_server(self, server_id: str, **kwargs) -> Server:
        """Update server."""
        logger.info(f"Updating server {server_id}")
        return await self.repo.update(server_id, kwargs)

    async def delete_server(self, server_id: str) -> bool:
        """Delete server."""
        logger.info(f"Deleting server {server_id}")
        return await self.repo.delete(server_id)

    async def get_active_servers(self, skip: int = 0, limit: int = 100) -> list:
        """Get all active servers."""
        return await self.repo.get_active_servers(skip, limit)

    async def get_all_servers(self) -> list:
        """Get all servers ordered by order_index."""
        return await self.repo.get_all_ordered()

    async def get_servers_by_country(self, country_name: str) -> list:
        """Get servers by country."""
        return await self.repo.get_by_country(country_name)

    async def disable_server(self, server_id: str) -> Server:
        """Disable a server."""
        logger.info(f"Disabling server {server_id}")
        return await self.repo.update(server_id, {"is_active": False})

    async def enable_server(self, server_id: str) -> Server:
        """Enable a server."""
        logger.info(f"Enabling server {server_id}")
        return await self.repo.update(server_id, {"is_active": True})
