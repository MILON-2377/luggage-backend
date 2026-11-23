from datetime import UTC, datetime

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.security.token_hasher import TokenHasher
from app.modules.authentication.contracts.repositories.admin_session import (
    AbstractAdminSessionRepository,
)
from app.modules.authentication.contracts.services.logout import (
    AbstractLogoutService,
)
from app.modules.authentication.dtos.logout import LogoutResponse
from app.modules.authentication.enums.session_revocation_reason import (
    SessionRevocationReason,
)


class LogoutService(AbstractLogoutService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        token_hasher: TokenHasher,
    ) -> None:
        self.uow = uow
        self.token_hasher = token_hasher

    async def logout(
        self,
        refresh_token: str | None,
    ) -> LogoutResponse:
        if refresh_token and refresh_token.strip():
            repository = self.uow.get_repository(
                AbstractAdminSessionRepository
            )

            refresh_token_hash = self.token_hasher.hash_token(
                refresh_token
            )

            session = await repository.get_by_refresh_token_hash(
                refresh_token_hash,
                for_update=True,
            )

            if session is not None:
                await repository.revoke(
                    session_id=session.id,
                    revoked_at=datetime.now(UTC),
                    reason=SessionRevocationReason.USER_LOGOUT,
                )

                await self.uow.flush()

        return LogoutResponse(
            authenticated=False,
            message="Logged out successfully.",
        )