"""
Celery application configuration for background tasks
"""
from celery import Celery
from app.config import settings

# Create Celery app
celery_app = Celery(
    "orchestrator",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.sync_tasks"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "sync-gmail-every-15-minutes": {
        "task": "app.tasks.sync_tasks.sync_gmail",
        "schedule": settings.sync_interval_minutes * 60,
    },
    "sync-gcal-every-15-minutes": {
        "task": "app.tasks.sync_tasks.sync_gcal",
        "schedule": settings.sync_interval_minutes * 60,
    },
    "sync-gdrive-every-15-minutes": {
        "task": "app.tasks.sync_tasks.sync_gdrive",
        "schedule": settings.sync_interval_minutes * 60,
    },
}
