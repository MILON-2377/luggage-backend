from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.modules.media.contracts.repositories.media_asset import (
    AbstractMediaAssetRepository,
)
from app.modules.media.contracts.repositories.media_file import (
    AbstractMediaFileRepository,
)
from app.modules.media.contracts.repositories.media_storage_location import (
    AbstractMediaStorageLocationRepository,
)
from app.modules.media.repositories.media_asset import MediaAssetRepository
from app.modules.media.repositories.media_file import MediaFileRepository
from app.modules.media.repositories.media_storage_location import (
    MediaStorageLocationRepository,
)


def register_media_repositories(
    uow: AbstractUnitOfWork,
) -> None:
    session = uow.session

    repositories = (
        (AbstractMediaAssetRepository, MediaAssetRepository),
        (AbstractMediaFileRepository, MediaFileRepository),
        (
            AbstractMediaStorageLocationRepository,
            MediaStorageLocationRepository,
        ),
    )

    for contract, implementation in repositories:
        uow.register_repository(
            contract,
            implementation(session),
        )