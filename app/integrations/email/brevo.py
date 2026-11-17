import asyncio
import logging
import math
from typing import Any

import httpx

from app.core.config import Settings
from app.core.contracts.email.email_provider import (
    AbstractEmailProvider,
    EmailMessage,
)
from app.integrations.email.errors import (
    EmailDeliveryError,
    EmailProviderUnavailableError,
)

logger = logging.getLogger(__name__)


class BrevoEmailProvider(AbstractEmailProvider):
    RETRYABLE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})

    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient,
    ) -> None:
        if not settings.EMAIL_RETRY_BACKOFF_SECONDS:
            raise ValueError("EMAIL_RETRY_BACKOFF_SECONDS must not be empty")

        self.settings = settings
        self.client = client

    async def send(self, message: EmailMessage) -> None:
        payload = self._build_payload(message)
        headers = {
            "api-key": self.settings.BREVO_API_KEY.get_secret_value(),
            "accept": "application/json",
            "content-type": "application/json",
        }
        max_attempts = self.settings.EMAIL_MAX_ATTEMPTS
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            retry_after: str | None = None

            try:
                response = await self.client.post(
                    self.settings.BREVO_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=self.settings.EMAIL_REQUEST_TIMEOUT,
                )
            except httpx.TransportError as exc:
                last_error = exc
                logger.warning(
                    "Brevo request failed (attempt %d/%d): %s",
                    attempt,
                    max_attempts,
                    type(exc).__name__,
                )
            else:
                if response.is_success:
                    return

                if response.status_code not in self.RETRYABLE_STATUS_CODES:
                    logger.error(
                        "Brevo rejected email: status=%d",
                        response.status_code,
                    )
                    raise EmailDeliveryError(
                        f"Email provider rejected the message "
                        f"(status {response.status_code})"
                    )

                last_error = EmailProviderUnavailableError(
                    f"Brevo returned status {response.status_code}"
                )
                retry_after = response.headers.get("retry-after")
                logger.warning(
                    "Brevo returned retryable status %d (attempt %d/%d)",
                    response.status_code,
                    attempt,
                    max_attempts,
                )

            if attempt < max_attempts:
                await asyncio.sleep(self._retry_delay(attempt, retry_after))

        raise EmailProviderUnavailableError from last_error

    def _build_payload(self, message: EmailMessage) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "sender": {
                "name": self.settings.EMAIL_FROM_NAME,
                "email": self.settings.EMAIL_FROM_ADDRESS,
            },
            "to": [{"email": message.recipient}],
            "subject": message.subject,
            "htmlContent": message.html_content,
        }

        if message.text_content is not None:
            payload["textContent"] = message.text_content

        return payload

    def _retry_delay(self, attempt: int, retry_after: str | None) -> float:
        backoff = self.settings.EMAIL_RETRY_BACKOFF_SECONDS
        delay = float(backoff[min(attempt - 1, len(backoff) - 1)])

        if retry_after is not None:
            try:
                requested = float(retry_after)
            except ValueError:
                return delay

            if math.isfinite(requested):
                return min(max(requested, 0.0), self.settings.EMAIL_MAX_RETRY_AFTER_SECONDS)

        return delay
