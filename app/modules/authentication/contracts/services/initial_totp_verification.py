from abc import ABC, abstractmethod

from app.modules.authentication.dtos.initial_totp_verification import (
    InitialTOTPVerificationResult,
)


class AbstractInitialTOTPVerificationService(ABC):
    @abstractmethod
    async def verify(
        self,
        enrollment_token: str,
        code: str,
    ) -> InitialTOTPVerificationResult:
        raise NotImplementedError