from app.core.errors.base import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)


class InvalidInitialMFASetupTokenError(UnauthorizedError):
    error_code = "INVALID_INITIAL_MFA_SETUP_TOKEN"
    default_message = "The initial MFA setup token is invalid."


class ExpiredInitialMFASetupTokenError(UnauthorizedError):
    error_code = "EXPIRED_INITIAL_MFA_SETUP_TOKEN"
    default_message = "The initial MFA setup token has expired."


class ConsumedInitialMFASetupTokenError(ConflictError):
    error_code = "CONSUMED_INITIAL_MFA_SETUP_TOKEN"
    default_message = "The initial MFA setup token has already been used."


class LockedInitialMFASetupTokenError(UnauthorizedError):
    error_code = "LOCKED_INITIAL_MFA_SETUP_TOKEN"
    default_message = "The initial MFA setup token has been locked."


class InitialMFASetupAccountNotFoundError(NotFoundError):
    error_code = "INITIAL_MFA_SETUP_ACCOUNT_NOT_FOUND"
    default_message = (
        "The account associated with the initial MFA setup token was not found."
    )


class InitialMFASetupAccountStateError(ConflictError):
    error_code = "INITIAL_MFA_SETUP_ACCOUNT_STATE_CONFLICT"
    default_message = "The account is not eligible for initial MFA setup."


class InitialMFASetupAuthorizationConflictError(ConflictError):
    error_code = "INITIAL_MFA_SETUP_AUTHORIZATION_CONFLICT"
    default_message = "The initial MFA setup authorization is no longer valid."


class InvalidInitialMFASetupAuthorizationError(UnauthorizedError):
    error_code = "INVALID_INITIAL_MFA_SETUP_AUTHORIZATION"
    default_message = "The initial MFA setup authorization is invalid or expired."


class InitialMFASetupAccountNotEligibleError(ConflictError):
    error_code = "INITIAL_MFA_SETUP_ACCOUNT_NOT_ELIGIBLE"
    default_message = "This account is not eligible for initial MFA setup."
