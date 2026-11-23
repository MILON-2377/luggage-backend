from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, SecretStr


class CreateAuthenticationTokensRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    admin_user_id: UUID
    session_id: UUID
    issued_at: datetime


class AuthenticationTokensDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: SecretStr
    refresh_token: SecretStr
    refresh_token_hash: str

    access_token_expires_at: datetime
    session_expires_at: datetime