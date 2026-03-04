import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.subscription import Subscription
from backend.repositories.subscription_repo import SubscriptionRepository
from backend.repositories.server_repo import ServerRepository
from backend.repositories.user_repo import UserRepository
from backend.config import settings
from backend.services.xui_service_mock import get_xui_service

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for subscription operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SubscriptionRepository(db)
        self.server_repo = ServerRepository(db)
        self.user_repo = UserRepository(db)

    async def create_subscription(
        self,
        user_id: str,
        plan_name: str,
        period_days: int,
        device_limit: int,
        traffic_gb: int,
    ) -> Subscription:
        """Create a new subscription and register client in XUI/Marzban."""
        xui_client_uuid = str(uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(days=period_days)
        expiry_ms = int(expires_at.timestamp() * 1000)

        sub = Subscription(
            id=str(uuid4()),
            user_id=user_id,
            plan_name=plan_name,
            period_days=period_days,
            device_limit=device_limit,
            traffic_gb=traffic_gb,
            expires_at=expires_at,
            xui_client_uuid=xui_client_uuid,
        )

        # Add all active servers to subscription
        servers = await self.server_repo.get_active_servers(limit=1000)
        sub.servers = servers

        # Register client in XUI/Marzban on each active server
        for server in servers:
            try:
                xui = get_xui_service(
                    panel_url=server.panel_url,
                    panel_username=server.panel_username,
                    panel_password=server.panel_password,
                    inbound_id=server.inbound_id,
                )
                ok = await xui.add_client(
                    client_uuid=xui_client_uuid,
                    traffic_limit_gb=traffic_gb,
                    expiry_timestamp_ms=expiry_ms,
                    device_limit=device_limit,
                )
                if ok:
                    logger.info(f"XUI client created on server {server.name} for user {user_id}")
                else:
                    logger.warning(f"XUI add_client returned False for server {server.name}")
            except Exception as e:
                logger.error(f"Failed to create XUI client on server {server.name}: {e}", exc_info=True)

        return await self.repo.create(sub)

    async def get_subscription(self, subscription_id: str) -> Subscription:
        """Get subscription by ID."""
        return await self.repo.get_by_id(subscription_id)

    async def get_subscription_by_uuid(self, uuid: str) -> Subscription:
        """Get subscription by XUI client UUID."""
        return await self.repo.get_by_uuid(uuid)

    async def get_user_subscriptions(self, user_id: str) -> list:
        """Get all subscriptions for a user."""
        return await self.repo.get_user_subscriptions(user_id)

    async def get_active_user_subscription(self, user_id: str) -> Subscription:
        """Get the active subscription for a user."""
        subs = await self.repo.get_user_subscriptions(user_id)
        now_utc = datetime.now(timezone.utc)
        for sub in subs:
            if not sub.is_active:
                continue
            expires = sub.expires_at
            # SQLite returns naive datetimes — make them timezone-aware
            if expires is not None and expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires is not None and expires > now_utc:
                return sub
        return None

    async def extend_subscription(self, subscription_id: str, days: int) -> Subscription:
        """Extend subscription validity and update XUI/Marzban client."""
        sub = await self.repo.get_by_id(subscription_id)
        if not sub:
            return None

        # If already expired, set new expiry from now
        expires = sub.expires_at
        if expires is not None and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires is not None and expires < datetime.now(timezone.utc):
            new_expires_at = datetime.now(timezone.utc) + timedelta(days=days)
        else:
            new_expires_at = sub.expires_at + timedelta(days=days)

        logger.info(f"Extending subscription {subscription_id} by {days} days to {new_expires_at}")
        updated = await self.repo.update(subscription_id, {"expires_at": new_expires_at})

        # Update expiry in XUI/Marzban on each server
        expiry_ms = int(new_expires_at.timestamp() * 1000)
        for server in sub.servers:
            try:
                xui = get_xui_service(
                    panel_url=server.panel_url,
                    panel_username=server.panel_username,
                    panel_password=server.panel_password,
                    inbound_id=server.inbound_id,
                )
                await xui.update_client(
                    client_uuid=sub.xui_client_uuid,
                    expiry_timestamp_ms=expiry_ms,
                )
                logger.info(f"XUI client extended on server {server.name}")
            except Exception as e:
                logger.error(f"Failed to extend XUI client on server {server.name}: {e}", exc_info=True)

        return updated

    async def deactivate_subscription(self, subscription_id: str) -> Subscription:
        """Deactivate subscription."""
        logger.info(f"Deactivating subscription {subscription_id}")
        return await self.repo.update(subscription_id, {"is_active": False})

    async def activate_subscription(self, subscription_id: str) -> Subscription:
        """Activate subscription."""
        logger.info(f"Activating subscription {subscription_id}")
        return await self.repo.update(subscription_id, {"is_active": True})

    async def get_expiring_subscriptions(self, hours: int = 24) -> list:
        """Get subscriptions expiring within specified hours."""
        return await self.repo.get_expiring_subscriptions(hours)

    async def count_active_subscriptions(self) -> int:
        """Count active subscriptions."""
        return await self.repo.count_active_subscriptions()
