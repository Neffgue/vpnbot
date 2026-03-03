"""Celery Beat schedule configuration."""
from celery.schedules import crontab
from datetime import timedelta

# Beat schedule for periodic tasks
beat_schedule = {
    # Check for expiring subscriptions every 1 minute
    'check-expiring-subscriptions': {
        'task': 'worker.tasks.notifications.check_expiring_subscriptions',
        'schedule': timedelta(minutes=1),
        'options': {'queue': 'notifications'}
    },
    
    # Health check servers every 30 seconds
    'health-check-servers': {
        'task': 'worker.tasks.health_check.health_check_servers',
        'schedule': timedelta(seconds=30),
        'options': {'queue': 'health_check'}
    },
    
    # Sync traffic stats every 5 minutes
    'sync-traffic-stats': {
        'task': 'worker.tasks.subscription_manager.sync_traffic_stats',
        'schedule': timedelta(minutes=5),
        'options': {'queue': 'subscriptions'}
    },
    
    # Cleanup expired subscriptions + auto-renewal every hour
    'cleanup-expired-subscriptions': {
        'task': 'worker.tasks.subscription_manager.cleanup_expired_subscriptions',
        'schedule': timedelta(hours=1),
        'options': {'queue': 'subscriptions'}
    },
}

__all__ = ['beat_schedule']
