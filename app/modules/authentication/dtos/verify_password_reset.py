from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VerifyPasswordResetResult:
    recovery_token: str