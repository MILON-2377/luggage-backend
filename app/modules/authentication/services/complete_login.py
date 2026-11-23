from datetime import UTC, datetime

from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.modules.authentication.contracts.services.complete_login import (
    AbstractCompleteLoginService,
)
from app.modules.authentication.contracts.services.session import (
    AbstractAdminSessionService,
)
from app.modules.authentication.contracts.services.token import (
    AbstractAuthenticationTokenService,
)
from app.modules.authentication.dtos.complete_login import (
    CompleteLoginRequest,
    CompleteLoginResponse,
)
from app.modules.authentication.dtos.session import CreateAdminSessionRequest
from app.modules.authentication.dtos.token import (
    CreateAuthenticationTokensRequest,
)


class CompleteLoginService(AbstractCompleteLoginService):
    def __init__(
        self,
        id_generator: AbstractIDGenerator,
        token_service: AbstractAuthenticationTokenService,
        session_service: AbstractAdminSessionService,
    ) -> None:
        self.id_generator = id_generator
        self.token_service = token_service
        self.session_service = session_service

    async def complete_login(
        self,
        payload: CompleteLoginRequest,
    ) -> CompleteLoginResponse:
        now = datetime.now(UTC)
        session_id = self.id_generator.generate()

        tokens = self.token_service.create_tokens(
            CreateAuthenticationTokensRequest(
                admin_user_id=payload.admin_user_id,
                session_id=session_id,
                issued_at=now,
            )
        )

        await self.session_service.create_session(
            CreateAdminSessionRequest(
                admin_user_id=payload.admin_user_id,
                session_id=session_id,
                tokens=tokens,
                device_name=payload.device_name,
                device_type=payload.device_type,
                browser=payload.browser,
                operating_system=payload.operating_system,
                ip_address=payload.ip_address,
                user_agent=payload.user_agent,
                issued_at=now,
            )
        )

        return CompleteLoginResponse(
            session_id=session_id,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            access_token_expires_at=tokens.access_token_expires_at,
            session_expires_at=tokens.session_expires_at,
        )
