from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MediaCleanupResultDTO:
    stale_pending_found: int
    stale_pending_deleted: int
    deletion_pending_found: int
    deletion_pending_resumed: int
    failed: int