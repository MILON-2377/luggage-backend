from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EnqueueEmailDTO:
    recipient: str
    subject: str
    html_content: str
    text_content: str | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class EmailDeliveryResultDTO:
    email_outbox_id: str
    status: str
    attempt_count: int
