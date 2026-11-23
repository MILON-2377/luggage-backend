from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.authentication.enums import AdminUserStatus


class AdminProfileResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )

    first_name: str | None
    last_name: str | None
    display_name: str | None
    timezone: str
    language: str


class AdminMeResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )

    id: UUID
    email: str
    status: AdminUserStatus
    email_verified_at: datetime | None
    last_login_at: datetime | None
    profile: AdminProfileResponse | None