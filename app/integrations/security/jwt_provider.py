from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt

from app.core.config import Settings
from app.core.contracts.security.jwt_provider import AbstractJWTProvider


class JWTProvider(AbstractJWTProvider):
    def __init__(self, settings: Settings) -> None:
        self._secret_key = settings.JWT_SECRET_KEY.get_secret_value()
        self._algorithm = settings.JWT_ALGORITHM
        self._issuer = settings.JWT_ISSUER
        self._audience = settings.JWT_AUDIENCE
        self._access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    def create_access_token(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
    ) -> str:
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=self._access_token_expire_minutes)

        payload: dict[str, Any] = {
            "sub": str(user_id),
            "sid": str(session_id),
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "iss": self._issuer,
            "aud": self._audience,
        }

        return jwt.encode(
            payload,
            self._secret_key,
            algorithm=self._algorithm,
        )

    def decode_access_token(self, token: str) -> dict[str, Any]:
        payload = jwt.decode(
            token,
            self._secret_key,
            algorithms=[self._algorithm],
            issuer=self._issuer,
            audience=self._audience,
            options={
                "require_sub": True,
                "require_exp": True,
                "require_iat": True,
                "require_iss": True,
                "require_aud": True,
            },
        )

        if payload.get("type") != "access":
            raise JWTError("Invalid token type.")

        if not payload.get("sid"):
            raise JWTError("Missing session identifier.")

        return payload