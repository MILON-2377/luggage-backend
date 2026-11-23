from datetime import UTC, datetime
from typing import Any

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.security.secret_encryptor import SecretEncryptor
from app.core.contracts.security.token_hasher import TokenHasher
from app.core.contracts.security.totp_provider import TOTPProvider
from app.modules.authentication.contracts.repositories import (
    AbstractAdminTotpCredentialRepository,
    AbstractAdminUserRepository,
    AbstractAuthChallengeRepository,
)
from app.modules.authentication.contracts.services.complete_login import (
    AbstractCompleteLoginService,
)
from app.modules.authentication.contracts.services.totp_login_verify import (
    AbstractTotpLoginVerifyService,
)
from app.modules.authentication.dtos.complete_login import CompleteLoginRequest
from app.modules.authentication.dtos.totp_login_verify import (
    TotpLoginVerifyRequest,
)
from app.modules.authentication.enums import AdminUserStatus, ChallengeType
from app.modules.authentication.errors.login import (
    AccountNotEligibleForLoginError,
)
from app.modules.authentication.errors.totp_login_verify import (
    ConsumedTotpLoginChallengeError,
    ExpiredTotpLoginChallengeError,
    InvalidTotpCodeError,
    InvalidTotpLoginChallengeError,
    LockedTotpLoginChallengeError,
    TotpCredentialNotFoundError,
)


class TotpLoginVerifyService(AbstractTotpLoginVerifyService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        token_hasher: TokenHasher,
        totp_provider: TOTPProvider,
        secret_encryptor: SecretEncryptor,
        complete_login_service: AbstractCompleteLoginService,
    ) -> None:
        self.uow = uow
        self.token_hasher = token_hasher
        self.totp_provider = totp_provider
        self.secret_encryptor = secret_encryptor
        self.complete_login_service = complete_login_service

    async def verify(
        self,
        payload: TotpLoginVerifyRequest,
    ):
        now = datetime.now(UTC)

        challenge_repository = self.uow.get_repository(
            AbstractAuthChallengeRepository
        )
        user_repository = self.uow.get_repository(
            AbstractAdminUserRepository
        )
        totp_repository = self.uow.get_repository(
            AbstractAdminTotpCredentialRepository
        )

        challenge_token = payload.challenge_token.get_secret_value()
        challenge_token_hash = self.token_hasher.hash_token(challenge_token)

        challenge = await challenge_repository.get_by_token_hash(
            challenge_token_hash,
            ChallengeType.MFA_AUTHENTICATION,
            for_update=True,
        )

        if challenge is None:
            raise InvalidTotpLoginChallengeError()

        if challenge.consumed_at is not None:
            raise ConsumedTotpLoginChallengeError()

        if challenge.expires_at <= now:
            raise ExpiredTotpLoginChallengeError()

        if challenge.failed_attempts >= challenge.max_attempts:
            raise LockedTotpLoginChallengeError()

        challenge_data: dict[str, Any] = challenge.challenge_data or {}

        if (
            challenge_data.get("purpose") != "admin_login"
            or "totp" not in challenge_data.get(
                "available_mfa_methods",
                [],
            )
        ):
            raise InvalidTotpLoginChallengeError()

        admin_user = await user_repository.get_by_id(
            challenge.admin_user_id,
            for_update=True,
        )

        if (
            admin_user is None
            or admin_user.status != AdminUserStatus.ACTIVE
        ):
            raise AccountNotEligibleForLoginError()

        credential = await totp_repository.get_active_by_admin_user_id(
            admin_user.id,
            for_update=True,
        )

        if credential is None:
            raise TotpCredentialNotFoundError()

        if (
            credential.algorithm != "SHA1"
            or credential.digits != 6
        ):
            raise AccountNotEligibleForLoginError()

        secret = self.secret_encryptor.decrypt(
            credential.secret_encrypted
        )

        time_step = int(now.timestamp()) // credential.period_seconds

        code = payload.code.get_secret_value()

        is_valid = self.totp_provider.verify_code_for_time_step(
            secret=secret,
            code=code,
            time_step=time_step,
            period_seconds=credential.period_seconds,
        )

        if not is_valid:
            failed_attempts = await challenge_repository.increment_failed_attempts(
                challenge.id
            )
            await self.uow.flush()

            if (
                failed_attempts is not None
                and failed_attempts >= challenge.max_attempts
            ):
                raise LockedTotpLoginChallengeError()

            raise InvalidTotpCodeError()

        recorded = await totp_repository.record_successful_use(
            credential_id=credential.id,
            time_step=time_step,
            used_at=now,
        )

        if not recorded:
            raise InvalidTotpCodeError()

        consumed = await challenge_repository.consume(
            challenge.id,
            now,
        )

        if not consumed:
            raise ConsumedTotpLoginChallengeError()

        await self.uow.flush()

        return await self.complete_login_service.complete_login(
            CompleteLoginRequest(
                admin_user_id=admin_user.id,
                device_name=None,
                device_type=None,
                browser=None,
                operating_system=None,
                ip_address=None,
                user_agent=None,
            )
        )