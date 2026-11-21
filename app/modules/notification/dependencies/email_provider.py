from fastapi import Request

from app.core.config import settings
from app.integrations.email.brevo import BrevoEmailProvider


def get_email_provider(request: Request) -> BrevoEmailProvider:
    return BrevoEmailProvider(
        settings=settings,
        client=request.app.state.http_client,
    )
