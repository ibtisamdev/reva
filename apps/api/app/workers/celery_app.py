"""Celery application configuration."""

from celery import Celery

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "reva",
    broker=str(settings.redis_url),
    backend=str(settings.redis_url),
    include=[
        "app.workers.tasks.example",
        "app.workers.tasks.embedding",
        # Future task modules:
        # "app.workers.tasks.sync",
        # "app.workers.tasks.recovery",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    # Task routing (for future scaling)
    task_routes={
        "app.workers.tasks.sync.*": {"queue": "sync"},
        "app.workers.tasks.recovery.*": {"queue": "recovery"},
    },
    # Beat schedule (for periodic tasks)
    beat_schedule={
        # Example periodic task
        # "check-abandoned-carts": {
        #     "task": "app.workers.tasks.recovery.check_abandoned_carts",
        #     "schedule": 300.0,  # Every 5 minutes
        # },
    },
)


# Task base class with common error handling
class BaseTask(celery_app.Task):  # type: ignore[misc, name-defined]
    """Base task class with error handling."""

    abstract = True
    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 600  # Max 10 minutes between retries
    retry_jitter = True
    max_retries = 3
