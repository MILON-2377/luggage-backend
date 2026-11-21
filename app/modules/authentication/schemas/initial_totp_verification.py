from pydantic import BaseModel, ConfigDict, Field, SecretStr


class InitialTOTPVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enrollment_token: SecretStr
    code: SecretStr = Field(min_length=6, max_length=8)


class InitialTOTPVerificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recovery_codes: list[str]
