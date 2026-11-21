from abc import ABC, abstractmethod

from app.modules.authentication.dtos.passkey_registration import (
    PasskeyRegistrationOptionsResultDTO,
    PasskeyRegistrationResultDTO,
    PasskeyRegistrationVerificationDTO,
)


class AbstractPasskeyRegistrationService(ABC):
    @abstractmethod
    async def generate_registration_options(
        self,
        enrollment_token: str,
    ) -> PasskeyRegistrationOptionsResultDTO:
        raise NotImplementedError

    @abstractmethod
    async def verify_registration(
        self,
        data: PasskeyRegistrationVerificationDTO,
    ) -> PasskeyRegistrationResultDTO:
        raise NotImplementedError
