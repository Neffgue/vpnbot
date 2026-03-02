"""Health check tasks for VPN servers."""
import logging
import httpx
from celery import shared_task
from datetime import datetime, timedelta
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+asyncpg://user:password@localhost/vpn_db'
)
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class ServerHealthChecker:
    """Helper class for server health checks."""
    
    @staticmethod
    async def get_all_servers() -> list:
        """Get all servers from database."""
        async with async_session() as session:
            from app.models import Server
            
            stmt = select(Server)
            result = await session.execute(stmt)
            return result.scalars().all()
    
    @staticmethod
    async def check_server_health(server) -> bool:
        """
        Ping 3x-ui panel to check if server is alive.
        Returns True if healthy, False otherwise.
        """
        if not server.panel_url:
            return False
        
        try:
            # Try to access the 3x-ui status endpoint
            url = f'{server.panel_url}/xui/api/inbounds'
            
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                response = await client.get(
                    url,
                    auth=(server.panel_username, server.panel_password)
                )
                return response.status_code in [200, 401]  # 401 means auth failed but server is up
        except Exception as e:
            logger.warning(f'Health check failed for {server.name}: {e}')
            return False
    
    @staticmethod
    async def update_server_status(server_id: int, is_active: bool):
        """Update server active status in database."""
        async with async_session() as session:
            from app.models import Server
            
            server = await session.get(Server, server_id)
            if server:
                server.is_active = is_active
                server.last_health_check = datetime.utcnow()
                await session.commit()
    
    @staticmethod
    async def send_admin_alert(message: str) -> bool:
        """Send alert to admin via Telegram."""
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        admin_id = os.getenv('TELEGRAM_ADMIN_ID')
        
        if not token or not admin_id:
            logger.error('Telegram credentials not configured')
            return False
        
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        payload = {
            'chat_id': int(admin_id),
            'text': message,
            'parse_mode': 'HTML'
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f'Failed to send admin alert: {e}')
            return False


@shared_task(bind=True, name='worker.tasks.health_check.health_check_servers')
def health_check_servers(self):
    """
    Check health of all 3x-ui servers.
    Update server.is_active field.
    Send alert if server goes down.
    """
    import asyncio
    
    async def run_health_check():
        servers = await ServerHealthChecker.get_all_servers()
        results = {
            'total': len(servers),
            'healthy': 0,
            'unhealthy': 0,
            'alerts': []
        }
        
        for server in servers:
            try:
                is_healthy = await ServerHealthChecker.check_server_health(server)
                was_active = server.is_active
                
                await ServerHealthChecker.update_server_status(server.id, is_healthy)
                
                if is_healthy:
                    results['healthy'] += 1
                    
                    # Server came back online
                    if not was_active:
                        message = f'✅ Server <b>{server.name}</b> ({server.country}) is now <b>ONLINE</b>'
                        await ServerHealthChecker.send_admin_alert(message)
                        results['alerts'].append(f'{server.name}: UP')
                else:
                    results['unhealthy'] += 1
                    
                    # Server went down
                    if was_active:
                        message = f'❌ Server <b>{server.name}</b> ({server.country}) is now <b>OFFLINE</b>'
                        await ServerHealthChecker.send_admin_alert(message)
                        results['alerts'].append(f'{server.name}: DOWN')
            
            except Exception as e:
                logger.error(f'Error checking server {server.name}: {e}')
                results['unhealthy'] += 1
        
        logger.info(
            f'health_check_servers: {results["healthy"]} healthy, '
            f'{results["unhealthy"]} unhealthy. Alerts: {results["alerts"]}'
        )
        return results
    
    try:
        return asyncio.run(run_health_check())
    except Exception as e:
        logger.error(f'Unexpected error in health_check_servers: {e}')
        self.retry(exc=e, countdown=60, max_retries=3)
