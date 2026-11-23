import logging
import secrets
from datetime import UTC, datetime, timedelta

from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Settings
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.contracts.security.password_hasher import PasswordHasher
from app.core.contracts.security.token_hasher import TokenHasher
from app.modules.authentication.contracts.repositories import (
    AbstractAdminTotpCredentialRepository,
    AbstractAdminUserRepository,
    AbstractAdminWebauthnCredentialRepository,
    AbstractAuthChallengeRepository,
    AbstractAuthRecoveryCodeRepository,
)
from app.modules.authentication.contracts.services.login import (
    AbstractLoginService,
)
from app.modules.authentication.dtos.login import LoginRequest, LoginResponse
from app.modules.authentication.enums import AdminUserStatus, ChallengeType
from app.modules.authentication.errors.login import (
    AccountLockedError,
    AccountNotEligibleForLoginError,
    InvalidLoginCredentialsError,
)
from app.modules.authentication.models import AuthChallenge

logger = logging.getLogger(__name__)


class LoginService(AbstractLoginService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        id_generator: AbstractIDGenerator,
        password_hasher: PasswordHasher,
        token_hasher: TokenHasher,
        settings: Settings,
    ) -> None:
        self.uow = uow
        self.id_generator = id_generator
        self.password_hasher = password_hasher
        self.token_hasher = token_hasher
        self.settings = settings

        self._max_failed_attempts = settings.ADMIN_LOGIN_MAX_FAILED_ATTEMPTS
        self._lockout_duration = timedelta(minutes=settings.ADMIN_LOGIN_LOCKOUT_MINUTES)

        self._dummy_password_hash = self.password_hasher.hash_password(
            secrets.token_urlsafe(32)
        )

    async def login(self, payload: LoginRequest) -> LoginResponse:
        now = datetime.now(UTC)
        password = payload.password.get_secret_value()

        admin_user_repository = self.uow.get_repository(AbstractAdminUserRepository)
        challenge_repository = self.uow.get_repository(AbstractAuthChallengeRepository)
        totp_repository = self.uow.get_repository(AbstractAdminTotpCredentialRepository)
        webauthn_repository = self.uow.get_repository(
            AbstractAdminWebauthnCredentialRepository
        )
        recovery_code_repository = self.uow.get_repository(
            AbstractAuthRecoveryCodeRepository
        )

        email = str(payload.email).strip().lower()

        admin_user = await admin_user_repository.get_by_email(
            email,
            for_update=True,
        )

        if admin_user is None:
            self._verify_password(password, self._dummy_password_hash)
            raise InvalidLoginCredentialsError()

        if admin_user.locked_until is not None:
            if admin_user.locked_until > now:
                raise AccountLockedError()

            await admin_user_repository.reset_failed_login_attempts(admin_user.id)
            await self.uow.flush()
            admin_user = await admin_user_repository.get_by_id(
                admin_user.id,
                for_update=True,
            )

            if admin_user is None:
                raise InvalidLoginCredentialsError()

        if admin_user.password_hash is None:
            self._verify_password(password, self._dummy_password_hash)
            raise AccountNotEligibleForLoginError()

        password_valid = self._verify_password(
            password,
            admin_user.password_hash,
        )

        if not password_valid:
            locked_until = now + self._lockout_duration

            failed_attempts = await admin_user_repository.record_failed_login(
                admin_user.id,
                max_attempts=self._max_failed_attempts,
                locked_until=locked_until,
            )

            await self.uow.commit()

            if (
                failed_attempts is not None
                and failed_attempts >= self._max_failed_attempts
            ):
                raise AccountLockedError()

            raise InvalidLoginCredentialsError()

        if admin_user.status != AdminUserStatus.ACTIVE:
            raise AccountNotEligibleForLoginError()

        totp_credentials = await totp_repository.get_active_by_admin_user_id(
            admin_user.id
        )
        webauthn_credentials = await webauthn_repository.get_active_by_admin_user_id(
            admin_user.id
        )
        recovery_codes = await recovery_code_repository.get_available_by_admin_user_id(
            admin_user.id
        )

        available_mfa_methods: list[str] = []

        if webauthn_credentials:
            available_mfa_methods.append("passkey")

        if totp_credentials:
            available_mfa_methods.append("totp")

        if recovery_codes:
            available_mfa_methods.append("recovery_code")

        if not available_mfa_methods:
            raise AccountNotEligibleForLoginError()

        challenge_token = secrets.token_urlsafe(32)
        challenge_token_hash = self.token_hasher.hash_token(challenge_token)

        logger.info(
            "Login challenge generated: token_length=%s hash_length=%s",
            len(challenge_token),
            len(challenge_token_hash),
        )

        challenge_expires_at = now + timedelta(
            seconds=self.settings.WEBAUTHN_CHALLENGE_EXPIRE_SECONDS
        )

        await challenge_repository.invalidate_pending_by_user_and_type(
            admin_user.id,
            ChallengeType.MFA_AUTHENTICATION,
            now,
        )

        challenge_repository.create(
            AuthChallenge(
                id=self.id_generator.generate(),
                admin_user_id=admin_user.id,
                challenge_type=ChallengeType.MFA_AUTHENTICATION,
                challenge_token_hash=challenge_token_hash,
                challenge_data={
                    "purpose": "admin_login",
                    "available_mfa_methods": available_mfa_methods,
                },
                expires_at=challenge_expires_at,
            )
        )

        await admin_user_repository.reset_failed_login_attempts(admin_user.id)

        await self.uow.flush()

        logger.info(
            "Admin login challenge created",
            extra={
                "admin_user_id": str(admin_user.id),
                "challenge_expires_at": challenge_expires_at.isoformat(),
                "available_mfa_methods": available_mfa_methods,
            },
        )

        return LoginResponse(
            challenge_token=challenge_token,
            expires_at=challenge_expires_at,
            available_mfa_methods=available_mfa_methods,
        )

    def _verify_password(
        self,
        password: str,
        password_hash: str,
    ) -> bool:
        try:
            return self.password_hasher.verify_password(
                password,
                password_hash,
            )
        except (InvalidHashError, VerificationError):
            return False
