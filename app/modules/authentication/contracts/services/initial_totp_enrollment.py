from abc import ABC, abstractmethod

from app.modules.authentication.dtos.totp_enrollment import TOTPEnrollmentResult


class AbstractInitialTOTPEnrollmentService(ABC):
    @abstractmethod
    async def enroll(
        self,
        enrollment_token: str,
    ) -> TOTPEnrollmentResult:
        raise NotImplementedError
