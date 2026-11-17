from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AcceptInvitationDTO:
    invitation_token: str
    password: str
    first_name: str
    last_name: str
    display_name: str | None = None
    phone: str | None = None
    job_title: str | None = None
    department: str | None = None
    timezone: str = "Asia/Shanghai"
    language: str = "en"
