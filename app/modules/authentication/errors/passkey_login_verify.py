from app.core.errors.base import ConflictError, UnauthorizedError


class InvalidPasskeyAssertionError(UnauthorizedError):
    error_code = "INVALID_PASSKEY_ASSERTION"
    default_message = "The passkey authentication response is invalid."


class ExpiredPasskeyLoginChallengeError(UnauthorizedError):
    error_code = "EXPIRED_PASSKEY_LOGIN_CHALLENGE"
    default_message = "The passkey authentication challenge has expired."


class ConsumedPasskeyLoginChallengeError(ConflictError):
    error_code = "CONSUMED_PASSKEY_LOGIN_CHALLENGE"
    default_message = "The passkey authentication challenge has already been consumed."


class LockedPasskeyLoginChallengeError(UnauthorizedError):
    error_code = "LOCKED_PASSKEY_LOGIN_CHALLENGE"
    default_message = "The passkey authentication challenge has exceeded its allowed attempts."


class PasskeyCredentialNotFoundError(UnauthorizedError):
    error_code = "PASSKEY_CREDENTIAL_NOT_FOUND"
    default_message = "The passkey credential is invalid or unavailable."