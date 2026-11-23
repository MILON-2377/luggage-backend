from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_token: str
    expires_at: datetime
    available_mfa_methods: list[
        Literal["passkey", "totp", "recovery_code"]
    ]