from app.core.errors.base import (
    ConflictError,
    InternalError,
    ValidationError,
)


class EmailOutboxError(InternalError):
    default_message = "An email outbox error occurred."


class EmailOutboxPayloadEncryptionError(EmailOutboxError):
    default_message = "Failed to encrypt the email payload."


class EmailOutboxPayloadDecryptionError(EmailOutboxError):
    default_message = "Failed to decrypt the email payload."


class EmailOutboxInvalidStatusError(ConflictError):
    default_message = "The email outbox record has an invalid status."


class EmailOutboxInvalidConfigurationError(ValidationError):
    default_message = "The email outbox configuration is invalid."
