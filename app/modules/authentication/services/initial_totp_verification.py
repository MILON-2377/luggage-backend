import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from app.core.config import Settings
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.contracts.security.secret_encryptor import SecretEncryptor
from app.core.contracts.security.totp_provider import TOTPProvider
from app.integrations.security.sha256_token_hasher import TokenHasher
from app.modules.authentication.contracts.repositories.admin_totp_credential import (
    AbstractAdminTotpCredentialRepository,
)
from app.modules.authentication.contracts.repositories.admin_user import (
    AbstractAdminUserRepository,
)
from app.modules.authentication.contracts.repositories.auth_challenge import (
    AbstractAuthChallengeRepository,
)
from app.modules.authentication.contracts.repositories.auth_recovery_code import (
    AbstractAuthRecoveryCodeRepository,
)
from app.modules.authentication.contracts.services.initial_totp_verification import (
    AbstractInitialTOTPVerificationService,
)
from app.modules.authentication.dtos.initial_totp_verification import (
    InitialTOTPVerificationResult,
)
from app.modules.authentication.enums.admin_user_status import AdminUserStatus
from app.modules.authentication.enums.challenge_type import ChallengeType
from app.modules.authentication.errors.initial_totp_verification import (
    ConsumedMFAEnrollmentSessionError,
    ExpiredMFAEnrollmentSessionError,
    InvalidMFAEnrollmentSessionError,
    InvalidTOTPVerificationCodeError,
    LockedMFAEnrollmentSessionError,
    MFAEnrollmentAccountNotEligibleError,
    TOTPCodeAlreadyUsedError,
    TOTPEnrollmentAlreadyVerifiedError,
    TOTPEnrollmentNotFoundError,
    TOTPVerificationConflictError,
)
from app.modules.authentication.models import AuthRecoveryCode


class InitialTOTPVerificationService(AbstractInitialTOTPVerificationService):
    RECOVERY_CODE_COUNT = 10
    RECOVERY_CODE_BYTES = 9
    ENROLLMENT_PURPOSE = "initial_mfa_enrollment"

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        id_generator: AbstractIDGenerator,
        token_hasher: TokenHasher,
        secret_encryptor: SecretEncryptor,
        totp_provider: TOTPProvider,
        settings: Settings,
    ) -> None:
        self.uow = uow
        self.id_generator = id_generator
        self.token_hasher = token_hasher
        self.secret_encryptor = secret_encryptor
        self.totp_provider = totp_provider
        self.settings = settings

    async def verify(
        self,
        enrollment_token: str,
        code: str,
    ) -> InitialTOTPVerificationResult:
        if not enrollment_token or not enrollment_token.strip():
            raise InvalidMFAEnrollmentSessionError()

        now = datetime.now(UTC)

        challenge_repository = self.uow.get_repository(AbstractAuthChallengeRepository)
        admin_user_repository = self.uow.get_repository(AbstractAdminUserRepository)
        credential_repository = self.uow.get_repository(
            AbstractAdminTotpCredentialRepository
        )
        recovery_code_repository = self.uow.get_repository(
            AbstractAuthRecoveryCodeRepository
        )

        challenge = await challenge_repository.get_by_token_hash(
            self.token_hasher.hash_token(enrollment_token),
            ChallengeType.MFA_ENROLLMENT_SESSION,
            for_update=True,
        )

        if challenge is None:
            raise InvalidMFAEnrollmentSessionError()

        if challenge.consumed_at is not None:
            raise ConsumedMFAEnrollmentSessionError()

        if challenge.expires_at <= now:
            raise ExpiredMFAEnrollmentSessionError()

        if challenge.failed_attempts >= challenge.max_attempts:
            raise LockedMFAEnrollmentSessionError()

        if (
            not challenge.challenge_data
            or challenge.challenge_data.get("purpose") != self.ENROLLMENT_PURPOSE
        ):
            raise InvalidMFAEnrollmentSessionError()

        admin_user = await admin_user_repository.get_by_id(
            challenge.admin_user_id,
            for_update=True,
        )

        if admin_user is None:
            raise InvalidMFAEnrollmentSessionError()

        if admin_user.status != AdminUserStatus.PENDING_MFA_SETUP:
            raise MFAEnrollmentAccountNotEligibleError()

        credential = await credential_repository.get_unrevoked_by_admin_user_id(
            admin_user.id,
            for_update=True,
        )

        if credential is None:
            raise TOTPEnrollmentNotFoundError()

        if credential.verified_at is not None:
            raise TOTPEnrollmentAlreadyVerifiedError()

        if credential.revoked_at is not None:
            raise TOTPEnrollmentNotFoundError()

        if not code.isdigit() or len(code) != credential.digits:
            await self._record_failed_attempt(challenge_repository, challenge.id)
            raise InvalidTOTPVerificationCodeError()

        secret = self.secret_encryptor.decrypt(credential.secret_encrypted)

        time_step = int(now.timestamp()) // credential.period_seconds

        if not self.totp_provider.verify_code_for_time_step(
            secret=secret,
            code=code,
            time_step=time_step,
            period_seconds=credential.period_seconds,
        ):
            await self._record_failed_attempt(challenge_repository, challenge.id)
            raise InvalidTOTPVerificationCodeError()

        marked_verified = await credential_repository.mark_verified(
            credential.id,
            now,
        )

        if not marked_verified:
            raise TOTPVerificationConflictError()

        recorded_use = await credential_repository.record_successful_use(
            credential.id,
            time_step,
            now,
        )

        if not recorded_use:
            raise TOTPCodeAlreadyUsedError()

        await recovery_code_repository.revoke_all_available_by_admin_user_id(
            admin_user.id,
            now,
        )

        recovery_codes = self._generate_recovery_codes()

        for recovery_code in recovery_codes:
            recovery_code_repository.create(
                AuthRecoveryCode(
                    id=self.id_generator.generate(),
                    admin_user_id=admin_user.id,
                    code_hash=hashlib.sha256(recovery_code.encode("utf-8")).hexdigest(),
                )
            )

        consumed = await challenge_repository.consume(challenge.id, now)

        if not consumed:
            raise TOTPVerificationConflictError()

        admin_user.status = AdminUserStatus.ACTIVE

        await self.uow.flush()

        return InitialTOTPVerificationResult(
            admin_user_id=admin_user.id,
            recovery_codes=tuple(recovery_codes),
        )

    async def _record_failed_attempt(
        self,
        challenge_repository: AbstractAuthChallengeRepository,
        challenge_id: uuid.UUID,
    ) -> None:
        updated_attempts = await challenge_repository.increment_failed_attempts(
            challenge_id
        )

        if updated_attempts is None:
            raise LockedMFAEnrollmentSessionError()

    def _generate_recovery_codes(self) -> list[str]:
        return [
            secrets.token_urlsafe(self.RECOVERY_CODE_BYTES)
            for _ in range(self.RECOVERY_CODE_COUNT)
        ]
