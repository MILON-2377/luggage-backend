from enum import StrEnum


class NotificationType(StrEnum):
    INQUIRY_RECEIVED = "inquiry_received"
    INQUIRY_ASSIGNED = "inquiry_assigned"
    QUOTATION_SENT = "quotation_sent"
    QUOTATION_ACCEPTED = "quotation_accepted"
    QUOTATION_EXPIRING = "quotation_expiring"
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_FAILED = "payment_failed"
    REFUND_PROCESSED = "refund_processed"
    SECURITY_ALERT = "security_alert"
    SYSTEM = "system"
