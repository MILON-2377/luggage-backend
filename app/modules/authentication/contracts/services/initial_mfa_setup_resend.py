from abc import ABC, abstractmethod


class AbstractInitialMFASetupResendService(ABC):
    @abstractmethod
    async def resend(self, email: str) -> None:
        raise NotImplementedError