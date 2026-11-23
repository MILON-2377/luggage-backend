import json
import logging
from datetime import UTC, datetime

from webauthn.helpers import bytes_to_base64url, options_to_json

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.security.passkey_provider import PasskeyProvider
from app.core.contracts.security.token_hasher import TokenHasher
from app.modules.authentication.contracts.repositories import (
    AbstractAdminUserRepository,
    AbstractAdminWebauthnCredentialRepository,
    AbstractAuthChallengeRepository,
)
from app.modules.authentication.contracts.services.passkey_login import (
    AbstractPasskeyLoginOptionsService,
)
from app.modules.authentication.dtos.passkey_login import (
    PasskeyLoginOptionsRequest,
    PasskeyLoginOptionsResponse,
)
from app.modules.authentication.enums import AdminUserStatus, ChallengeType
from app.modules.authentication.errors.passkey_login import (
    ConsumedPasskeyLoginChallengeError,
    ExpiredPasskeyLoginChallengeError,
    InvalidPasskeyLoginChallengeError,
    LockedPasskeyLoginChallengeError,
    PasskeyNotAvailableForLoginError,
)

logger = logging.getLogger(__name__)


class PasskeyLoginOptionsService(AbstractPasskeyLoginOptionsService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        token_hasher: TokenHasher,
        passkey_provider: PasskeyProvider,
    ) -> None:
        self.uow = uow
        self.token_hasher = token_hasher
        self.passkey_provider = passkey_provider

    async def generate_options(
        self,
        payload: PasskeyLoginOptionsRequest,
    ) -> PasskeyLoginOptionsResponse:
        now = datetime.now(UTC)

        challenge_repository = self.uow.get_repository(AbstractAuthChallengeRepository)
        admin_user_repository = self.uow.get_repository(AbstractAdminUserRepository)
        webauthn_repository = self.uow.get_repository(
            AbstractAdminWebauthnCredentialRepository
        )

        raw_token = payload.challenge_token.get_secret_value()
        token_hash = self.token_hasher.hash_token(raw_token)

        logger.info(
            "Passkey options token received: token_length=%s hash_length=%s",
            len(raw_token),
            len(token_hash),
        )

        auth_challenge = await challenge_repository.get_by_token_hash(
            token_hash,
            ChallengeType.MFA_AUTHENTICATION,
            for_update=True,
        )

        logger.info(
            "Passkey login challenge lookup: found=%s",
            auth_challenge is not None,
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

        available_methods = challenge_data.get("available_mfa_methods", [])

        if "passkey" not in available_methods:
            raise PasskeyNotAvailableForLoginError()

        admin_user = await admin_user_repository.get_by_id(
            auth_challenge.admin_user_id,
            for_update=True,
        )

        logger.info(
            "Passkey login admin lookup: found=%s status=%s",
            admin_user is not None,
            admin_user.status.value if admin_user is not None else None,
        )

        if admin_user is None or admin_user.status != AdminUserStatus.ACTIVE:
            raise InvalidPasskeyLoginChallengeError()

        credentials = await webauthn_repository.get_active_by_admin_user_id(
            admin_user.id
        )

        logger.info(
            "Passkey login credentials lookup: count=%s",
            len(credentials),
        )

        if not credentials:
            raise PasskeyNotAvailableForLoginError()

        credential_ids = [credential.credential_id for credential in credentials]

        options = self.passkey_provider.generate_authentication_options(
            credential_ids=credential_ids,
        )

        options_json = json.loads(options_to_json(options))

        challenge_data = dict(challenge_data)
        challenge_data["webauthn_challenge"] = bytes_to_base64url(options.challenge)
        auth_challenge.challenge_data = challenge_data

        await self.uow.flush()

        return PasskeyLoginOptionsResponse(
            public_key=options_json,
        )
