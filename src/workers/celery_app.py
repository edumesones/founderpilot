"""Celery application configuration."""
from celery import Celery
from celery.schedules import crontab
from src.core.config import settings

# Create Celery app
celery_app = Celery(
    "founderpilot",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "src.workers.tasks.slack_tasks",
        "src.workers.tasks.meeting_tasks",
    ],
)

# Configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Result backend
    result_expires=3600,  # 1 hour

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,

    # Beat schedule for periodic tasks
    beat_schedule={
        # Sync all calendars every 15 minutes
        "sync-calendars-every-15-min": {
            "task": "src.workers.tasks.meeting_tasks.sync_all_calendars",
            "schedule": crontab(minute="*/15"),
            "options": {"queue": "meeting_pilot"},
        },
        # Check for meetings needing briefs every 5 minutes
        "check-briefs-every-5-min": {
            "task": "src.workers.tasks.meeting_tasks.check_meetings_needing_briefs",
            "schedule": crontab(minute="*/5"),
            "options": {"queue": "meeting_pilot"},
        },
    },
)
