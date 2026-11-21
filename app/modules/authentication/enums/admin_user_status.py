from enum import StrEnum


class AdminUserStatus(StrEnum):
    INVITED = "invited"
    PENDING_MFA_SETUP = "pending_mfa_setup"
    ACTIVE = "active"
    DISABLED = "disabled"
    SUSPENDED = "suspended"