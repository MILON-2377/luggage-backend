from enum import StrEnum


class StorageLocationStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"
    DELETION_PENDING = "deletion_pending"
    DELETED = "deleted"