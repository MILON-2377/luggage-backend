from enum import StrEnum


class MediaFileRole(StrEnum):
    ORIGINAL = "original"
    THUMBNAIL = "thumbnail"
    PREVIEW = "preview"
    OPTIMIZED = "optimized"
    POSTER = "poster"