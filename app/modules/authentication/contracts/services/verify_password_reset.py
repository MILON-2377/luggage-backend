from abc import ABC, abstractmethod

from app.modules.authentication.dtos.verify_password_reset import (
    VerifyPasswordResetResult,
)


class AbstractVerifyPasswordResetService(ABC):
    @abstractmethod
    async def verify_password_reset_token(
        self,
        token: str,
    ) -> VerifyPasswordResetResult:
        raise NotImplementedError