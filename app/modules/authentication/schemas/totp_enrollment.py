from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TOTPEnrollmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enrollment_token: str


class TOTPEnrollmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    secret: str
    provisioning_uri: str
    expires_at: datetime
