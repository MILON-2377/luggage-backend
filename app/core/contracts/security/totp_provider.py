from abc import ABC, abstractmethod


class TOTPProvider(ABC):
    @abstractmethod
    def generate_secret(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_provisioning_uri(
        self,
        secret: str,
        account_name: str,
        issuer_name: str,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def verify_code(
        self,
        secret: str,
        code: str,
        valid_window: int = 0,
    ) -> bool:
        raise NotImplementedError
