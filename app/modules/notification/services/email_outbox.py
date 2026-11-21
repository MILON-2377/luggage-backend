import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.config import Settings
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.email.email_provider import (
    AbstractEmailProvider,
    EmailMessage,
)
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.contracts.security.secret_encryptor import SecretEncryptor
from app.modules.notification.contracts.repositories.email_outbox import (
    AbstractEmailOutboxRepository,
)
from app.modules.notification.contracts.services.email_outbox import (
    AbstractEmailOutboxService,
)
from app.modules.notification.dtos.email_outbox import (
    EmailDeliveryResultDTO,
    EnqueueEmailDTO,
)
from app.modules.notification.enums import EmailOutboxStatus
from app.modules.notification.models.email_outbox import EmailOutbox

logger = logging.getLogger(__name__)

MIN_LEASE_SECONDS = 60.0
MAX_ERROR_LENGTH = 1000


@dataclass(frozen=True, slots=True)
class _ClaimedEmail:
    id: uuid.UUID
    payload_encrypted: str
    attempt_count: int
    max_attempts: int


class EmailOutboxService(AbstractEmailOutboxService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        secret_encryptor: SecretEncryptor,
        id_generator: AbstractIDGenerator,
        settings: Settings,
        email_provider: AbstractEmailProvider | None = None,
    ) -> None:
        self.uow = uow
        self.email_provider = email_provider
        self.secret_encryptor = secret_encryptor
        self.id_generator = id_generator
        self.settings = settings

    async def enqueue(self, data: EnqueueEmailDTO) -> None:

        payload = json.dumps(
            {
                "recipient": data.recipient,
                "subject": data.subject,
                "html_content": data.html_content,
                "text_content": data.text_content,
            },
            ensure_ascii=False,
        )

        repository = self.uow.get_repository(AbstractEmailOutboxRepository)

        repository.create(
            EmailOutbox(
                id=self.id_generator.generate(),
                provider=self.settings.EMAIL_PROVIDER,
                payload_encrypted=self.secret_encryptor.encrypt(payload),
                idempotency_key=data.idempotency_key,
                status=EmailOutboxStatus.PENDING,
                attempt_count=0,
                max_attempts=self.settings.EMAIL_MAX_ATTEMPTS,
                next_attempt_at=datetime.now(UTC),
            )
        )
        await self.uow.flush()

    async def process_batch(
        self,
        *,
        limit: int = 20,
    ) -> list[EmailDeliveryResultDTO]:

        if self.email_provider is None:
            raise RuntimeError(
                "An email provider is required to process the email outbox."
            )

        if limit <= 0:
            raise ValueError("Batch limit must be greater than zero.")

        if limit <= 0:
            raise ValueError("Batch limit must be greater than zero.")

        claimed = await self._claim(limit)

        results: list[EmailDeliveryResultDTO] = []

        for item in claimed:
            result = await self._deliver(item)
            if result is not None:
                results.append(result)

        return results

    async def _claim(self, limit: int) -> list[_ClaimedEmail]:
        repository = self.uow.get_repository(AbstractEmailOutboxRepository)

        now = datetime.now(UTC)
        lease_duration = timedelta(seconds=self._lease_seconds())

        # claim_batch increments attempt_count atomically, so the service
        # must not increment it again.
        records = await repository.claim_batch(
            now=now,
            lease_expires_before=now - lease_duration,
            limit=limit,
        )

        # Snapshot plain values before commit; ORM objects must not be
        # touched after the transaction ends.
        claimed = [
            _ClaimedEmail(
                id=record.id,
                payload_encrypted=record.payload_encrypted,
                attempt_count=record.attempt_count,
                max_attempts=record.max_attempts,
            )
            for record in records
        ]

        await self.uow.commit()
        return claimed

    async def _deliver(self, item: _ClaimedEmail) -> EmailDeliveryResultDTO | None:
        repository = self.uow.get_repository(AbstractEmailOutboxRepository)

        try:
            message = self._decode_message(item.payload_encrypted)
            await self.email_provider.send(message)
        except Exception as exc:
            logger.exception(
                "Email outbox delivery failed: id=%s error_type=%s",
                item.id,
                type(exc).__name__,
            )
            return await self._record_failure(item, exc)

        try:
            marked = await repository.mark_sent(item.id, datetime.now(UTC))
            await self.uow.commit()
        except Exception:
            await self.uow.rollback()
            logger.exception("Email sent but status update failed: id=%s", item.id)
            return None

        if not marked:
            logger.warning("Email outbox lease lost after send: id=%s", item.id)
            return None

        return EmailDeliveryResultDTO(
            email_outbox_id=str(item.id),
            status=EmailOutboxStatus.SENT.value,
            attempt_count=item.attempt_count,
        )

    async def _record_failure(
        self,
        item: _ClaimedEmail,
        exc: Exception,
    ) -> EmailDeliveryResultDTO | None:
        repository = self.uow.get_repository(AbstractEmailOutboxRepository)

        now = datetime.now(UTC)
        error = type(exc).__name__[:MAX_ERROR_LENGTH]
        exhausted = item.attempt_count >= item.max_attempts

        try:
            if exhausted:
                updated = await repository.mark_failed(
                    item.id,
                    error,
                    failed_at=now,
                )
                status = EmailOutboxStatus.FAILED
            else:
                updated = await repository.mark_retry(
                    item.id,
                    now + timedelta(seconds=self._backoff_seconds(item.attempt_count)),
                    error,
                )
                status = EmailOutboxStatus.PENDING

            await self.uow.commit()
        except Exception:
            await self.uow.rollback()
            logger.exception("Failed to record email failure: id=%s", item.id)
            return None

        if not updated:
            logger.warning("Email outbox lease lost after failure: id=%s", item.id)
            return None

        return EmailDeliveryResultDTO(
            email_outbox_id=str(item.id),
            status=status.value,
            attempt_count=item.attempt_count,
        )

    def _decode_message(self, payload_encrypted: str) -> EmailMessage:
        data = json.loads(self.secret_encryptor.decrypt(payload_encrypted))

        return EmailMessage(
            recipient=data["recipient"],
            subject=data["subject"],
            html_content=data["html_content"],
            text_content=data.get("text_content"),
        )

    def _backoff_seconds(self, attempt_count: int) -> float:
        backoff = self.settings.EMAIL_RETRY_BACKOFF_SECONDS
        return float(backoff[min(max(attempt_count, 1) - 1, len(backoff) - 1)])

    def _lease_seconds(self) -> float:
        # Worst case for one send call: every provider attempt times out and
        # every retry sleeps for its full (capped) delay.
        worst_case = (
            self.settings.EMAIL_REQUEST_TIMEOUT * self.settings.EMAIL_MAX_ATTEMPTS
            + sum(self.settings.EMAIL_RETRY_BACKOFF_SECONDS)
        )
        # The lease must also cover the time spent on earlier emails in the
        # same batch, so add headroom per email.
        return max(MIN_LEASE_SECONDS, worst_case * 2)
