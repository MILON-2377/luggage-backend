from datetime import datetime
from ipaddress import IPv4Address, IPv6Address
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.authentication.dtos.token import AuthenticationTokensDTO


class CreateAdminSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    admin_user_id: UUID
    session_id: UUID
    tokens: AuthenticationTokensDTO

    device_name: str | None = None
    device_type: str | None = None
    browser: str | None = None
    operating_system: str | None = None
    ip_address: IPv4Address | IPv6Address | None = None
    user_agent: str | None = None

    issued_at: datetime


class CreateAdminSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    expires_at: datetime