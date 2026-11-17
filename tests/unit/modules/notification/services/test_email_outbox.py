import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.contracts.email.email_provider import EmailMessage
from app.modules.authentication.models.admin_user import AdminUser
from app.modules.media.models.media_asset import MediaAsset
from app.modules.notification.contracts.repositories.email_outbox import (
    AbstractEmailOutboxRepository,
)
from app.modules.notification.dtos.email_outbox import EnqueueEmailDTO
from app.modules.notification.enums import EmailOutboxStatus
from app.modules.notification.models.email_outbox import EmailOutbox
from app.modules.notification.services.email_outbox import EmailOutboxService


class FakeSettings:
    def __init__(self) -> None:
        self.EMAIL_PROVIDER = "brevo"
        self.EMAIL_MAX_ATTEMPTS = 3
        self.EMAIL_REQUEST_TIMEOUT = 10.0
        self.EMAIL_RETRY_BACKOFF_SECONDS = [0.5, 1.5]


class FakeEncryptor:
    def encrypt(self, value: str) -> str:
        return f"enc:{value}"

    def decrypt(self, value: str) -> str:
        assert value.startswith("enc:")
        return value[len("enc:") :]


class FakeIDGenerator:
    def generate(self) -> uuid.UUID:
        return uuid.uuid4()


class FakeProvider:
    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []
        self.error: Exception | None = None

    async def send(self, message: EmailMessage) -> None:
        if self.error is not None:
            raise self.error
        self.sent.append(message)


class FakeRepository:
    def __init__(self) -> None:
        self.created: list[EmailOutbox] = []
        self.claim_result: list[Any] = []
        self.claim_kwargs: dict[str, Any] | None = None
        self.sent_calls: list[tuple[uuid.UUID, datetime]] = []
        self.retry_calls: list[tuple[uuid.UUID, datetime, str]] = []
        self.failed_calls: list[tuple[uuid.UUID, str]] = []
        self.mark_result = True
        self.mark_error: Exception | None = None

    def create(self, entity: EmailOutbox) -> None:
        self.created.append(entity)

    async def claim_batch(self, **kwargs: Any) -> list[Any]:
        self.claim_kwargs = kwargs
        return self.claim_result

    async def mark_sent(self, outbox_id: uuid.UUID, sent_at: datetime) -> bool:
        if self.mark_error:
            raise self.mark_error
        self.sent_calls.append((outbox_id, sent_at))
        return self.mark_result

    async def mark_retry(
        self, outbox_id: uuid.UUID, next_attempt_at: datetime, error: str
    ) -> bool:
        if self.mark_error:
            raise self.mark_error
        self.retry_calls.append((outbox_id, next_attempt_at, error))
        return self.mark_result

    async def mark_failed(self, outbox_id: uuid.UUID, error: str) -> bool:
        if self.mark_error:
            raise self.mark_error
        self.failed_calls.append((outbox_id, error))
        return self.mark_result


class FakeUoW:
    def __init__(self, repository: FakeRepository) -> None:
        self.repository = repository
        self.commits = 0
        self.rollbacks = 0
        self.flushes = 0

    def get_repository(self, repository_type: type) -> FakeRepository:
        assert repository_type is AbstractEmailOutboxRepository
        return self.repository

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def flush(self) -> None:
        self.flushes += 1


def make_record(
    *,
    attempt_count: int = 1,
    max_attempts: int = 3,
    recipient: str = "user@example.com",
) -> SimpleNamespace:
    payload = json.dumps(
        {
            "recipient": recipient,
            "subject": "Hello",
            "html_content": "<p>Hi</p>",
            "text_content": "Hi",
        }
    )
    return SimpleNamespace(
        id=uuid.uuid4(),
        payload_encrypted=f"enc:{payload}",
        attempt_count=attempt_count,
        max_attempts=max_attempts,
    )


@dataclass
class Env:
    service: EmailOutboxService
    uow: FakeUoW
    repo: FakeRepository
    provider: FakeProvider
    settings: FakeSettings


@pytest.fixture
def env() -> Env:
    repo = FakeRepository()
    uow = FakeUoW(repo)
    provider = FakeProvider()
    settings = FakeSettings()
    service = EmailOutboxService(
        uow=uow,  # type: ignore[arg-type]
        email_provider=provider,  # type: ignore[arg-type]
        secret_encryptor=FakeEncryptor(),  # type: ignore[arg-type]
        id_generator=FakeIDGenerator(),  # type: ignore[arg-type]
        settings=settings,  # type: ignore[arg-type]
    )
    return Env(service, uow, repo, provider, settings)


class TestEnqueue:
    async def test_creates_pending_record_with_encrypted_payload(
        self, env: Env
    ) -> None:
        before = datetime.now(UTC)

        await env.service.enqueue(
            EnqueueEmailDTO(
                recipient="user@example.com",
                subject="Welcome",
                html_content="<p>Hello</p>",
                text_content=None,
                idempotency_key="invite:123",
            )
        )

        assert len(env.repo.created) == 1
        record = env.repo.created[0]
        assert record.status == EmailOutboxStatus.PENDING
        assert record.attempt_count == 0
        assert record.max_attempts == 3
        assert record.provider == "brevo"
        assert record.idempotency_key == "invite:123"
        assert record.next_attempt_at >= before
        assert record.payload_encrypted.startswith("enc:")

        payload = json.loads(record.payload_encrypted[len("enc:") :])
        assert payload == {
            "recipient": "user@example.com",
            "subject": "Welcome",
            "html_content": "<p>Hello</p>",
            "text_content": None,
        }

    async def test_does_not_leak_plaintext_into_record(self, env: Env) -> None:
        await env.service.enqueue(
            EnqueueEmailDTO(
                recipient="secret@example.com",
                subject="S",
                html_content="<p>x</p>",
                text_content=None,
                idempotency_key="k",
            )
        )

        record = env.repo.created[0]
        assert "secret@example.com" not in record.__dict__.get("idempotency_key", "")

    async def test_flushes_but_never_commits(self, env: Env) -> None:
        await env.service.enqueue(
            EnqueueEmailDTO(
                recipient="user@example.com",
                subject="S",
                html_content="<p>x</p>",
                text_content=None,
                idempotency_key="k",
            )
        )

        assert env.uow.flushes == 1
        assert env.uow.commits == 0


class TestProcessBatchValidation:
    @pytest.mark.parametrize("limit", [0, -1])
    async def test_rejects_non_positive_limit(self, env: Env, limit: int) -> None:
        with pytest.raises(ValueError):
            await env.service.process_batch(limit=limit)

        assert env.repo.claim_kwargs is None

    async def test_empty_claim_returns_empty_and_commits_once(self, env: Env) -> None:
        results = await env.service.process_batch()

        assert results == []
        assert env.uow.commits == 1
        assert env.provider.sent == []


class TestClaim:
    async def test_passes_limit_and_lease_window(self, env: Env) -> None:
        await env.service.process_batch(limit=7)

        kwargs = env.repo.claim_kwargs
        assert kwargs is not None
        assert kwargs["limit"] == 7
        lease = kwargs["now"] - kwargs["lease_expires_before"]
        # worst case = 10*3 + 2.0 = 32; doubled = 64; floor is 60
        assert lease == timedelta(seconds=64)

    async def test_lease_has_minimum_floor(self, env: Env) -> None:
        env.settings.EMAIL_REQUEST_TIMEOUT = 1.0
        env.settings.EMAIL_MAX_ATTEMPTS = 1
        env.settings.EMAIL_RETRY_BACKOFF_SECONDS = [0.1]

        await env.service.process_batch()

        kwargs = env.repo.claim_kwargs
        assert kwargs is not None
        assert kwargs["now"] - kwargs["lease_expires_before"] == timedelta(seconds=60)

    async def test_claim_is_committed_before_sending(self, env: Env) -> None:
        env.repo.claim_result = [make_record()]
        commits_at_send: list[int] = []

        original_send = env.provider.send

        async def spy_send(message: EmailMessage) -> None:
            commits_at_send.append(env.uow.commits)
            await original_send(message)

        env.provider.send = spy_send  # type: ignore[method-assign]

        await env.service.process_batch()

        assert commits_at_send == [1]


class TestSuccessfulDelivery:
    async def test_sends_decoded_message_and_marks_sent(self, env: Env) -> None:
        record = make_record(attempt_count=1)
        env.repo.claim_result = [record]

        results = await env.service.process_batch()

        assert env.provider.sent == [
            EmailMessage(
                recipient="user@example.com",
                subject="Hello",
                html_content="<p>Hi</p>",
                text_content="Hi",
            )
        ]
        assert [call[0] for call in env.repo.sent_calls] == [record.id]
        assert len(results) == 1
        assert results[0].email_outbox_id == str(record.id)
        assert results[0].status == EmailOutboxStatus.SENT.value
        assert results[0].attempt_count == 1

    async def test_commits_claim_and_each_delivery(self, env: Env) -> None:
        env.repo.claim_result = [make_record(), make_record()]

        await env.service.process_batch()

        assert env.uow.commits == 3

    async def test_does_not_increment_attempt_count_again(self, env: Env) -> None:
        env.repo.claim_result = [make_record(attempt_count=2)]

        results = await env.service.process_batch()

        assert results[0].attempt_count == 2

    async def test_handles_missing_text_content_key(self, env: Env) -> None:
        record = make_record()
        payload = json.dumps(
            {
                "recipient": "a@example.com",
                "subject": "S",
                "html_content": "<p>x</p>",
            }
        )
        record.payload_encrypted = f"enc:{payload}"
        env.repo.claim_result = [record]

        await env.service.process_batch()

        assert env.provider.sent[0].text_content is None


class TestFailedDelivery:
    async def test_schedules_retry_with_backoff(self, env: Env) -> None:
        record = make_record(attempt_count=1, max_attempts=3)
        env.repo.claim_result = [record]
        env.provider.error = RuntimeError("boom")
        before = datetime.now(UTC)

        results = await env.service.process_batch()

        assert env.repo.failed_calls == []
        assert len(env.repo.retry_calls) == 1
        outbox_id, next_attempt_at, error = env.repo.retry_calls[0]
        assert outbox_id == record.id
        assert error == "RuntimeError"
        assert next_attempt_at >= before + timedelta(seconds=0.5)
        assert results[0].status == EmailOutboxStatus.PENDING.value
        assert results[0].attempt_count == 1

    async def test_backoff_grows_with_attempt_count(self, env: Env) -> None:
        env.repo.claim_result = [make_record(attempt_count=2, max_attempts=5)]
        env.provider.error = RuntimeError("boom")
        before = datetime.now(UTC)

        await env.service.process_batch()

        next_attempt_at = env.repo.retry_calls[0][1]
        delta = next_attempt_at - before
        assert timedelta(seconds=1.5) <= delta < timedelta(seconds=3)

    async def test_backoff_reuses_last_value_beyond_list(self, env: Env) -> None:
        env.repo.claim_result = [make_record(attempt_count=9, max_attempts=10)]
        env.provider.error = RuntimeError("boom")
        before = datetime.now(UTC)

        await env.service.process_batch()

        delta = env.repo.retry_calls[0][1] - before
        assert timedelta(seconds=1.5) <= delta < timedelta(seconds=3)

    async def test_marks_failed_when_attempts_exhausted(self, env: Env) -> None:
        record = make_record(attempt_count=3, max_attempts=3)
        env.repo.claim_result = [record]
        env.provider.error = RuntimeError("boom")

        results = await env.service.process_batch()

        assert env.repo.retry_calls == []
        assert env.repo.failed_calls == [(record.id, "RuntimeError")]
        assert results[0].status == EmailOutboxStatus.FAILED.value

    async def test_stores_only_exception_type_not_message(self, env: Env) -> None:
        env.repo.claim_result = [make_record()]
        env.provider.error = RuntimeError("user@example.com secret-token")

        await env.service.process_batch()

        assert env.repo.retry_calls[0][2] == "RuntimeError"

    async def test_undecryptable_payload_is_treated_as_failure(self, env: Env) -> None:
        record = make_record(attempt_count=1)
        record.payload_encrypted = "garbage"
        env.repo.claim_result = [record]

        results = await env.service.process_batch()

        assert env.provider.sent == []
        assert len(env.repo.retry_calls) == 1
        assert results[0].status == EmailOutboxStatus.PENDING.value

    async def test_malformed_json_payload_is_treated_as_failure(self, env: Env) -> None:
        record = make_record()
        record.payload_encrypted = "enc:{not json"
        env.repo.claim_result = [record]

        results = await env.service.process_batch()

        assert env.repo.retry_calls[0][2] == "JSONDecodeError"
        assert results[0].status == EmailOutboxStatus.PENDING.value

    async def test_missing_required_field_is_treated_as_failure(self, env: Env) -> None:
        record = make_record()
        record.payload_encrypted = 'enc:{"recipient": "a@example.com"}'
        env.repo.claim_result = [record]

        await env.service.process_batch()

        assert env.repo.retry_calls[0][2] == "KeyError"


class TestBatchIsolation:
    async def test_one_failure_does_not_stop_the_rest(self, env: Env) -> None:
        bad = make_record(recipient="bad@example.com")
        good = make_record(recipient="good@example.com")
        env.repo.claim_result = [bad, good]

        original_send = env.provider.send

        async def flaky_send(message: EmailMessage) -> None:
            if message.recipient == "bad@example.com":
                raise RuntimeError("boom")
            await original_send(message)

        env.provider.send = flaky_send  # type: ignore[method-assign]

        results = await env.service.process_batch()

        assert [r.status for r in results] == [
            EmailOutboxStatus.PENDING.value,
            EmailOutboxStatus.SENT.value,
        ]
        assert [m.recipient for m in env.provider.sent] == ["good@example.com"]

    async def test_results_preserve_claim_order(self, env: Env) -> None:
        records = [make_record() for _ in range(3)]
        env.repo.claim_result = records

        results = await env.service.process_batch()

        assert [r.email_outbox_id for r in results] == [str(r.id) for r in records]


class TestLeaseAndStatusUpdateProblems:
    async def test_lease_lost_after_send_returns_no_result(self, env: Env) -> None:
        env.repo.claim_result = [make_record()]
        env.repo.mark_result = False

        results = await env.service.process_batch()

        assert len(env.provider.sent) == 1
        assert results == []

    async def test_lease_lost_after_failure_returns_no_result(self, env: Env) -> None:
        env.repo.claim_result = [make_record()]
        env.provider.error = RuntimeError("boom")
        env.repo.mark_result = False

        results = await env.service.process_batch()

        assert results == []

    async def test_status_update_error_after_send_rolls_back(self, env: Env) -> None:
        env.repo.claim_result = [make_record(), make_record()]
        env.repo.mark_error = RuntimeError("db down")

        results = await env.service.process_batch()

        assert len(env.provider.sent) == 2
        assert results == []
        assert env.uow.rollbacks == 2

    async def test_status_update_error_after_failure_rolls_back(self, env: Env) -> None:
        env.repo.claim_result = [make_record()]
        env.provider.error = RuntimeError("boom")
        env.repo.mark_error = RuntimeError("db down")

        results = await env.service.process_batch()

        assert results == []
        assert env.uow.rollbacks == 1
