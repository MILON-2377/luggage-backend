from app.core.errors.base import UnauthorizedError


class InvalidAccessTokenError(UnauthorizedError):
    error_code = "INVALID_ACCESS_TOKEN"
    default_message = "The access token is invalid or has expired."