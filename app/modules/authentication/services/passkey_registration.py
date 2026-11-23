import base64
import json
from datetime import UTC, datetime
from typing import Any

from webauthn.helpers.options_to_json import options_to_json

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.contracts.security.passkey_provider import PasskeyProvider
from app.core.contracts.security.token_hasher import TokenHasher
from app.modules.authentication.contracts.repositories import (
    AbstractAdminUserRepository,
    AbstractAdminWebauthnCredentialRepository,
    AbstractAuthChallengeRepository,
)
from app.modules.authentication.contracts.services.passkey_registration import (
    AbstractPasskeyRegistrationService,
)
from app.modules.authentication.dtos.passkey_registration import (
    PasskeyRegistrationOptionsResultDTO,
    PasskeyRegistrationResultDTO,
    PasskeyRegistrationVerificationDTO,
)
from app.modules.authentication.enums import AdminUserStatus, ChallengeType
from app.modules.authentication.errors.passkey_registration import (
    ConsumedPasskeyRegistrationSessionError,
    ExpiredPasskeyRegistrationSessionError,
    InvalidPasskeyAttestationError,
    InvalidPasskeyRegistrationSessionError,
    LockedPasskeyRegistrationSessionError,
    PasskeyCredentialAlreadyRegisteredError,
)
from app.modules.authentication.models.admin_webauthn_credential import (
    AdminWebauthnCredential,
)


class PasskeyRegistrationService(AbstractPasskeyRegistrationService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        id_generator: AbstractIDGenerator,
        token_hasher: TokenHasher,
        passkey_provider: PasskeyProvider,
    ) -> None:
        self.uow = uow
        self.id_generator = id_generator
        self.token_hasher = token_hasher
        self.passkey_provider = passkey_provider

    async def generate_registration_options(
        self,
        enrollment_token: str,
    ) -> PasskeyRegistrationOptionsResultDTO:
        challenge, admin_user = await self._get_enrollment_session(enrollment_token)

        options = self.passkey_provider.generate_registration_options(
            user_id=admin_user.id.bytes,
            username=admin_user.email,
            display_name=admin_user.email,
        )

        challenge.challenge_data = {
            **(challenge.challenge_data or {}),
            "webauthn_challenge": base64.urlsafe_b64encode(options.challenge)
            .decode("ascii")
            .rstrip("="),
        }

        await self.uow.flush()

        return PasskeyRegistrationOptionsResultDTO(
            options=json.loads(options_to_json(options))
        )

    async def verify_registration(
        self,
        data: PasskeyRegistrationVerificationDTO,
    ) -> PasskeyRegistrationResultDTO:
        challenge, admin_user = await self._get_enrollment_session(
            data.enrollment_token
        )

        encoded_challenge = (challenge.challenge_data or {}).get("webauthn_challenge")
        if not encoded_challenge:
            raise InvalidPasskeyRegistrationSessionError()

        try:
            padding = "=" * (-len(encoded_challenge) % 4)
            expected_challenge = base64.urlsafe_b64decode(encoded_challenge + padding)
            verification = self.passkey_provider.verify_registration(
                credential=data.credential,
                expected_challenge=expected_challenge,
            )
        except Exception as exc:
            raise InvalidPasskeyAttestationError() from exc

        credential_id = verification.credential_id

        credential_repository = self.uow.get_repository(
            AbstractAdminWebauthnCredentialRepository
        )

        existing_credential = await credential_repository.get_by_credential_id(
            credential_id,
            for_update=True,
        )
        if existing_credential is not None:
            raise PasskeyCredentialAlreadyRegisteredError()

        credential_uuid = self.id_generator.generate()

        response_data: dict[str, Any] = data.credential.get("response", {})
        transports = response_data.get("transports")

        device_type = getattr(
            verification.credential_device_type,
            "value",
            verification.credential_device_type,
        )
        backup_eligible = device_type == "multi_device"

        credential_repository.create(
            AdminWebauthnCredential(
                id=credential_uuid,
                admin_user_id=admin_user.id,
                credential_id=credential_id,
                public_key=verification.credential_public_key,
                sign_count=verification.sign_count,
                transports=transports,
                aaguid=verification.aaguid,
                device_name=data.credential_name,
                backup_eligible=backup_eligible,
                backup_state=verification.credential_backed_up,
            )
        )

        await self.uow.flush()

        return PasskeyRegistrationResultDTO(
            credential_id=credential_uuid,
            credential_name=data.credential_name,
        )

    async def _get_enrollment_session(
        self,
        enrollment_token: str,
    ) -> tuple[Any, Any]:
        if not enrollment_token or not enrollment_token.strip():
            raise InvalidPasskeyRegistrationSessionError()

        now = datetime.now(UTC)

        challenge_repository = self.uow.get_repository(AbstractAuthChallengeRepository)
        admin_user_repository = self.uow.get_repository(AbstractAdminUserRepository)

        challenge = await challenge_repository.get_by_token_hash(
            self.token_hasher.hash_token(enrollment_token),
            ChallengeType.MFA_ENROLLMENT_SESSION,
            for_update=True,
        )

        if challenge is None:
            raise InvalidPasskeyRegistrationSessionError()

        if challenge.consumed_at is not None:
            raise ConsumedPasskeyRegistrationSessionError()

        if challenge.expires_at <= now:
            raise ExpiredPasskeyRegistrationSessionError()

        if challenge.failed_attempts >= challenge.max_attempts:
            raise LockedPasskeyRegistrationSessionError()

        if (
            not challenge.challenge_data
            or challenge.challenge_data.get("purpose") != "initial_mfa_enrollment"
        ):
            raise InvalidPasskeyRegistrationSessionError()

        admin_user = await admin_user_repository.get_by_id(
            challenge.admin_user_id,
            for_update=True,
        )

        if admin_user is None:
            raise InvalidPasskeyRegistrationSessionError()

        if admin_user.status != AdminUserStatus.PENDING_MFA_SETUP:
            raise InvalidPasskeyRegistrationSessionError()

        return challenge, admin_user
