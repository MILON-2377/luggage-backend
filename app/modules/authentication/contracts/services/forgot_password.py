from abc import ABC, abstractmethod


class AbstractForgotPasswordService(ABC):
    @abstractmethod
    async def request_password_reset(self, email: str) -> None:
        raise NotImplementedError