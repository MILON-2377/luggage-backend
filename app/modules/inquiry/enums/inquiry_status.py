
from enum import StrEnum


class InquiryStatus(StrEnum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    QUOTED = "quoted"
    WON = "won"
    LOST = "lost"
    SPAM = "spam"
    CLOSED = "closed"
