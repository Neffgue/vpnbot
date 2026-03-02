import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.services.subscription_service import SubscriptionService
from backend.services.user_service import UserService
from backend.utils.happ_link import HappLinkGenerator

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{uuid}")
async def get_vpn_config(
    uuid: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get VPN configuration for Happ app (public endpoint, no auth).
    Returns subscription info and server list with VLESS links.
    """
    sub_service = SubscriptionService(db)
    subscription = await sub_service.get_subscription_by_uuid(uuid)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    # Check if subscription is active and not expired
    if not subscription.is_active or subscription.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subscription expired or inactive",
        )

    user_service = UserService(db)
    user = await user_service.get_user(subscription.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Calculate remaining traffic (placeholder)
    traffic_used = 0  # Would need to get from XUI
    traffic_remaining = subscription.traffic_gb - traffic_used

    # Generate VLESS links for each server
    vless_links = []
    for server in subscription.servers:
        vless_link = HappLinkGenerator.generate_vless_link(
            uuid=uuid,
            server_name=server.name,
            host=server.host,
            port=server.port,
        )
        vless_links.append({
            "name": f"{server.country_emoji} {server.name}",
            "link": vless_link,
            "country": server.country_name,
        })

    # Generate subscription link
    subscription_link = HappLinkGenerator.generate_subscription_link(
        [link["link"] for link in vless_links]
    )

    return {
        "telegram_id": user.telegram_id,
        "traffic_remaining_gb": traffic_remaining,
        "expires_at": subscription.expires_at.isoformat(),
        "device_limit": subscription.device_limit,
        "plan_name": subscription.plan_name,
        "servers": vless_links,
        "subscription_link": subscription_link,
    }
