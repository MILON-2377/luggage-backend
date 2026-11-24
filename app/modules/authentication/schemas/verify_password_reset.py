from pydantic import BaseModel, ConfigDict, Field


class VerifyPasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=32, max_length=128)


class VerifyPasswordResetResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recovery_token: str