from pwdlib import PasswordHash

from app.core.contracts.security.password_hasher import PasswordHasher


class Argon2PasswordHasher(PasswordHasher):
    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()

    def hash_password(self, password: str) -> str:
        return self._password_hash.hash(password)

    def verify_password(
        self,
        password: str,
        hashed_password: str,
    ) -> bool:
        return self._password_hash.verify(password, hashed_password)

    def verify_and_update_password(
        self,
        password: str,
        hashed_password: str,
    ) -> tuple[bool, str | None]:
        return self._password_hash.verify_and_update(
            password,
            hashed_password,
        )
