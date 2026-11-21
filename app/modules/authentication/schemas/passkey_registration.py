from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class PasskeyRegistrationOptionsRequest(BaseModel):
    enrollment_token: SecretStr


class PasskeyRegistrationOptionsResponse(BaseModel):
    options: dict[str, Any]


class PasskeyRegistrationVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enrollment_token: SecretStr
    credential: dict[str, Any] = Field(min_length=1)
    credential_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )


class PasskeyRegistrationVerificationResponse(BaseModel):
    credential_id: str
    credential_name: str | None
