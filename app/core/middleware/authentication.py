import logging
from uuid import UUID

from jose import JWTError
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import Settings
from app.core.config import settings as default_settings
from app.core.contracts.security.jwt_provider import AbstractJWTProvider
from app.integrations.security.cookie_policy import CookiePolicy
from app.integrations.security.cookie_service import CookieService
from app.integrations.security.jwt_provider import JWTProvider

logger = logging.getLogger(__name__)


class AuthenticationMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        app_settings: Settings = default_settings,
        jwt_provider: AbstractJWTProvider | None = None,
        cookie_service: CookieService | None = None,
    ) -> None:
        self.app = app
        self.jwt_provider: AbstractJWTProvider = jwt_provider or JWTProvider(
            settings=app_settings
        )
        self.cookie_service = cookie_service or CookieService(
            policy=CookiePolicy(settings=app_settings),
        )

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        state = scope.setdefault("state", {})
        state["authenticated_user_id"] = None
        state["authenticated_session_id"] = None
        state["access_token_claims"] = None

        request = Request(scope, receive=receive)
        access_token = self.cookie_service.get_access_token(request)

        logger.debug(
            "Access token cookie received: %s",
            access_token is not None,
        )

        if access_token:
            try:
                claims = self.jwt_provider.decode_access_token(access_token)

                if claims.get("type") != "access":
                    raise JWTError("Invalid token type.")

                state["authenticated_user_id"] = UUID(claims["sub"])
                state["authenticated_session_id"] = UUID(claims["sid"])
                state["access_token_claims"] = claims

            except (JWTError, ValueError, TypeError, KeyError):
                pass

        await self.app(scope, receive, send)