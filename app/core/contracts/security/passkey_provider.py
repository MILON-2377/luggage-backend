from abc import ABC, abstractmethod
from typing import Any


class PasskeyProvider(ABC):
    @abstractmethod
    def generate_registration_options(
        self,
        *,
        user_id: bytes,
        username: str,
        display_name: str,
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def verify_registration(
        self,
        *,
        credential: dict[str, Any],
        expected_challenge: bytes,
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def generate_authentication_options(
        self,
        *,
        credential_ids: list[bytes],
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def verify_authentication(
        self,
        *,
        credential: dict[str, Any],
        expected_challenge: bytes,
        credential_public_key: bytes,
        credential_current_sign_count: int,
    ) -> Any:
        raise NotImplementedError
