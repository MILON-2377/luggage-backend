from abc import ABC, abstractmethod


class TokenHasher(ABC):
    @abstractmethod
    def hash_token(self, token: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def verify_token(self, token: str, token_hash: str) -> bool:
        raise NotImplementedError
