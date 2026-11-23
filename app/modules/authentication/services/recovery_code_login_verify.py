from datetime import UTC, datetime

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.security.token_hasher import TokenHasher
from app.modules.authentication.contracts.repositories import (
    AbstractAdminUserRepository,
    AbstractAuthChallengeRepository,
    AbstractAuthRecoveryCodeRepository,
)
from app.modules.authentication.contracts.services.complete_login import (
    AbstractCompleteLoginService,
)
from app.modules.authentication.contracts.services.recovery_code_login_verify import (
    AbstractRecoveryCodeLoginVerifyService,
)
from app.modules.authentication.dtos.complete_login import (
    CompleteLoginRequest,
    CompleteLoginResponse,
)
from app.modules.authentication.dtos.recovery_code_login_verify import (
    RecoveryCodeLoginVerifyRequest,
)
from app.modules.authentication.enums import AdminUserStatus, ChallengeType
from app.modules.authentication.errors.login import (
    AccountNotEligibleForLoginError,
)
from app.modules.authentication.errors.recovery_code_login_verify import (
    ConsumedRecoveryCodeLoginChallengeError,
    ExpiredRecoveryCodeLoginChallengeError,
    InvalidRecoveryCodeError,
    InvalidRecoveryCodeLoginChallengeError,
    LockedRecoveryCodeLoginChallengeError,
)


class RecoveryCodeLoginVerifyService(AbstractRecoveryCodeLoginVerifyService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        token_hasher: TokenHasher,
        complete_login_service: AbstractCompleteLoginService,
    ) -> None:
        self._uow = uow
        self._token_hasher = token_hasher
        self._complete_login_service = complete_login_service

    async def verify(
        self,
        payload: RecoveryCodeLoginVerifyRequest,
    ) -> CompleteLoginResponse:
        now = datetime.now(UTC)

        challenge_repository: AbstractAuthChallengeRepository = (
            self._uow.get_repository(AbstractAuthChallengeRepository)
        )

        user_repository: AbstractAdminUserRepository = self._uow.get_repository(
            AbstractAdminUserRepository
        )

        recovery_code_repository: AbstractAuthRecoveryCodeRepository = (
            self._uow.get_repository(AbstractAuthRecoveryCodeRepository)
        )

        challenge_token = payload.challenge_token.get_secret_value()
        challenge_token_hash = self._token_hasher.hash_token(challenge_token)

        challenge = await challenge_repository.get_by_token_hash(
            challenge_token_hash,
            ChallengeType.MFA_AUTHENTICATION,
            for_update=True,
        )

        if challenge is None:
            raise InvalidRecoveryCodeLoginChallengeError()

        if challenge.consumed_at is not None:
            raise ConsumedRecoveryCodeLoginChallengeError()

        if challenge.expires_at <= now:
            raise ExpiredRecoveryCodeLoginChallengeError()

        if challenge.failed_attempts >= challenge.max_attempts:
            raise LockedRecoveryCodeLoginChallengeError()

        challenge_data = challenge.challenge_data or {}

        if challenge_data.get(
            "purpose"
        ) != "admin_login" or "recovery_code" not in challenge_data.get(
            "available_mfa_methods", []
        ):
            raise InvalidRecoveryCodeLoginChallengeError()

        admin_user = await user_repository.get_by_id(
            challenge.admin_user_id,
            for_update=True,
        )

        if admin_user is None:
            raise InvalidRecoveryCodeLoginChallengeError()

        if admin_user.status != AdminUserStatus.ACTIVE:
            raise AccountNotEligibleForLoginError()

        recovery_code = payload.recovery_code.get_secret_value()
        recovery_code_hash = self._token_hasher.hash_token(recovery_code)

        available_code = await recovery_code_repository.get_available_by_code_hash(
            admin_user.id,
            recovery_code_hash,
            for_update=True,
        )

        if available_code is None:
            attempts = await challenge_repository.increment_failed_attempts(
                challenge.id
            )

            if attempts is not None and attempts >= challenge.max_attempts:
                raise LockedRecoveryCodeLoginChallengeError()

            raise InvalidRecoveryCodeError()

        consumed = await recovery_code_repository.consume(
            admin_user.id,
            recovery_code_hash,
            now,
        )

        if not consumed:
            attempts = await challenge_repository.increment_failed_attempts(
                challenge.id
            )

            if attempts is not None and attempts >= challenge.max_attempts:
                raise LockedRecoveryCodeLoginChallengeError()

            raise InvalidRecoveryCodeError()

        challenge_consumed = await challenge_repository.consume(
            challenge.id,
            now,
        )

        if not challenge_consumed:
            raise ConsumedRecoveryCodeLoginChallengeError()

        await self._uow.flush()

        return await self._complete_login_service.complete_login(
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
