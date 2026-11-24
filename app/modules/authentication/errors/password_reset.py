from app.core.errors.base import (
    ConflictError,
    UnauthorizedError,
)


class InvalidPasswordResetTokenError(UnauthorizedError):
    error_code = "INVALID_PASSWORD_RESET_TOKEN"
    default_message = "The password reset token is invalid."


class ExpiredPasswordResetTokenError(UnauthorizedError):
    error_code = "EXPIRED_PASSWORD_RESET_TOKEN"
    default_message = "The password reset token has expired."


class ConsumedPasswordResetTokenError(ConflictError):
    error_code = "CONSUMED_PASSWORD_RESET_TOKEN"
    default_message = "The password reset token has already been consumed."


class LockedPasswordResetTokenError(UnauthorizedError):
    error_code = "LOCKED_PASSWORD_RESET_TOKEN"
    default_message = "The password reset token has exceeded its allowed attempts."