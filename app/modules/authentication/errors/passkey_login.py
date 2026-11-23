
from app.core.errors.base import ConflictError, UnauthorizedError


class InvalidPasskeyLoginChallengeError(UnauthorizedError):
    error_code = "INVALID_PASSKEY_LOGIN_CHALLENGE"
    default_message = "The authentication challenge is invalid."


class ExpiredPasskeyLoginChallengeError(UnauthorizedError):
    error_code = "EXPIRED_PASSKEY_LOGIN_CHALLENGE"
    default_message = "The authentication challenge has expired."


class ConsumedPasskeyLoginChallengeError(ConflictError):
    error_code = "CONSUMED_PASSKEY_LOGIN_CHALLENGE"
    default_message = "The authentication challenge has already been consumed."


class LockedPasskeyLoginChallengeError(UnauthorizedError):
    error_code = "LOCKED_PASSKEY_LOGIN_CHALLENGE"
    default_message = "The authentication challenge has exceeded its allowed attempts."


class PasskeyNotAvailableForLoginError(ConflictError):
    error_code = "PASSKEY_NOT_AVAILABLE_FOR_LOGIN"
    default_message = "Passkey authentication is not available for this login."
