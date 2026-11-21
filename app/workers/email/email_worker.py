import asyncio
import logging

from httpx import AsyncClient

import app.core.database.models
from app.core.config import settings
from app.core.database.session import AsyncSessionLocal
from app.core.database.unit_of_work import UnitOfWork
from app.modules.notification.dependencies.email_worker import (
    get_email_delivery_service,
)
from app.modules.notification.repositories.registry import (
    register_notification_repositories,
)
from app.workers.email.email_outbox_listener import EmailOutboxListener

logger = logging.getLogger(__name__)

LISTENER_RECONNECT_DELAY_SECONDS = 5


async def _process_pending_emails(
    http_client: AsyncClient,
) -> int:
    total_processed = 0

    while True:
        async with AsyncSessionLocal() as session:
            async with UnitOfWork(session) as uow:
                register_notification_repositories(uow)

                email_service = get_email_delivery_service(
                    uow=uow,
                    http_client=http_client,
                )

                results = await email_service.process_batch(
                    limit=settings.EMAIL_WORKER_BATCH_SIZE,
                )

        processed = len(results)
        total_processed += processed

        if processed:
            logger.info(
                "Email worker processed batch. Processed=%d",
                processed,
            )

        if processed == 0:
            break

    return total_processed


async def run_email_worker(stop_event: asyncio.Event) -> None:
    async with AsyncClient(
        timeout=settings.EMAIL_REQUEST_TIMEOUT,
    ) as http_client:
        logger.info("Email worker started.")

        try:
            while not stop_event.is_set():
                try:
                    async with EmailOutboxListener() as listener:
                        logger.info(
                            "Email worker notification listener connected."
                        )

                        while not stop_event.is_set():
                            try:
                                processed = await _process_pending_emails(
                                    http_client,
                                )

                                if processed:
                                    logger.info(
                                        "Email worker processing cycle "
                                        "completed. Processed=%d",
                                        processed,
                                    )

                            except asyncio.CancelledError:
                                raise

                            except Exception:
                                logger.exception(
                                    "Email worker processing cycle failed."
                                )

                            if stop_event.is_set():
                                break

                            notified = await listener.wait_for_notification(
                                timeout=(
                                    settings.EMAIL_WORKER_RECOVERY_INTERVAL_SECONDS
                                ),
                            )

                            if notified:
                                logger.debug(
                                    "Email worker awakened by PostgreSQL "
                                    "notification."
                                )
                            else:
                                logger.debug(
                                    "Email worker recovery check triggered."
                                )

                except asyncio.CancelledError:
                    raise

                except Exception:
                    logger.exception(
                        "Email worker listener connection failed."
                    )

                if stop_event.is_set():
                    break

                try:
                    await asyncio.wait_for(
                        stop_event.wait(),
                        timeout=LISTENER_RECONNECT_DELAY_SECONDS,
                    )
                except TimeoutError:
                    continue

        finally:
            logger.info("Email worker stopped.")