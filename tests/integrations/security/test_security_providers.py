from app.integrations.security.argon2_password_hasher import Argon2PasswordHasher
from app.integrations.security.fernet_secret_encryptor import FernetSecretEncryptor
from app.integrations.security.pyotp_provider import PyOTPProvider
from app.integrations.security.sha256_token_hasher import SHA256TokenHasher
from app.integrations.security.webauthn_provider import WebAuthnProvider


def test_security_providers_can_be_instantiated() -> None:
    assert isinstance(Argon2PasswordHasher(), Argon2PasswordHasher)
    assert isinstance(SHA256TokenHasher(), SHA256TokenHasher)
    assert isinstance(FernetSecretEncryptor(), FernetSecretEncryptor)
    assert isinstance(PyOTPProvider(), PyOTPProvider)
    assert isinstance(WebAuthnProvider(), WebAuthnProvider)
