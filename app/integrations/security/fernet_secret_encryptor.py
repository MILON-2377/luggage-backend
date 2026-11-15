from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.contracts.security.secret_encryptor import SecretEncryptor


class FernetSecretEncryptor(SecretEncryptor):
    def __init__(self) -> None:
        self._fernet = Fernet(
            settings.AUTH_ENCRYPTION_KEY.get_secret_value().encode("utf-8")
        )

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Unable to decrypt secret.") from exc
