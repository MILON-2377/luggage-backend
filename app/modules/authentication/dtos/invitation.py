import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class InvitationResultDTO:
    admin_user_id: uuid.UUID
    email: str
    invitation_token: str
    expires_at: datetime
