import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ValidateInvitationDTO:
    admin_user_id: uuid.UUID
    email: str
    expires_at: datetime
