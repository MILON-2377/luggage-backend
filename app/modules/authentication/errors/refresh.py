from app.core.errors.base import UnauthorizedError


class InvalidRefreshTokenError(UnauthorizedError):
    error_code = "INVALID_REFRESH_TOKEN"
    default_message = "The refresh token is invalid, expired, or has been revoked."
