import secrets
from datetime import UTC, datetime, timedelta

from app.core.config import Settings
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.contracts.security.token_hasher import TokenHasher
from app.modules.authentication.contracts.repositories.admin_user import (
    AbstractAdminUserRepository,
)
from app.modules.authentication.contracts.repositories.auth_challenge import (
    AbstractAuthChallengeRepository,
)
from app.modules.authentication.contracts.services.verify_password_reset import (
    AbstractVerifyPasswordResetService,
)
from app.modules.authentication.dtos.verify_password_reset import (
    VerifyPasswordResetResult,
)
from app.modules.authentication.enums import AdminUserStatus, ChallengeType
from app.modules.authentication.errors.password_reset import (
    ConsumedPasswordResetTokenError,
    ExpiredPasswordResetTokenError,
    InvalidPasswordResetTokenError,
    LockedPasswordResetTokenError,
)
from app.modules.authentication.models import AuthChallenge


class VerifyPasswordResetService(AbstractVerifyPasswordResetService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        id_generator: AbstractIDGenerator,
        token_hasher: TokenHasher,
        settings: Settings,
    ) -> None:
        self.uow = uow
        self.id_generator = id_generator
        self.token_hasher = token_hasher
        self.settings = settings

    async def verify_password_reset_token(
        self,
        token: str,
    ) -> VerifyPasswordResetResult:
        if not token or not token.strip():
            raise InvalidPasswordResetTokenError()

        now = datetime.now(UTC)

        challenge_repository = self.uow.get_repository(AbstractAuthChallengeRepository)
        admin_user_repository = self.uow.get_repository(AbstractAdminUserRepository)

        challenge = await challenge_repository.get_by_token_hash(
            self.token_hasher.hash_token(token),
            ChallengeType.PASSWORD_RESET,
            for_update=True,
        )

        if challenge is None:
            raise InvalidPasswordResetTokenError()

        if challenge.consumed_at is not None:
            raise ConsumedPasswordResetTokenError()

        if challenge.expires_at <= now:
            raise ExpiredPasswordResetTokenError()

        if challenge.failed_attempts >= challenge.max_attempts:
            raise LockedPasswordResetTokenError()

        admin_user = await admin_user_repository.get_by_id(
            challenge.admin_user_id,
            for_update=True,
        )

        if admin_user is None or admin_user.status != AdminUserStatus.ACTIVE:
            raise InvalidPasswordResetTokenError()

        if not await challenge_repository.consume(challenge.id, now):
            raise InvalidPasswordResetTokenError()

        await challenge_repository.invalidate_pending_by_user_and_type(
            admin_user.id,
            ChallengeType.ACCOUNT_RECOVERY,
            now,
        )

        recovery_token = secrets.token_urlsafe(32)
        recovery_expires_at = now + timedelta(
            minutes=self.settings.PASSWORD_RESET_RECOVERY_EXPIRE_MINUTES
        )

        challenge_repository.create(
            AuthChallenge(
                id=self.id_generator.generate(),
                admin_user_id=admin_user.id,
                challenge_type=ChallengeType.ACCOUNT_RECOVERY,
                challenge_token_hash=self.token_hasher.hash_token(recovery_token),
                challenge_data={"purpose": "password_reset"},
                expires_at=recovery_expires_at,
                max_attempts=self.settings.PASSWORD_RESET_MAX_ATTEMPTS,
            )
        )

        await self.uow.flush()

        return VerifyPasswordResetResult(
            recovery_token=recovery_token,
        )
