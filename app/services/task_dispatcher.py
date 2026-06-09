import os
from redis import Redis


def redis_broker_available() -> bool:
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    if not broker_url.startswith("redis://") and not broker_url.startswith("rediss://"):
        return True

    try:
        Redis.from_url(broker_url, socket_connect_timeout=0.5, socket_timeout=0.5).ping()
        return True
    except Exception:
        return False


def dispatch_task(task, *args, logger=None, description="task") -> bool:
    if os.getenv("DISABLE_CELERY_DISPATCH", "").lower() in {"1", "true", "yes"}:
        if logger:
            logger.warning(f"{description} saved but Celery dispatch is disabled.")
        return False

    if not redis_broker_available():
        if logger:
            logger.warning(f"{description} saved but Redis/Celery broker is not reachable.")
        return False

    try:
        task.delay(*args)
        return True
    except Exception as e:
        if logger:
            logger.warning(f"{description} saved but Celery dispatch failed: {e}")
        return False
