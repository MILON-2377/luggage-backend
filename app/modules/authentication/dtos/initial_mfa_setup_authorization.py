from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class InitialMFASetupAuthorizationResult:
    admin_user_id: UUID
    enrollment_token: str
    expires_at: datetime
