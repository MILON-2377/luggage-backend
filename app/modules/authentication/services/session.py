from datetime import UTC, datetime

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.modules.authentication.contracts.repositories import (
    AbstractAdminSessionRepository,
)
from app.modules.authentication.contracts.services.session import (
    AbstractAdminSessionService,
)
from app.modules.authentication.dtos.session import (
    CreateAdminSessionRequest,
    CreateAdminSessionResponse,
)
from app.modules.authentication.enums import SessionRevocationReason
from app.modules.authentication.models import AdminSession


class AdminSessionService(AbstractAdminSessionService):
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self.uow = uow

    async def create_session(
        self,
        payload: CreateAdminSessionRequest,
    ) -> CreateAdminSessionResponse:
        repository = self.uow.get_repository(
            AbstractAdminSessionRepository
        )

        now = datetime.now(UTC)

        await repository.revoke_all_active_by_admin_user_id(
            admin_user_id=payload.admin_user_id,
            revoked_at=now,
            reason=SessionRevocationReason.NEW_LOGIN,
        )

        session = AdminSession(
            id=payload.session_id,
            admin_user_id=payload.admin_user_id,
            refresh_token_hash=payload.tokens.refresh_token_hash,
            device_name=payload.device_name,
            device_type=payload.device_type,
            browser=payload.browser,
            operating_system=payload.operating_system,
            ip_address=payload.ip_address,
            user_agent=payload.user_agent,
            expires_at=payload.tokens.session_expires_at,
        )

        repository.create(session)

        await self.uow.flush()

        return CreateAdminSessionResponse(
            session_id=session.id,
            expires_at=session.expires_at,
        )