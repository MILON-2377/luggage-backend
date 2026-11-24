from app.core.errors.base import AppError


class MediaStorageError(AppError):
    status_code = 502
    error_code = "MEDIA_STORAGE_ERROR"
    default_message = "The media storage provider failed to process the request."


class AssetNotFoundError(MediaStorageError):
    status_code = 404
    error_code = "MEDIA_STORAGE_ASSET_NOT_FOUND"
    default_message = "The uploaded file was not found at the storage provider."

    def __init__(self, public_id: str) -> None:
        self.public_id = public_id
        super().__init__(
            f"Media asset not found at provider: {public_id}",
            details={"public_id": public_id},
        )


class AssetVerificationError(MediaStorageError):
    status_code = 422
    error_code = "MEDIA_ASSET_VERIFICATION_FAILED"
    default_message = "The uploaded media asset failed verification."


class AssetPublicIdMismatchError(AssetVerificationError):
    error_code = "MEDIA_ASSET_PUBLIC_ID_MISMATCH"

    def __init__(self, *, expected: str, actual: str | None) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            "The uploaded media asset does not match the expected public ID.",
            details={"expected": expected, "actual": actual},
        )


class AssetResourceTypeMismatchError(AssetVerificationError):
    error_code = "MEDIA_ASSET_RESOURCE_TYPE_MISMATCH"

    def __init__(self, *, expected: str, actual: str | None) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            "The uploaded media asset does not match the expected resource type.",
            details={"expected": expected, "actual": actual},
        )


class AssetMimeTypeMismatchError(AssetVerificationError):
    error_code = "MEDIA_ASSET_MIME_TYPE_MISMATCH"

    def __init__(self, *, expected: str, actual: str | None) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            "The uploaded media asset does not match the expected MIME type.",
            details={"expected": expected, "actual": actual},
        )
