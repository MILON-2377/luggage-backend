from app.core.errors.base import ConflictError, UnauthorizedError


class InvalidMFAEnrollmentSessionError(UnauthorizedError):
    error_code = "INVALID_MFA_ENROLLMENT_SESSION"
    default_message = "The MFA enrollment session is invalid."


class ExpiredMFAEnrollmentSessionError(UnauthorizedError):
    error_code = "EXPIRED_MFA_ENROLLMENT_SESSION"
    default_message = "The MFA enrollment session has expired."


class ConsumedMFAEnrollmentSessionError(ConflictError):
    error_code = "CONSUMED_MFA_ENROLLMENT_SESSION"
    default_message = "The MFA enrollment session has already been consumed."


class LockedMFAEnrollmentSessionError(UnauthorizedError):
    error_code = "LOCKED_MFA_ENROLLMENT_SESSION"
    default_message = "The MFA enrollment session has been locked."


class MFAEnrollmentAccountNotEligibleError(ConflictError):
    error_code = "MFA_ENROLLMENT_ACCOUNT_NOT_ELIGIBLE"
    default_message = "This account is not eligible for MFA enrollment."


class TOTPAlreadyVerifiedError(ConflictError):
    error_code = "TOTP_ALREADY_VERIFIED"
    default_message = "A verified TOTP credential already exists for this account."
