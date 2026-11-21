from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class InitialMFASetupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    initial_setup_token: SecretStr = Field(
        min_length=1,
        max_length=256,
    )


class InitialMFASetupResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enrollment_token: str
    expires_at: datetime
