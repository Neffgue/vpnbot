"""Subscription management tasks."""
import logging
import httpx
from celery import shared_task
from datetime import datetime, timedelta
import os
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import json

logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+asyncpg://user:password@localhost/vpn_db'
)
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class SubscriptionManager:
    """Helper class for subscription management."""
    
    @staticmethod
    async def get_expired_subscriptions() -> list:
        """Get all expired but still active subscriptions."""
        async with async_session() as session:
            from app.models import Subscription
            
            now = datetime.utcnow()
            stmt = select(Subscription).where(
                and_(
                    Subscription.is_active == True,
                    Subscription.expires_at <= now
                )
            )
            result = await session.execute(stmt)
            return result.scalars().all()
    
    @staticmethod
    async def deactivate_subscription(subscription_id: int) -> bool:
        """
        Deactivate expired subscription.
        Remove inbound from 3x-ui panel.
        """
        async with async_session() as session:
            from app.models import Subscription
            
            subscription = await session.get(Subscription, subscription_id)
            if not subscription:
                return False
            
            try:
                # Remove from 3x-ui
                if subscription.server and subscription.inbound_id:
                    success = await SubscriptionManager.remove_inbound_from_server(
                        subscription.server, subscription.inbound_id
                    )
                    if not success:
                        logger.warning(
                            f'Failed to remove inbound {subscription.inbound_id} '
                            f'from server {subscription.server.name}'
                        )
                
                # Mark as inactive
                subscription.is_active = False
                subscription.deactivated_at = datetime.utcnow()
                await session.commit()
                return True
            
            except Exception as e:
                logger.error(f'Error deactivating subscription {subscription_id}: {e}')
                return False
    
    @staticmethod
    async def remove_inbound_from_server(server, inbound_id: int) -> bool:
        """Remove inbound from 3x-ui panel."""
        if not server.panel_url:
            return False
        
        try:
            url = f'{server.panel_url}/xui/api/inbounds/{inbound_id}'
            
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                response = await client.delete(
                    url,
                    auth=(server.panel_username, server.panel_password)
                )
                return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f'Failed to remove inbound: {e}')
            return False
    
    @staticmethod
    async def get_all_subscriptions_for_sync() -> list:
        """Get all active subscriptions for traffic sync."""
        async with async_session() as session:
            from app.models import Subscription
            
            stmt = select(Subscription).where(
                Subscription.is_active == True
            )
            result = await session.execute(stmt)
            return result.scalars().all()
    
    @staticmethod
    async def get_inbound_stats(server, inbound_id: int) -> dict:
        """Fetch traffic stats for inbound from 3x-ui panel."""
        if not server.panel_url:
            return {}
        
        try:
            url = f'{server.panel_url}/xui/api/inbounds/get/{inbound_id}'
            
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                response = await client.get(
                    url,
                    auth=(server.panel_username, server.panel_password)
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        inbound = data.get('obj', {})
                        # Extract traffic stats
                        return {
                            'up': inbound.get('up', 0),
                            'down': inbound.get('down', 0),
                        }
        except Exception as e:
            logger.error(f'Failed to fetch inbound stats: {e}')
        
        return {}
    
    @staticmethod
    async def update_subscription_traffic(subscription_id: int, up_bytes: int, down_bytes: int):
        """Update subscription traffic usage."""
        async with async_session() as session:
            from app.models import Subscription
            
            subscription = await session.get(Subscription, subscription_id)
            if subscription:
                total_bytes = up_bytes + down_bytes
                traffic_gb = total_bytes / (1024 ** 3)
                subscription.traffic_used_gb = traffic_gb
                subscription.last_traffic_sync = datetime.utcnow()
                await session.commit()


@shared_task(bind=True, name='worker.tasks.subscription_manager.sync_traffic_stats')
def sync_traffic_stats(self):
    """
    Sync traffic stats from 3x-ui panels to database.
    Update subscription.traffic_used_gb field.
    """
    import asyncio
    
    async def run_sync():
        subscriptions = await SubscriptionManager.get_all_subscriptions_for_sync()
        results = {
            'total': len(subscriptions),
            'synced': 0,
            'failed': 0
        }
        
        for subscription in subscriptions:
            try:
                if not subscription.server or not subscription.inbound_id:
                    continue
                
                stats = await SubscriptionManager.get_inbound_stats(
                    subscription.server, subscription.inbound_id
                )
                
                if stats:
                    await SubscriptionManager.update_subscription_traffic(
                        subscription.id, stats['up'], stats['down']
                    )
                    results['synced'] += 1
                else:
                    results['failed'] += 1
            
            except Exception as e:
                logger.error(f'Error syncing traffic for subscription {subscription.id}: {e}')
                results['failed'] += 1
        
        logger.info(f'sync_traffic_stats: Synced {results["synced"]}/{results["total"]} subscriptions')
        return results
    
    try:
        return asyncio.run(run_sync())
    except Exception as e:
        logger.error(f'Unexpected error in sync_traffic_stats: {e}')
        self.retry(exc=e, countdown=300, max_retries=3)


@shared_task(bind=True, name='worker.tasks.subscription_manager.cleanup_expired_subscriptions')
def cleanup_expired_subscriptions(self):
    """
    Daily task to deactivate expired subscriptions.
    Remove them from 3x-ui panels.
    """
    import asyncio
    
    async def run_cleanup():
        expired_subs = await SubscriptionManager.get_expired_subscriptions()
        results = {
            'total': len(expired_subs),
            'deactivated': 0,
            'failed': 0
        }
        
        for subscription in expired_subs:
            try:
                success = await SubscriptionManager.deactivate_subscription(subscription.id)
                if success:
                    results['deactivated'] += 1
                else:
                    results['failed'] += 1
            except Exception as e:
                logger.error(f'Error deactivating subscription {subscription.id}: {e}')
                results['failed'] += 1
        
        logger.info(
            f'cleanup_expired_subscriptions: Deactivated {results["deactivated"]} '
            f'subscriptions, {results["failed"]} failed'
        )
        return results
    
    try:
        return asyncio.run(run_cleanup())
    except Exception as e:
        logger.error(f'Unexpected error in cleanup_expired_subscriptions: {e}')
        self.retry(exc=e, countdown=3600, max_retries=3)
