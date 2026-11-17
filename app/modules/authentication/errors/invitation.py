from app.core.errors.base import (
    ConflictError,
    NotFoundError,
)


class InvitationNotFoundError(NotFoundError):
    default_message = "Invitation not found."


class InvitationExpiredError(ConflictError):
    default_message = "Invitation has expired."


class InvitationAlreadyUsedError(ConflictError):
    default_message = "Invitation has already been used."


class InvitationAttemptsExceededError(ConflictError):
    default_message = "Invitation attempt limit exceeded."


class AccountNotFoundError(NotFoundError):
    default_message = "Account not found."


class AccountNotEligibleForInvitationError(ConflictError):
    default_message = "This account is not eligible for an invitation."
