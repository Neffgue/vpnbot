import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas.server import ServerResponse
from backend.services.server_service import ServerService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list[ServerResponse])
async def list_servers(
    db: AsyncSession = Depends(get_db),
):
    """
    Get all active VPN servers (public endpoint).
    """
    service = ServerService(db)
    servers = await service.get_active_servers(limit=1000)
    return servers


@router.get("/{server_id}", response_model=ServerResponse)
async def get_server(
    server_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get server by ID (public endpoint).
    """
    service = ServerService(db)
    server = await service.get_server(server_id)

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    return server


@router.get("/country/{country_name}", response_model=list[ServerResponse])
async def get_servers_by_country(
    country_name: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all servers in a country (public endpoint).
    """
    service = ServerService(db)
    servers = await service.get_servers_by_country(country_name)

    if not servers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No servers found for this country",
        )

    return servers
