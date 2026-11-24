from app.core.config import Settings
from app.core.storage.registry import (
    register_media_provider,
    registered_media_providers,
)
from app.integrations.media.cloudinary_media_storage import (
    CloudinaryMediaStorage,
)
from app.modules.media.enums import StorageProvider


def register_media_providers(settings: Settings) -> None:
    if StorageProvider.CLOUDINARY not in registered_media_providers():
        register_media_provider(
            StorageProvider.CLOUDINARY,
            lambda: CloudinaryMediaStorage(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET.get_secret_value(),
                upload_preset=settings.CLOUDINARY_UPLOAD_PRESET,
            ),
        )