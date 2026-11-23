from app.core.errors.base import ConflictError, UnauthorizedError


class InvalidTotpLoginChallengeError(UnauthorizedError):
    error_code = "INVALID_TOTP_LOGIN_CHALLENGE"
    default_message = "The TOTP login challenge is invalid."


class ExpiredTotpLoginChallengeError(UnauthorizedError):
    error_code = "EXPIRED_TOTP_LOGIN_CHALLENGE"
    default_message = "The TOTP login challenge has expired."


class ConsumedTotpLoginChallengeError(ConflictError):
    error_code = "CONSUMED_TOTP_LOGIN_CHALLENGE"
    default_message = "The TOTP login challenge has already been used."


class LockedTotpLoginChallengeError(UnauthorizedError):
    error_code = "LOCKED_TOTP_LOGIN_CHALLENGE"
    default_message = "The TOTP login challenge is locked."


class InvalidTotpCodeError(UnauthorizedError):
    error_code = "INVALID_TOTP_CODE"
    default_message = "The TOTP code is invalid."


class TotpCredentialNotFoundError(UnauthorizedError):
    error_code = "TOTP_CREDENTIAL_NOT_FOUND"
    default_message = "No active TOTP credential is available for this account."