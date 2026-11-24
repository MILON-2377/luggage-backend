from collections.abc import Callable

from app.core.contracts.storage.media import AbstractMediaStorage
from app.core.errors.base import InternalError
from app.modules.media.enums import StorageProvider

MediaStorageFactory = Callable[[], AbstractMediaStorage]

_REGISTRY: dict[StorageProvider, MediaStorageFactory] = {}


class UnknownMediaProviderError(InternalError):
    error_code = "MEDIA_PROVIDER_NOT_REGISTERED"
    default_message = "The configured media provider is not registered."

    def __init__(self, provider: StorageProvider | str) -> None:
        self.provider = provider
        super().__init__(
            f"No media storage registered for provider: {provider!r}",
            details={"provider": str(provider)},
        )


class DuplicateMediaProviderError(InternalError):
    error_code = "MEDIA_PROVIDER_ALREADY_REGISTERED"
    default_message = "The media provider is already registered."

    def __init__(self, provider: StorageProvider) -> None:
        self.provider = provider
        super().__init__(
            f"Media provider already registered: {provider.value!r}",
            details={"provider": provider.value},
        )


def register_media_provider(
    provider: StorageProvider,
    factory: MediaStorageFactory,
) -> None:
    if provider in _REGISTRY:
        raise DuplicateMediaProviderError(provider)

    _REGISTRY[provider] = factory


def is_media_provider_registered(provider: StorageProvider) -> bool:
    return provider in _REGISTRY


def create_media_storage(provider: StorageProvider) -> AbstractMediaStorage:
    try:
        factory = _REGISTRY[provider]
    except KeyError as exc:
        raise UnknownMediaProviderError(provider) from exc

    return factory()


def registered_media_providers() -> frozenset[StorageProvider]:
    return frozenset(_REGISTRY)


def clear_media_providers() -> None:
    """Remove all registrations. Intended for tests only."""
    _REGISTRY.clear()
