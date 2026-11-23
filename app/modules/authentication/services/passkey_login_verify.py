from datetime import UTC, datetime

from webauthn.helpers import base64url_to_bytes

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.security.passkey_provider import PasskeyProvider
from app.core.contracts.security.token_hasher import TokenHasher
from app.modules.authentication.contracts.repositories import (
    AbstractAdminWebauthnCredentialRepository,
    AbstractAuthChallengeRepository,
)
from app.modules.authentication.contracts.services.complete_login import (
    AbstractCompleteLoginService,
)
from app.modules.authentication.contracts.services.passkey_login_verify import (
    AbstractPasskeyLoginVerifyService,
)
from app.modules.authentication.dtos.complete_login import (
    CompleteLoginRequest,
    CompleteLoginResponse,
)
from app.modules.authentication.dtos.passkey_login_verify import (
    PasskeyLoginVerifyRequest,
)
from app.modules.authentication.enums import ChallengeType
from app.modules.authentication.errors.passkey_login import (
    InvalidPasskeyLoginChallengeError,
)
from app.modules.authentication.errors.passkey_login_verify import (
    ConsumedPasskeyLoginChallengeError,
    ExpiredPasskeyLoginChallengeError,
    InvalidPasskeyAssertionError,
    LockedPasskeyLoginChallengeError,
    PasskeyCredentialNotFoundError,
)


class PasskeyLoginVerifyService(AbstractPasskeyLoginVerifyService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        token_hasher: TokenHasher,
        passkey_provider: PasskeyProvider,
        complete_login_service: AbstractCompleteLoginService,
    ) -> None:
        self.uow = uow
        self.token_hasher = token_hasher
        self.passkey_provider = passkey_provider
        self.complete_login_service = complete_login_service

    async def verify(
        self,
        payload: PasskeyLoginVerifyRequest,
    ) -> CompleteLoginResponse:
        now = datetime.now(UTC)

        challenge_repository = self.uow.get_repository(
            AbstractAuthChallengeRepository
        )
        credential_repository = self.uow.get_repository(
            AbstractAdminWebauthnCredentialRepository
        )

        challenge_token = payload.challenge_token.get_secret_value()
        challenge_hash = self.token_hasher.hash_token(challenge_token)

        auth_challenge = await challenge_repository.get_by_token_hash(
            challenge_hash,
            ChallengeType.MFA_AUTHENTICATION,
            for_update=True,
        )

        if auth_challenge is None:
            raise InvalidPasskeyLoginChallengeError()

        if auth_challenge.consumed_at is not None:
            raise ConsumedPasskeyLoginChallengeError()

        if auth_challenge.expires_at <= now:
            raise ExpiredPasskeyLoginChallengeError()

        if auth_challenge.failed_attempts >= auth_challenge.max_attempts:
            raise LockedPasskeyLoginChallengeError()

        challenge_data = auth_challenge.challenge_data or {}

        if challenge_data.get("purpose") != "admin_login":
            raise InvalidPasskeyLoginChallengeError()

        if "passkey" not in challenge_data.get(
            "available_mfa_methods", []
        ):
            raise InvalidPasskeyLoginChallengeError()

        expected_challenge_value = challenge_data.get(
            "webauthn_challenge"
        )

        if not expected_challenge_value:
            raise InvalidPasskeyLoginChallengeError()

        credential_data = payload.credential

        credential_id_value = (
            credential_data.get("rawId")
            or credential_data.get("id")
        )

        if not credential_id_value:
            raise InvalidPasskeyAssertionError()

        try:
            credential_id = base64url_to_bytes(credential_id_value)
        except (TypeError, ValueError):
            raise InvalidPasskeyAssertionError() from None

        credential = await credential_repository.get_by_credential_id(
            credential_id,
            for_update=True,
        )

        if (
            credential is None
            or credential.revoked_at is not None
            or credential.admin_user_id != auth_challenge.admin_user_id
        ):
            raise PasskeyCredentialNotFoundError()

        try:
            verification = self.passkey_provider.verify_authentication(
                credential=credential_data,
                expected_challenge=base64url_to_bytes(
                    expected_challenge_value
                ),
                credential_public_key=credential.public_key,
                credential_current_sign_count=credential.sign_count,
            )
        except Exception:
            await challenge_repository.increment_failed_attempts(
                auth_challenge.id
            )
            await self.uow.flush()
            raise InvalidPasskeyAssertionError() from None

        credential.sign_count = verification.new_sign_count
        credential.last_used_at = now

        if hasattr(verification, "credential_device_type"):
            credential.backup_eligible = (
                verification.credential_device_type == "multi_device"
            )

        if hasattr(verification, "credential_backed_up"):
            credential.backup_state = verification.credential_backed_up

        await challenge_repository.consume(
            auth_challenge.id,
            now,
        )

        await self.uow.flush()

        return await self.complete_login_service.complete_login(
            CompleteLoginRequest(
                admin_user_id=auth_challenge.admin_user_id,
            )
        )