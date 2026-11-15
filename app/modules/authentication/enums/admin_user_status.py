from enum import StrEnum


class AdminUserStatus(StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    DISABLED = "disabled"
    SUSPENDED = "suspended"