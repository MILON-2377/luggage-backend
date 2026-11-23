import logging
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
from app.modules.authentication.contracts.services.initial_totp_enrollment import (
    AbstractInitialTOTPEnrollmentService,
)
from app.modules.authentication.dtos.totp_enrollment import TOTPEnrollmentResult
from app.modules.authentication.enums.admin_user_status import AdminUserStatus
from app.modules.authentication.enums.challenge_type import ChallengeType
from app.modules.authentication.errors.totp_enrollment import (
    ConsumedMFAEnrollmentSessionError,
    ExpiredMFAEnrollmentSessionError,
    InvalidMFAEnrollmentSessionError,
    LockedMFAEnrollmentSessionError,
    MFAEnrollmentAccountNotEligibleError,
    TOTPAlreadyVerifiedError,
)
from app.modules.authentication.models import AdminTotpCredential

logger = logging.getLogger(__name__)

class InitialTOTPEnrollmentService(AbstractInitialTOTPEnrollmentService):
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

    async def enroll(
        self,
        enrollment_token: str,
    ) -> TOTPEnrollmentResult:
        if not enrollment_token or not enrollment_token.strip():
            raise InvalidMFAEnrollmentSessionError()

        now = datetime.now(UTC)

        challenge_repository = self.uow.get_repository(AbstractAuthChallengeRepository)
        admin_user_repository = self.uow.get_repository(AbstractAdminUserRepository)
        credential_repository = self.uow.get_repository(
            AbstractAdminTotpCredentialRepository
        )

        challenge = await challenge_repository.get_by_token_hash(
            self.token_hasher.hash_token(enrollment_token),
            ChallengeType.MFA_ENROLLMENT_SESSION,
            for_update=True,
        )

        if challenge is None:
            logger.warning("MFA enrollment failed: challenge not found")
            raise InvalidMFAEnrollmentSessionError()

        if challenge.consumed_at is not None:
            logger.warning(
                    "MFA enrollment failed: challenge already consumed "
                    "challenge_id=%s consumed_at=%s",
                    challenge.id,
                    challenge.consumed_at,
                )
            raise ConsumedMFAEnrollmentSessionError()

        if challenge.expires_at <= now:
            logger.warning(
        "MFA enrollment failed: challenge expired "
        "challenge_id=%s expires_at=%s",
        challenge.id,
        challenge.expires_at,
    )
            raise ExpiredMFAEnrollmentSessionError()

        if challenge.failed_attempts >= challenge.max_attempts:
            logger.warning(
        "MFA enrollment failed: challenge locked "
        "challenge_id=%s failed_attempts=%s max_attempts=%s",
        challenge.id,
        challenge.failed_attempts,
        challenge.max_attempts,
    )
            raise LockedMFAEnrollmentSessionError()

        if (
            not challenge.challenge_data
            or challenge.challenge_data.get("purpose") != "initial_mfa_enrollment"
        ):
            logger.warning(
        "MFA enrollment failed: invalid challenge purpose "
        "challenge_id=%s purpose=%s",
        challenge.id,
        (challenge.challenge_data or {}).get("purpose"),
    )
            raise InvalidMFAEnrollmentSessionError()

        admin_user = await admin_user_repository.get_by_id(
            challenge.admin_user_id,
            for_update=True,
        )

        if admin_user is None:
            logger.warning(
        "MFA enrollment failed: administrator not found "
        "challenge_id=%s",
        challenge.id,
    )
            raise InvalidMFAEnrollmentSessionError()

        if admin_user.status != AdminUserStatus.PENDING_MFA_SETUP:
            logger.warning(
        "MFA enrollment failed: administrator status mismatch "
        "admin_user_id=%s status=%s expected=%s",
        admin_user.id,
        admin_user.status,
        AdminUserStatus.PENDING_MFA_SETUP,
    )
            raise MFAEnrollmentAccountNotEligibleError()

        credential = await credential_repository.get_unrevoked_by_admin_user_id(
            admin_user.id,
            for_update=True,
        )

        if credential is not None and credential.verified_at is not None:
            logger.warning(
        "MFA enrollment failed: TOTP already verified "
        "admin_user_id=%s credential_id=%s verified_at=%s",
        admin_user.id,
        credential.id,
        credential.verified_at,
    )
            raise TOTPAlreadyVerifiedError()

        secret = self.totp_provider.generate_secret()

        provisioning_uri = self.totp_provider.generate_provisioning_uri(
            secret=secret,
            account_name=admin_user.email,
            issuer_name=self.settings.APP_NAME,
        )

        encrypted_secret = self.secret_encryptor.encrypt(secret)

        if credential is None:
            credential_repository.create(
                AdminTotpCredential(
                    id=self.id_generator.generate(),
                    admin_user_id=admin_user.id,
                    secret_encrypted=encrypted_secret,
                    algorithm="SHA1",
                    digits=6,
                    period_seconds=30,
                )
            )
        else:
            credential.secret_encrypted = encrypted_secret
            credential.algorithm = "SHA1"
            credential.digits = 6
            credential.period_seconds = 30
            credential.last_used_time_step = None
            credential.last_used_at = None

        await self.uow.flush()

        return TOTPEnrollmentResult(
            admin_user_id=admin_user.id,
            secret=secret,
            provisioning_uri=provisioning_uri,
            expires_at=challenge.expires_at,
        )
