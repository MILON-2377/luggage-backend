import asyncio
from datetime import UTC, datetime

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.security.password_hasher import PasswordHasher
from app.core.contracts.security.token_hasher import TokenHasher
from app.core.errors.base import ValidationError
from app.modules.authentication.contracts.repositories import (
    AbstractAdminUserProfileRepository,
    AbstractAdminUserRepository,
    AbstractAuthChallengeRepository,
)
from app.modules.authentication.contracts.services.invitation_acceptance import (
    AbstractInvitationAcceptanceService,
)
from app.modules.authentication.dtos.accept_invitation import AcceptInvitationDTO
from app.modules.authentication.enums import AdminUserStatus, ChallengeType
from app.modules.authentication.errors.invitation import (
    AccountNotEligibleForInvitationError,
    InvitationAlreadyUsedError,
    InvitationAttemptsExceededError,
    InvitationExpiredError,
    InvitationNotFoundError,
)
from app.modules.authentication.models import AuthChallenge


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


class InvitationAcceptanceService(AbstractInvitationAcceptanceService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        token_hasher: TokenHasher,
        password_hasher: PasswordHasher,
    ) -> None:
        self.uow = uow
        self.token_hasher = token_hasher
        self.password_hasher = password_hasher

    async def accept_invitation(
        self,
        data: AcceptInvitationDTO,
    ) -> None:
        first_name = data.first_name.strip()
        last_name = data.last_name.strip()

        if not first_name or not last_name:
            raise ValidationError("First name and last name are required.")

        if not data.password:
            raise ValidationError("Password is required.")

        timezone = _clean_optional(data.timezone)
        language = _clean_optional(data.language)

        challenge_repository = self.uow.get_repository(AbstractAuthChallengeRepository)
        user_repository = self.uow.get_repository(AbstractAdminUserRepository)
        profile_repository = self.uow.get_repository(AbstractAdminUserProfileRepository)

        # Hash the password before taking any row locks: password hashing is
        # slow and must not hold locks (or block the event loop).
        password_hash = await asyncio.to_thread(
            self.password_hasher.hash_password,
            data.password,
        )

        challenge = await challenge_repository.get_by_token_hash(
            self.token_hasher.hash_token(data.invitation_token),
            ChallengeType.ACCOUNT_INVITATION,
            for_update=True,
        )

        if challenge is None:
            raise InvitationNotFoundError

        now = datetime.now(UTC)
        self._validate_challenge(challenge, now)

        admin_user = await user_repository.get_by_id(
            challenge.admin_user_id,
            for_update=True,
        )

        if (
            admin_user is None
            or admin_user.status != AdminUserStatus.INVITED
            or admin_user.password_hash is not None
        ):
            raise AccountNotEligibleForInvitationError

        profile = await profile_repository.get_by_admin_user_id(admin_user.id)

        if profile is None:
            raise AccountNotEligibleForInvitationError

        # Atomic single-use guard, independent of the row lock above.
        if not await challenge_repository.consume(challenge.id, now):
            raise InvitationAlreadyUsedError

        admin_user.password_hash = password_hash
        admin_user.password_changed_at = now
        admin_user.email_verified_at = now
        admin_user.status = AdminUserStatus.ACTIVE

        profile.first_name = first_name
        profile.last_name = last_name
        profile.display_name = _clean_optional(data.display_name)
        profile.phone = _clean_optional(data.phone)
        profile.job_title = _clean_optional(data.job_title)
        profile.department = _clean_optional(data.department)

        # timezone/language are NOT NULL with defaults: only overwrite when given.
        if timezone is not None:
            profile.timezone = timezone
        if language is not None:
            profile.language = language

        await self.uow.flush()
        await self.uow.commit()

    @staticmethod
    def _validate_challenge(
        challenge: AuthChallenge,
        now: datetime,
    ) -> None:
        if challenge.consumed_at is not None:
            raise InvitationAlreadyUsedError

        if challenge.expires_at <= now:
            raise InvitationExpiredError

        if challenge.failed_attempts >= challenge.max_attempts:
            raise InvitationAttemptsExceededError
