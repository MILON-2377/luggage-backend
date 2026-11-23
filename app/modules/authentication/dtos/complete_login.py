from datetime import datetime
from ipaddress import IPv4Address, IPv6Address
from uuid import UUID

from pydantic import BaseModel, ConfigDict, SecretStr


class CompleteLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    admin_user_id: UUID

    device_name: str | None = None
    device_type: str | None = None
    browser: str | None = None
    operating_system: str | None = None
    ip_address: IPv4Address | IPv6Address | None = None
    user_agent: str | None = None


class CompleteLoginResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: UUID

    access_token: SecretStr
    refresh_token: SecretStr

    access_token_expires_at: datetime
    session_expires_at: datetime