from app.core.errors.base import ConflictError, UnauthorizedError


class InvalidRecoveryCodeLoginChallengeError(UnauthorizedError):
    error_code = "INVALID_RECOVERY_CODE_LOGIN_CHALLENGE"
    default_message = "The recovery-code login challenge is invalid."


class ExpiredRecoveryCodeLoginChallengeError(UnauthorizedError):
    error_code = "EXPIRED_RECOVERY_CODE_LOGIN_CHALLENGE"
    default_message = "The recovery-code login challenge has expired."


class ConsumedRecoveryCodeLoginChallengeError(ConflictError):
    error_code = "CONSUMED_RECOVERY_CODE_LOGIN_CHALLENGE"
    default_message = "The recovery-code login challenge has already been used."


class LockedRecoveryCodeLoginChallengeError(UnauthorizedError):
    error_code = "LOCKED_RECOVERY_CODE_LOGIN_CHALLENGE"
    default_message = "The recovery-code login challenge is locked."


class InvalidRecoveryCodeError(UnauthorizedError):
    error_code = "INVALID_RECOVERY_CODE"
    default_message = "The recovery code is invalid."


class RecoveryCodeNotAvailableError(UnauthorizedError):
    error_code = "RECOVERY_CODE_NOT_AVAILABLE"
    default_message = "No unused recovery code is available for this account."