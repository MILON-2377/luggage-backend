from typing import Any

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import (
    bytes_to_base64url,
    options_to_json,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.core.config import settings
from app.core.contracts.security.passkey_provider import PasskeyProvider


class WebAuthnProvider(PasskeyProvider):
    def __init__(self) -> None:
        self._rp_id = settings.WEBAUTHN_RP_ID
        self._rp_name = settings.WEBAUTHN_RP_NAME
        self._origin = settings.WEBAUTHN_EXPECTED_ORIGIN

    def generate_registration_options(
        self,
        *,
        user_id: bytes,
        username: str,
        display_name: str,
    ) -> Any:
        return generate_registration_options(
            rp_id=self._rp_id,
            rp_name=self._rp_name,
            user_id=user_id,
            user_name=username,
            user_display_name=display_name,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
        )

    def verify_registration(
        self,
        *,
        credential: dict[str, Any],
        expected_challenge: bytes,
    ) -> Any:
        return verify_registration_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=self._rp_id,
            expected_origin=self._origin,
            require_user_verification=True,
        )

    def generate_authentication_options(
        self,
        *,
        credential_ids: list[bytes],
    ) -> Any:
        return generate_authentication_options(
            rp_id=self._rp_id,
            allow_credentials=[
                PublicKeyCredentialDescriptor(id=credential_id)
                for credential_id in credential_ids
            ],
            user_verification=UserVerificationRequirement.REQUIRED,
        )

    def verify_authentication(
        self,
        *,
        credential: dict[str, Any],
        expected_challenge: bytes,
        credential_public_key: bytes,
        credential_current_sign_count: int,
    ) -> Any:
        return verify_authentication_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=self._rp_id,
            expected_origin=self._origin,
            credential_public_key=credential_public_key,
            credential_current_sign_count=credential_current_sign_count,
            require_user_verification=True,
        )
