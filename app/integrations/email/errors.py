from app.core.errors.base import AppError


class EmailError(AppError):
    status_code = 502
    error_code = "EMAIL_ERROR"
    default_message = "An email error occurred."


class EmailDeliveryError(EmailError):
    status_code = 502
    error_code = "EMAIL_DELIVERY_FAILED"
    default_message = "The email could not be delivered."


class EmailProviderUnavailableError(EmailDeliveryError):
    status_code = 503
    error_code = "EMAIL_PROVIDER_UNAVAILABLE"
    default_message = "The email service is temporarily unavailable."


class EmailTemplateError(EmailError):
    status_code = 500
    error_code = "EMAIL_TEMPLATE_ERROR"
    default_message = "The email template could not be rendered."
