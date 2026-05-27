import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery = Celery(
    "solar_automation",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.tasks"]
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Celery Beat schedule
celery.conf.beat_schedule = {
    "check-follow-ups-every-60s": {
        "task": "app.tasks.check_follow_ups",
        "schedule": 60.0,
    },
    "poll-inbox-every-60s": {
        "task": "app.tasks.poll_inbox",
        "schedule": 60.0,
    },
    "process-email-queue-every-10s": {
        "task": "app.tasks.process_email_queue",
        "schedule": 10.0,
    },
}
