"""Celery application factory and configuration."""
import os
from celery import Celery
from kombu import Exchange, Queue

# Initialize Celery app
app = Celery(
    'vpn_sales_worker',
    broker=os.getenv('REDIS_BROKER_URL') or os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_BACKEND_URL') or os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
)

# Celery configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # 1 hour
)

# Task routing configuration
app.conf.task_routes = {
    'worker.tasks.notifications.*': {'queue': 'notifications'},
    'worker.tasks.health_check.*': {'queue': 'health_check'},
    'worker.tasks.subscription_manager.*': {'queue': 'subscriptions'},
}

# Queue configuration
default_exchange = Exchange('celery', type='direct')
app.conf.task_queues = (
    Queue('celery', exchange=default_exchange, routing_key='celery'),
    Queue('notifications', exchange=default_exchange, routing_key='notifications'),
    Queue('health_check', exchange=default_exchange, routing_key='health_check'),
    Queue('subscriptions', exchange=default_exchange, routing_key='subscriptions'),
)

# Import tasks to register them
from worker.tasks import notifications, health_check, subscription_manager  # noqa: F401, E402

__all__ = ['app']
