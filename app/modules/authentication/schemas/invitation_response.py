from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class ValidateInvitationResponse(BaseModel):
    valid: bool
    email: EmailStr
    expires_at: datetime


class CreateAdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    admin_user_id: UUID
    email: EmailStr
    role: str
    status: str
    invitation_expires_at: datetime
