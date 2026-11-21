import asyncio
import logging

import psycopg
from psycopg import AsyncConnection

from app.core.config import settings

logger = logging.getLogger(__name__)

CHANNEL_NAME = "email_outbox_wakeup"


class EmailOutboxListener:
    def __init__(self) -> None:
        self._connection: AsyncConnection | None = None
        self._notification_task: asyncio.Task | None = None

    async def __aenter__(self) -> "EmailOutboxListener":
        self._connection = await AsyncConnection.connect(
            settings.DATABASE_URL,
            autocommit=True,
        )

        await self._connection.execute(
            f"LISTEN {CHANNEL_NAME}"
        )

        self._notification_task = asyncio.create_task(
            self._receive_notification()
        )

        logger.info(
            "Listening for PostgreSQL notifications: channel=%s",
            CHANNEL_NAME,
        )

        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        if self._notification_task is not None:
            if not self._notification_task.done():
                self._notification_task.cancel()

            await asyncio.gather(
                self._notification_task,
                return_exceptions=True,
            )

            self._notification_task = None

        if self._connection is not None:
            await self._connection.close()
            self._connection = None

        logger.info("PostgreSQL notification listener disconnected.")

    async def wait_for_notification(
        self,
        *,
        timeout: float,
    ) -> bool:
        if self._notification_task is None:
            raise RuntimeError("Notification listener is not connected.")

        try:
            notification = await asyncio.wait_for(
                asyncio.shield(self._notification_task),
                timeout=timeout,
            )
        except TimeoutError:
            return False

        logger.debug(
            "Email outbox notification received: payload=%s",
            notification.payload,
        )

        self._notification_task = asyncio.create_task(
            self._receive_notification()
        )

        return True

    async def _receive_notification(self):
        if self._connection is None:
            raise RuntimeError("Notification listener is not connected.")

        async for notification in self._connection.notifies():
            return notification

        raise ConnectionError(
            "PostgreSQL notification listener disconnected."
        )