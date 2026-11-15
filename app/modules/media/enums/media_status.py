from enum import StrEnum


class MediaStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DELETION_PENDING = "deletion_pending"
    DELETED = "deleted"