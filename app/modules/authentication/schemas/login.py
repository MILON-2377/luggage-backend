from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, SecretStr


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: SecretStr


class LoginResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_token: str
    expires_at: datetime
    available_mfa_methods: list[str]