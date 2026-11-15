from enum import StrEnum


class ChallengeType(StrEnum):
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    MFA_AUTHENTICATION = "mfa_authentication"
    TOTP_ENROLLMENT = "totp_enrollment"
    WEBAUTHN_REGISTRATION = "webauthn_registration"
    ACCOUNT_RECOVERY = "account_recovery"