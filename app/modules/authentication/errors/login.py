from app.core.errors.base import ConflictError, UnauthorizedError


class InvalidLoginCredentialsError(UnauthorizedError):
    error_code = "INVALID_LOGIN_CREDENTIALS"
    default_message = "The email or password is incorrect."


class AccountLockedError(UnauthorizedError):
    error_code = "ACCOUNT_LOCKED"
    default_message = "This account is temporarily locked due to failed login attempts."


class AccountNotEligibleForLoginError(ConflictError):
    error_code = "ACCOUNT_NOT_ELIGIBLE_FOR_LOGIN"
    default_message = "This account is not eligible to log in."



