import secrets
from datetime import UTC, datetime

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
from app.modules.authentication.contracts.services.initial_mfa_setup_authorization import (
    AbstractInitialMFASetupAuthorizationService,
)
from app.modules.authentication.dtos.initial_mfa_setup_authorization import (
    InitialMFASetupAuthorizationResult,
)
from app.modules.authentication.enums import AdminUserStatus, ChallengeType
from app.modules.authentication.errors.initial_mfa_setup_authorization import (
    InitialMFASetupAccountNotEligibleError,
    InvalidInitialMFASetupAuthorizationError,
)
from app.modules.authentication.models import AuthChallenge


class InitialMFASetupAuthorizationService(AbstractInitialMFASetupAuthorizationService):
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

    async def authorize_initial_setup(
        self,
        initial_setup_token: str,
    ) -> InitialMFASetupAuthorizationResult:
        if not initial_setup_token or not initial_setup_token.strip():
            raise InvalidInitialMFASetupAuthorizationError()

        now = datetime.now(UTC)

        challenge_repository = self.uow.get_repository(AbstractAuthChallengeRepository)
        admin_user_repository = self.uow.get_repository(AbstractAdminUserRepository)

        # The lookup is by hash of the token, so a separate verify_token
        # comparison afterwards is redundant and has been removed.
        challenge = await challenge_repository.get_by_token_hash(
            self.token_hasher.hash_token(initial_setup_token),
            ChallengeType.INITIAL_MFA_SETUP,
            for_update=True,
        )

        if challenge is None:
            raise InvalidInitialMFASetupAuthorizationError()

        if (
            challenge.consumed_at is not None
            or challenge.expires_at <= now
            or challenge.failed_attempts >= challenge.max_attempts
        ):
            raise InvalidInitialMFASetupAuthorizationError()

        admin_user = await admin_user_repository.get_by_id(
            challenge.admin_user_id,
            for_update=True,
        )

        if admin_user is None:
            raise InvalidInitialMFASetupAuthorizationError()

        if admin_user.status != AdminUserStatus.PENDING_MFA_SETUP:
            raise InitialMFASetupAccountNotEligibleError()

        admin_user_id = admin_user.id

        if not await challenge_repository.consume(challenge.id, now):
            raise InvalidInitialMFASetupAuthorizationError()

        # Only one live enrollment session per user: invalidate older ones
        # so repeated authorizations don't accumulate valid tokens.
        await challenge_repository.invalidate_pending_by_user_and_type(
            admin_user_id,
            ChallengeType.MFA_ENROLLMENT_SESSION,
            now,
        )

        enrollment_token = secrets.token_urlsafe(32)
        enrollment_expires_at = now + self.settings.MFA_ENROLLMENT_SESSION_TTL

        challenge_repository.create(
            AuthChallenge(
                id=self.id_generator.generate(),
                admin_user_id=admin_user_id,
                challenge_type=ChallengeType.MFA_ENROLLMENT_SESSION,
                challenge_token_hash=self.token_hasher.hash_token(enrollment_token),
                challenge_data={"purpose": "initial_mfa_enrollment"},
                expires_at=enrollment_expires_at,
                max_attempts=self.settings.MFA_ENROLLMENT_MAX_ATTEMPTS,
            )
        )

        await self.uow.flush()

        return InitialMFASetupAuthorizationResult(
            admin_user_id=admin_user_id,
            enrollment_token=enrollment_token,
            expires_at=enrollment_expires_at,
        )
