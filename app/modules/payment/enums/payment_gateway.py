from enum import StrEnum


class PaymentGateway(StrEnum):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    ALIPAY = "alipay"
    WECHAT_PAY = "wechat_pay"
    MANUAL = "manual"
