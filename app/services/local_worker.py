import asyncio
from app.services.task_dispatcher import redis_broker_available
from app.utils.logger import logger


async def run_local_email_worker():
    logger.warning("Redis/Celery is not reachable. Starting local email/follow-up worker fallback.")

    while not redis_broker_available():
        try:
            from app.tasks import check_follow_ups, poll_inbox, process_email_queue

            await asyncio.to_thread(poll_inbox)
            await asyncio.to_thread(check_follow_ups)
            await asyncio.to_thread(process_email_queue)
        except Exception as e:
            logger.error(f"Local email worker fallback error: {e}", exc_info=True)

        await asyncio.sleep(10)

    logger.info("Redis/Celery broker is reachable. Local email/follow-up worker fallback stopped.")
