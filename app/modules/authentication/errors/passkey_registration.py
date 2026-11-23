
from app.core.errors.base import ConflictError, UnauthorizedError


class InvalidPasskeyRegistrationSessionError(UnauthorizedError):
    error_code = "INVALID_PASSKEY_REGISTRATION_SESSION"
    default_message = "The passkey registration session is invalid."


class ExpiredPasskeyRegistrationSessionError(UnauthorizedError):
    error_code = "EXPIRED_PASSKEY_REGISTRATION_SESSION"
    default_message = "The passkey registration session has expired."


class ConsumedPasskeyRegistrationSessionError(ConflictError):
    error_code = "CONSUMED_PASSKEY_REGISTRATION_SESSION"
    default_message = "The passkey registration session has already been consumed."


class LockedPasskeyRegistrationSessionError(UnauthorizedError):
    error_code = "LOCKED_PASSKEY_REGISTRATION_SESSION"
    default_message = "The passkey registration session is locked."


class InvalidPasskeyAttestationError(UnauthorizedError):
    error_code = "INVALID_PASSKEY_ATTESTATION"
    default_message = "The passkey registration response could not be verified."


class PasskeyCredentialAlreadyRegisteredError(ConflictError):
    error_code = "PASSKEY_CREDENTIAL_ALREADY_REGISTERED"
    default_message = "This passkey credential is already registered."
