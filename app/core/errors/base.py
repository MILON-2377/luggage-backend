from typing import Any


class AppError(Exception):
    """
    Base exception for all application-level errors.
    """

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    default_message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | list[Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details

        super().__init__(self.message)


class ValidationError(AppError):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    default_message = "The provided data is invalid."


class UnauthorizedError(AppError):
    status_code = 401
    error_code = "UNAUTHORIZED"
    default_message = "Authentication is required."


class ForbiddenError(AppError):
    status_code = 403
    error_code = "FORBIDDEN"
    default_message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    status_code = 404
    error_code = "NOT_FOUND"
    default_message = "The requested resource was not found."


class ConflictError(AppError):
    status_code = 409
    error_code = "CONFLICT"
    default_message = "The request conflicts with the current resource state."


class InternalError(AppError):
    status_code = 500
    error_code = "INTERNAL_ERROR"
    default_message = "An unexpected internal error occurred."