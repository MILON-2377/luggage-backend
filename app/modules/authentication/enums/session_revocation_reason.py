from enum import StrEnum


class SessionRevocationReason(StrEnum):
    USER_LOGOUT = "user_logout"
    NEW_LOGIN = "new_login"
    ADMIN_REVOKED = "admin_revoked"
    PASSWORD_CHANGED = "password_changed"
    SECURITY_EVENT = "security_event"
    SESSION_EXPIRED = "session_expired"
