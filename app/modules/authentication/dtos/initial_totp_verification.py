import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InitialTOTPVerificationResult:
    admin_user_id: uuid.UUID
    recovery_codes: tuple[str, ...]
