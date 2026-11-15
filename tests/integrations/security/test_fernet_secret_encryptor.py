import pytest
from cryptography.fernet import InvalidToken

from app.integrations.security.fernet_secret_encryptor import FernetSecretEncryptor


def test_encrypt_and_decrypt() -> None:
    encryptor = FernetSecretEncryptor()
    secret = "JBSWY3DPEHPK3PXP"

    encrypted = encryptor.encrypt(secret)

    assert encrypted != secret
    assert encryptor.decrypt(encrypted) == secret


def test_encryption_produces_different_ciphertexts() -> None:
    encryptor = FernetSecretEncryptor()
    secret = "JBSWY3DPEHPK3PXP"

    first = encryptor.encrypt(secret)
    second = encryptor.encrypt(secret)

    assert first != second
    assert encryptor.decrypt(first) == secret
    assert encryptor.decrypt(second) == secret


def test_decrypt_invalid_ciphertext() -> None:
    encryptor = FernetSecretEncryptor()

    with pytest.raises(ValueError, match="Unable to decrypt secret"):
        encryptor.decrypt("invalid-ciphertext")
