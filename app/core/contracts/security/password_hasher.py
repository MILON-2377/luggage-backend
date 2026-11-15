from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    @abstractmethod
    def hash_password(self, password: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def verify_password(
        self,
        password: str,
        hashed_password: str,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    def verify_and_update_password(
        self,
        password: str,
        hashed_password: str,
    ) -> tuple[bool, str | None]:
        raise NotImplementedError
