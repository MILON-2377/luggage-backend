from enum import StrEnum


class PaymentType(StrEnum):
    DEPOSIT = "deposit"
    INSTALLMENT = "installment"
    BALANCE = "balance"
    FULL = "full"