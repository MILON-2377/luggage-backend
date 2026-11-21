from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.modules.notification.enums import EmailOutboxStatus
from app.modules.notification.repositories.email_outbox import (
    EmailOutboxRepository,
)


@pytest.fixture
def repository(db_session):
    return EmailOutboxRepository(db_session)


@pytest.mark.asyncio
async def test_claim_batch_returns_empty_when_limit_is_zero(repository):
    result = await repository.claim_batch(
        now=datetime.now(UTC),
        lease_expires_before=datetime.now(UTC) - timedelta(minutes=1),
        limit=0,
    )

    assert result == []


@pytest.mark.asyncio
async def test_mark_failed_sets_failed_timestamp_and_clears_payload(
    repository,
    email_outbox,
):
    failed_at = datetime.now(UTC)

    result = await repository.mark_failed(
        email_outbox.id,
        "EmailDeliveryError",
        failed_at,
    )

    assert result is True

    await repository.session.refresh(email_outbox)

    assert email_outbox.status == EmailOutboxStatus.FAILED
    assert email_outbox.failed_at == failed_at
    assert email_outbox.sent_at is None
    assert email_outbox.locked_at is None
    assert email_outbox.payload_encrypted is None
    assert email_outbox.last_error == "EmailDeliveryError"


@pytest.mark.asyncio
async def test_mark_sent_clears_payload_and_sets_sent_timestamp(
    repository,
    email_outbox,
):
    sent_at = datetime.now(UTC)

    result = await repository.mark_sent(email_outbox.id, sent_at)

    assert result is True

    await repository.session.refresh(email_outbox)

    assert email_outbox.status == EmailOutboxStatus.SENT
    assert email_outbox.sent_at == sent_at
    assert email_outbox.failed_at is None
    assert email_outbox.locked_at is None
    assert email_outbox.payload_encrypted is None


@pytest.mark.asyncio
async def test_mark_retry_resets_terminal_timestamps(
    repository,
    email_outbox,
):
    result = await repository.mark_retry(
        email_outbox.id,
        datetime.now(UTC) + timedelta(seconds=30),
        "EmailDeliveryError",
    )

    assert result is True

    await repository.session.refresh(email_outbox)

    assert email_outbox.status == EmailOutboxStatus.PENDING
    assert email_outbox.sent_at is None
    assert email_outbox.failed_at is None
    assert email_outbox.locked_at is None
    assert email_outbox.last_error == "EmailDeliveryError"


@pytest.mark.asyncio
async def test_mark_retry_rejects_exhausted_attempts(
    repository,
    email_outbox,
):
    email_outbox.attempt_count = email_outbox.max_attempts
    await repository.session.flush()

    result = await repository.mark_retry(
        email_outbox.id,
        datetime.now(UTC) + timedelta(seconds=30),
        "EmailDeliveryError",
    )

    assert result is False
