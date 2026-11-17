import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateInvitedAccountDTO:
    email: str
    role_slug: str
    created_by: uuid.UUID
