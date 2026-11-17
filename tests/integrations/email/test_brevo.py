import json

import httpx
import pytest
from pydantic import SecretStr

from app.core.contracts.email.email_provider import EmailMessage
from app.integrations.email.brevo import BrevoEmailProvider
from app.integrations.email.errors import (
    EmailDeliveryError,
    EmailProviderUnavailableError,
)


class FakeSettings:
    def __init__(self) -> None:
        self.BREVO_API_KEY = SecretStr("test-api-key")
        self.BREVO_API_URL = "https://api.brevo.test/v3/smtp/email"
        self.EMAIL_FROM_ADDRESS = "no-reply@example.com"
        self.EMAIL_FROM_NAME = "Example Showroom"
        self.EMAIL_REQUEST_TIMEOUT = 5.0
        self.EMAIL_MAX_ATTEMPTS = 3
        self.EMAIL_RETRY_BACKOFF_SECONDS = [0.5, 1.5]
        self.EMAIL_MAX_RETRY_AFTER_SECONDS = 5.0


@pytest.fixture
def settings() -> FakeSettings:
    return FakeSettings()


@pytest.fixture
def message() -> EmailMessage:
    return EmailMessage(
        recipient="user@example.com",
        subject="Welcome",
        html_content="<p>Hello</p>",
        text_content="Hello",
    )


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    recorded: list[float] = []

    async def fake_sleep(delay: float) -> None:
        recorded.append(delay)

    monkeypatch.setattr("app.integrations.email.brevo.asyncio.sleep", fake_sleep)
    return recorded


def make_provider(settings: FakeSettings, handler) -> BrevoEmailProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return BrevoEmailProvider(settings, client)  # type: ignore[arg-type]


class TestSuccess:
    async def test_sends_expected_request(
        self, settings: FakeSettings, message: EmailMessage
    ) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(201, json={"messageId": "abc"})

        await make_provider(settings, handler).send(message)

        assert len(captured) == 1
        request = captured[0]
        assert request.method == "POST"
        assert str(request.url) == settings.BREVO_API_URL
        assert request.headers["api-key"] == "test-api-key"
        assert request.headers["accept"] == "application/json"
        assert json.loads(request.content) == {
            "sender": {
                "name": "Example Showroom",
                "email": "no-reply@example.com",
            },
            "to": [{"email": "user@example.com"}],
            "subject": "Welcome",
            "htmlContent": "<p>Hello</p>",
            "textContent": "Hello",
        }

    async def test_omits_text_content_when_none(self, settings: FakeSettings) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(201)

        message = EmailMessage(
            recipient="user@example.com",
            subject="Hi",
            html_content="<p>Hi</p>",
            text_content=None,
        )

        await make_provider(settings, handler).send(message)

        assert "textContent" not in json.loads(captured[0].content)

    async def test_no_sleep_on_first_attempt_success(
        self,
        settings: FakeSettings,
        message: EmailMessage,
        sleeps: list[float],
    ) -> None:
        await make_provider(settings, lambda _r: httpx.Response(201)).send(message)
        assert sleeps == []


class TestNonRetryableErrors:
    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 422])
    async def test_raises_delivery_error_without_retry(
        self,
        settings: FakeSettings,
        message: EmailMessage,
        sleeps: list[float],
        status_code: int,
    ) -> None:
        calls = 0

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(status_code, json={"message": "nope"})

        with pytest.raises(EmailDeliveryError) as exc_info:
            await make_provider(settings, handler).send(message)

        assert not isinstance(exc_info.value, EmailProviderUnavailableError)
        assert str(status_code) in str(exc_info.value)
        assert calls == 1
        assert sleeps == []

    async def test_error_message_does_not_leak_body_or_key(
        self, settings: FakeSettings, message: EmailMessage
    ) -> None:
        provider = make_provider(
            settings,
            lambda _r: httpx.Response(400, text="secret-body-content"),
        )

        with pytest.raises(EmailDeliveryError) as exc_info:
            await provider.send(message)

        assert "secret-body-content" not in str(exc_info.value)
        assert "test-api-key" not in str(exc_info.value)


class TestRetries:
    @pytest.mark.parametrize("status_code", [408, 425, 429, 500, 502, 503, 504])
    async def test_retries_retryable_status_then_succeeds(
        self,
        settings: FakeSettings,
        message: EmailMessage,
        sleeps: list[float],
        status_code: int,
    ) -> None:
        responses = iter([httpx.Response(status_code), httpx.Response(201)])

        await make_provider(settings, lambda _r: next(responses)).send(message)

        assert sleeps == [0.5]

    async def test_raises_unavailable_after_all_attempts(
        self,
        settings: FakeSettings,
        message: EmailMessage,
        sleeps: list[float],
    ) -> None:
        calls = 0

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(503)

        with pytest.raises(EmailProviderUnavailableError):
            await make_provider(settings, handler).send(message)

        assert calls == settings.EMAIL_MAX_ATTEMPTS
        assert sleeps == [0.5, 1.5]

    async def test_no_sleep_after_final_attempt(
        self,
        settings: FakeSettings,
        message: EmailMessage,
        sleeps: list[float],
    ) -> None:
        settings.EMAIL_MAX_ATTEMPTS = 1

        with pytest.raises(EmailProviderUnavailableError):
            await make_provider(settings, lambda _r: httpx.Response(500)).send(message)

        assert sleeps == []

    async def test_backoff_reuses_last_value_when_list_is_short(
        self,
        settings: FakeSettings,
        message: EmailMessage,
        sleeps: list[float],
    ) -> None:
        settings.EMAIL_MAX_ATTEMPTS = 4

        with pytest.raises(EmailProviderUnavailableError):
            await make_provider(settings, lambda _r: httpx.Response(500)).send(message)

        assert sleeps == [0.5, 1.5, 1.5]

    async def test_chained_error_is_preserved(
        self,
        settings: FakeSettings,
        message: EmailMessage,
        sleeps: list[float],
    ) -> None:
        with pytest.raises(EmailProviderUnavailableError) as exc_info:
            await make_provider(settings, lambda _r: httpx.Response(502)).send(message)

        assert isinstance(exc_info.value.__cause__, EmailProviderUnavailableError)
        assert "502" in str(exc_info.value.__cause__)


class TestTransportErrors:
    @pytest.mark.parametrize(
        "exception",
        [
            httpx.ConnectError("boom"),
            httpx.ReadTimeout("slow"),
            httpx.ConnectTimeout("slow"),
            httpx.RemoteProtocolError("bad"),
        ],
    )
    async def test_retries_transport_errors_then_succeeds(
        self,
        settings: FakeSettings,
        message: EmailMessage,
        sleeps: list[float],
        exception: Exception,
    ) -> None:
        outcomes: list[Exception | httpx.Response] = [exception, httpx.Response(201)]

        def handler(_request: httpx.Request) -> httpx.Response:
            outcome = outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        await make_provider(settings, handler).send(message)

        assert sleeps == [0.5]

    async def test_raises_unavailable_when_transport_always_fails(
        self,
        settings: FakeSettings,
        message: EmailMessage,
        sleeps: list[float],
    ) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("down")

        with pytest.raises(EmailProviderUnavailableError) as exc_info:
            await make_provider(settings, handler).send(message)

        assert isinstance(exc_info.value.__cause__, httpx.ConnectError)
        assert sleeps == [0.5, 1.5]


class TestRetryAfter:
    @pytest.mark.parametrize(
        ("header", "expected"),
        [
            ("2", 2.0),
            ("0", 0.0),
            ("-3", 0.0),
            ("99", 5.0),
            ("1.5", 1.5),
        ],
    )
    async def test_honors_and_clamps_retry_after(
        self,
        settings: FakeSettings,
        message: EmailMessage,
        sleeps: list[float],
        header: str,
        expected: float,
    ) -> None:
        responses = iter(
            [httpx.Response(429, headers={"retry-after": header}), httpx.Response(201)]
        )

        await make_provider(settings, lambda _r: next(responses)).send(message)

        assert sleeps == [expected]

    async def test_clamp_uses_configured_maximum(
        self,
        settings: FakeSettings,
        message: EmailMessage,
        sleeps: list[float],
    ) -> None:
        settings.EMAIL_MAX_RETRY_AFTER_SECONDS = 30.0
        responses = iter(
            [httpx.Response(429, headers={"retry-after": "20"}), httpx.Response(201)]
        )

        await make_provider(settings, lambda _r: next(responses)).send(message)

        assert sleeps == [20.0]

    async def test_clamp_applies_lower_configured_maximum(
        self,
        settings: FakeSettings,
        message: EmailMessage,
        sleeps: list[float],
    ) -> None:
        settings.EMAIL_MAX_RETRY_AFTER_SECONDS = 1.0
        responses = iter(
            [httpx.Response(429, headers={"retry-after": "4"}), httpx.Response(201)]
        )

        await make_provider(settings, lambda _r: next(responses)).send(message)

        assert sleeps == [1.0]

    @pytest.mark.parametrize(
        "header",
        ["nan", "inf", "-inf", "Wed, 21 Oct 2026 07:28:00 GMT", ""],
    )
    async def test_invalid_retry_after_falls_back_to_backoff(
        self,
        settings: FakeSettings,
        message: EmailMessage,
        sleeps: list[float],
        header: str,
    ) -> None:
        responses = iter(
            [httpx.Response(429, headers={"retry-after": header}), httpx.Response(201)]
        )

        await make_provider(settings, lambda _r: next(responses)).send(message)

        assert sleeps == [0.5]

    async def test_missing_retry_after_uses_backoff(
        self,
        settings: FakeSettings,
        message: EmailMessage,
        sleeps: list[float],
    ) -> None:
        responses = iter([httpx.Response(503), httpx.Response(201)])

        await make_provider(settings, lambda _r: next(responses)).send(message)

        assert sleeps == [0.5]

    async def test_retry_after_is_ignored_for_transport_errors(
        self,
        settings: FakeSettings,
        message: EmailMessage,
        sleeps: list[float],
    ) -> None:
        outcomes: list[Exception | httpx.Response] = [
            httpx.ConnectError("boom"),
            httpx.Response(201),
        ]

        def handler(_request: httpx.Request) -> httpx.Response:
            outcome = outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        await make_provider(settings, handler).send(message)

        assert sleeps == [0.5]


class TestConstruction:
    def test_rejects_empty_backoff_list(self, settings: FakeSettings) -> None:
        settings.EMAIL_RETRY_BACKOFF_SECONDS = []
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _r: httpx.Response(201))
        )

        with pytest.raises(ValueError, match="EMAIL_RETRY_BACKOFF_SECONDS"):
            BrevoEmailProvider(settings, client)  # type: ignore[arg-type]