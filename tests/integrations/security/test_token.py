
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.config import settings
from app.integrations.security.jwt_provider import JWTProvider
from app.integrations.security.sha256_token_hasher import SHA256TokenHasher
from app.modules.authentication.dtos.token import (
    CreateAuthenticationTokensRequest,
)
from app.modules.authentication.services.token import (
    AuthenticationTokenService,
)


def create_token_service() -> AuthenticationTokenService:
    return AuthenticationTokenService(
        jwt_provider=JWTProvider(settings=settings),
        token_hasher=SHA256TokenHasher(),
        settings=settings,
    )


def test_create_tokens_returns_valid_access_and_refresh_tokens() -> None:
    service = create_token_service()
    admin_user_id = uuid4()
    session_id = uuid4()
    issued_at = datetime.now(UTC)

    result = service.create_tokens(
        CreateAuthenticationTokensRequest(
            admin_user_id=admin_user_id,
            session_id=session_id,
            issued_at=issued_at,
        )
    )

    access_token = result.access_token.get_secret_value()
    refresh_token = result.refresh_token.get_secret_value()

    assert access_token
    assert refresh_token
    assert refresh_token != access_token
    assert result.refresh_token_hash == SHA256TokenHasher().hash_token(
        refresh_token
    )

    claims = JWTProvider(settings=settings).decode_access_token(access_token)

    assert claims["sub"] == str(admin_user_id)
    assert claims["sid"] == str(session_id)
    assert claims["type"] == "access"


def test_create_tokens_generates_unique_refresh_tokens() -> None:
    service = create_token_service()
    payload = CreateAuthenticationTokensRequest(
        admin_user_id=uuid4(),
        session_id=uuid4(),
        issued_at=datetime.now(UTC),
    )

    first_result = service.create_tokens(payload)
    second_result = service.create_tokens(payload)

    assert (
        first_result.refresh_token.get_secret_value()
        != second_result.refresh_token.get_secret_value()
    )
    assert first_result.refresh_token_hash != second_result.refresh_token_hash


def test_create_tokens_sets_expected_expiration_times() -> None:
    service = create_token_service()
    issued_at = datetime.now(UTC)

    result = service.create_tokens(
        CreateAuthenticationTokensRequest(
            admin_user_id=uuid4(),
            session_id=uuid4(),
            issued_at=issued_at,
        )
    )

    assert result.access_token_expires_at == issued_at + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    assert result.session_expires_at == issued_at + timedelta(
        days=settings.AUTH_SESSION_EXPIRE_DAYS
    )