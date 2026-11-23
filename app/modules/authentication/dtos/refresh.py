
from datetime import datetime

from pydantic import BaseModel, ConfigDict, SecretStr


class RefreshTokensDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: SecretStr
    refresh_token: SecretStr
    access_token_expires_at: datetime
    session_expires_at: datetime