from enum import StrEnum


class AcceptanceMethod(StrEnum):
    WEB_LINK = "web_link"
    EMAIL_REPLY = "email_reply"
    SIGNED_DOCUMENT = "signed_document"
    PHONE = "phone"
    MANUAL = "manual"