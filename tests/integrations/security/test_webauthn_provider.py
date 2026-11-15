from webauthn.helpers.structs import (
    UserVerificationRequirement,
)

from app.integrations.security.webauthn_provider import WebAuthnProvider


def test_generate_registration_options() -> None:
    provider = WebAuthnProvider()

    options = provider.generate_registration_options(
        user_id=b"test-user-id",
        username="admin@example.com",
        display_name="Admin",
    )

    assert options.rp.id == "localhost"
    assert options.user.id == b"test-user-id"
    assert options.user.name == "admin@example.com"
    assert options.user.display_name == "Admin"
    assert (
        options.authenticator_selection.user_verification
        == UserVerificationRequirement.REQUIRED
    )


def test_generate_authentication_options() -> None:
    provider = WebAuthnProvider()

    options = provider.generate_authentication_options(
        credential_ids=[b"credential-id"],
    )

    assert options.rp_id == "localhost"
    assert len(options.allow_credentials) == 1
    assert options.allow_credentials[0].id == b"credential-id"
    assert options.user_verification == UserVerificationRequirement.REQUIRED


def test_generate_authentication_options_without_credentials() -> None:
    provider = WebAuthnProvider()

    options = provider.generate_authentication_options(
        credential_ids=[],
    )

    assert options.rp_id == "localhost"
    assert options.allow_credentials == []
