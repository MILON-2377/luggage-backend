import uuid
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.repositories.base import BaseRepository
from app.modules.notification.contracts.repositories.email_outbox import (
    AbstractEmailOutboxRepository,
)
from app.modules.notification.enums import EmailOutboxStatus
from app.modules.notification.models.email_outbox import EmailOutbox

MAX_ERROR_LENGTH = 1000
LEASE_EXHAUSTED_ERROR = (
    "Maximum delivery attempts exhausted after worker lease expired."
)


class EmailOutboxRepository(
    BaseRepository[EmailOutbox],
    AbstractEmailOutboxRepository,
):
    async def claim_batch(
        self,
        *,
        now: datetime,
        lease_expires_before: datetime,
        limit: int,
    ) -> list[EmailOutbox]:
        if limit <= 0:
            return []

        # Permanently fail rows whose worker died on the last allowed attempt.
        await self.session.execute(
            update(EmailOutbox)
            .where(
                EmailOutbox.status == EmailOutboxStatus.PROCESSING,
                EmailOutbox.locked_at <= lease_expires_before,
                EmailOutbox.attempt_count >= EmailOutbox.max_attempts,
            )
            .values(
                status=EmailOutboxStatus.FAILED,
                failed_at=now,
                locked_at=None,
                payload_encrypted=None,
                last_error=LEASE_EXHAUSTED_ERROR,
            )
            .execution_options(synchronize_session="fetch")
        )

        # Step 1: lock the rows to claim. Done as a separate statement because
        # "UPDATE ... WHERE id IN (SELECT ... LIMIT n FOR UPDATE SKIP LOCKED)"
        # can be re-evaluated by the planner and touch more than n rows.
        id_statement = (
            select(EmailOutbox.id)
            .where(
                EmailOutbox.attempt_count < EmailOutbox.max_attempts,
                (
                    (
                        (EmailOutbox.status == EmailOutboxStatus.PENDING)
                        & (EmailOutbox.next_attempt_at <= now)
                    )
                    | (
                        (EmailOutbox.status == EmailOutboxStatus.PROCESSING)
                        & (EmailOutbox.locked_at <= lease_expires_before)
                    )
                ),
            )
            .order_by(
                EmailOutbox.next_attempt_at,
                EmailOutbox.created_at,
                EmailOutbox.id,
            )
            .limit(limit)
            .with_for_update(skip_locked=True)
        )

        claimed_ids = list((await self.session.execute(id_statement)).scalars().all())

        if not claimed_ids:
            return []

        # Step 2: the rows are locked by this transaction, so this is safe.
        statement = (
            update(EmailOutbox)
            .where(EmailOutbox.id.in_(claimed_ids))
            .values(
                status=EmailOutboxStatus.PROCESSING,
                locked_at=now,
                attempt_count=EmailOutbox.attempt_count + 1,
            )
            .returning(EmailOutbox)
            .execution_options(
                populate_existing=True,
                synchronize_session=False,
            )
        )

        result = await self.session.execute(statement)
        records = list(result.scalars().all())
        records.sort(key=lambda r: (r.next_attempt_at, r.created_at, r.id))
        return records

    async def get_by_id(
        self,
        email_outbox_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> EmailOutbox | None:
        statement = select(EmailOutbox).where(EmailOutbox.id == email_outbox_id)

        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def mark_sent(
        self,
        email_outbox_id: uuid.UUID,
        sent_at: datetime,
    ) -> bool:
        statement = (
            update(EmailOutbox)
            .where(
                EmailOutbox.id == email_outbox_id,
                EmailOutbox.status == EmailOutboxStatus.PROCESSING,
            )
            .values(
                status=EmailOutboxStatus.SENT,
                sent_at=sent_at,
                failed_at=None,
                locked_at=None,
                payload_encrypted=None,
                last_error=None,
            )
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return cast(CursorResult, result).rowcount == 1

    async def mark_retry(
        self,
        email_outbox_id: uuid.UUID,
        next_attempt_at: datetime,
        error: str,
    ) -> bool:
        statement = (
            update(EmailOutbox)
            .where(
                EmailOutbox.id == email_outbox_id,
                EmailOutbox.status == EmailOutboxStatus.PROCESSING,
                EmailOutbox.attempt_count < EmailOutbox.max_attempts,
            )
            .values(
                status=EmailOutboxStatus.PENDING,
                next_attempt_at=next_attempt_at,
                locked_at=None,
                sent_at=None,
                failed_at=None,
                last_error=error[:MAX_ERROR_LENGTH],
            )
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return cast(CursorResult, result).rowcount == 1

    async def mark_failed(
        self,
        email_outbox_id: uuid.UUID,
        error: str,
        failed_at: datetime,
    ) -> bool:
        statement = (
            update(EmailOutbox)
            .where(
                EmailOutbox.id == email_outbox_id,
                EmailOutbox.status == EmailOutboxStatus.PROCESSING,
            )
            .values(
                status=EmailOutboxStatus.FAILED,
                failed_at=failed_at,
                sent_at=None,
                locked_at=None,
                payload_encrypted=None,
                last_error=error[:MAX_ERROR_LENGTH],
            )
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return cast(CursorResult, result).rowcount == 1
