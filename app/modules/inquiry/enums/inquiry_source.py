
from enum import StrEnum


class InquirySource(StrEnum):
    CONTACT_FORM = "contact_form"
    PRODUCT_PAGE = "product_page"
    EMAIL = "email"
    PHONE = "phone"
    TRADE_SHOW = "trade_show"
    OTHER = "other"
