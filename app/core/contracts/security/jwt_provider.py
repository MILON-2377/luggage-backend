from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class AbstractJWTProvider(ABC):
    @abstractmethod
    def create_access_token(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def decode_access_token(self, token: str) -> dict[str, Any]:
        raise NotImplementedError