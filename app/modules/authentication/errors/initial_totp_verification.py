from app.core.errors.base import ConflictError, UnauthorizedError


class InvalidMFAEnrollmentSessionError(UnauthorizedError):
    error_code = "INVALID_MFA_ENROLLMENT_SESSION"
    default_message = "The MFA enrollment session is invalid."


class ExpiredMFAEnrollmentSessionError(UnauthorizedError):
    error_code = "EXPIRED_MFA_ENROLLMENT_SESSION"
    default_message = "The MFA enrollment session has expired."


class ConsumedMFAEnrollmentSessionError(ConflictError):
    error_code = "CONSUMED_MFA_ENROLLMENT_SESSION"
    default_message = "The MFA enrollment session has already been used."


class LockedMFAEnrollmentSessionError(UnauthorizedError):
    error_code = "LOCKED_MFA_ENROLLMENT_SESSION"
    default_message = "The MFA enrollment session has been locked."


class MFAEnrollmentAccountNotEligibleError(ConflictError):
    error_code = "MFA_ENROLLMENT_ACCOUNT_NOT_ELIGIBLE"
    default_message = "The account is not eligible for initial MFA setup."


class TOTPEnrollmentNotFoundError(ConflictError):
    error_code = "TOTP_ENROLLMENT_NOT_FOUND"
    default_message = "No pending TOTP enrollment was found."


class TOTPEnrollmentAlreadyVerifiedError(ConflictError):
    error_code = "TOTP_ENROLLMENT_ALREADY_VERIFIED"
    default_message = "The TOTP credential has already been verified."


class InvalidTOTPVerificationCodeError(UnauthorizedError):
    error_code = "INVALID_TOTP_VERIFICATION_CODE"
    default_message = "The authenticator code is invalid."


class TOTPVerificationConflictError(ConflictError):
    error_code = "TOTP_VERIFICATION_CONFLICT"
    default_message = "The TOTP verification could not be completed. Please try again."


class TOTPCodeAlreadyUsedError(UnauthorizedError):
    error_code = "TOTP_CODE_ALREADY_USED"
    default_message = "This authenticator code has already been used."
