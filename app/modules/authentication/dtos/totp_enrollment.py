import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class TOTPEnrollmentResult:
    admin_user_id: uuid.UUID
    secret: str
    provisioning_uri: str
    expires_at: datetime
