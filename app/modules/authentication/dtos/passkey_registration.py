from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PasskeyRegistrationOptionsDTO:
    enrollment_token: str


@dataclass(frozen=True, slots=True)
class PasskeyRegistrationOptionsResultDTO:
    options: dict[str, Any]


@dataclass(frozen=True, slots=True)
class PasskeyRegistrationVerificationDTO:
    enrollment_token: str
    credential: dict[str, Any]
    credential_name: str | None = None


@dataclass(frozen=True, slots=True)
class PasskeyRegistrationResultDTO:
    credential_id: UUID
    credential_name: str | None
