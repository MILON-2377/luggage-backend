import secrets
from datetime import UTC, datetime, timedelta

from app.core.config import Settings
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.security.jwt_provider import AbstractJWTProvider
from app.core.contracts.security.token_hasher import TokenHasher
from app.modules.authentication.contracts.repositories import (
    AbstractAdminSessionRepository,
    AbstractAdminUserRepository,
)
from app.modules.authentication.contracts.services.refresh import (
    AbstractRefreshService,
)
from app.modules.authentication.dtos.refresh import RefreshTokensDTO
from app.modules.authentication.enums import AdminUserStatus
from app.modules.authentication.errors.refresh import InvalidRefreshTokenError


class RefreshService(AbstractRefreshService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        jwt_provider: AbstractJWTProvider,
        token_hasher: TokenHasher,
        settings: Settings,
    ) -> None:
        self.uow = uow
        self.jwt_provider = jwt_provider
        self.token_hasher = token_hasher
        self.settings = settings

    async def refresh(
        self,
        refresh_token: str,
    ) -> RefreshTokensDTO:
        if not refresh_token or not refresh_token.strip():
            raise InvalidRefreshTokenError()

        now = datetime.now(UTC)
        refresh_token_hash = self.token_hasher.hash_token(refresh_token)

        session_repository = self.uow.get_repository(AbstractAdminSessionRepository)
        user_repository = self.uow.get_repository(AbstractAdminUserRepository)

        session = await session_repository.get_by_refresh_token_hash(
            refresh_token_hash,
            for_update=True,
        )

        if (
            session is None
            or session.revoked_at is not None
            or session.expires_at <= now
        ):
            raise InvalidRefreshTokenError()

        admin_user = await user_repository.get_by_id(
            session.admin_user_id,
        )

        if admin_user is None or admin_user.status != AdminUserStatus.ACTIVE:
            raise InvalidRefreshTokenError()

        new_refresh_token = secrets.token_urlsafe(64)
        new_refresh_token_hash = self.token_hasher.hash_token(new_refresh_token)

        access_token = self.jwt_provider.create_access_token(
            user_id=session.admin_user_id,
            session_id=session.id,
        )

        session.refresh_token_hash = new_refresh_token_hash
        session.last_activity_at = now

        await self.uow.flush()

        return RefreshTokensDTO(
            access_token=access_token,
            refresh_token=new_refresh_token,
            access_token_expires_at=now
            + timedelta(minutes=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            session_expires_at=session.expires_at,
        )
