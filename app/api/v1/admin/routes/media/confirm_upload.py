import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.policies import RateLimitPolicyName
from app.modules.authentication.dependencies.current_admin import CurrentAdmin
from app.modules.media.contracts.services.media import AbstractMediaService
from app.modules.media.dependencies.media import get_media_service
from app.modules.media.dependencies.uow import get_media_uow
from app.modules.media.schemas.upload import ConfirmUploadResponse

router = APIRouter()


@router.post(
    "/{media_asset_id}/confirm",
    response_model=ConfirmUploadResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(rate_limit(RateLimitPolicyName.AUTHENTICATED_API)),
    ],
)
async def confirm_upload(
    media_asset_id: uuid.UUID,
    response: Response,
    _admin: CurrentAdmin,
    service: Annotated[AbstractMediaService, Depends(get_media_service)],
    uow: Annotated[AbstractUnitOfWork, Depends(get_media_uow)],
) -> ConfirmUploadResponse:
    result = await service.confirm_upload(media_asset_id)

    await uow.commit()

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return ConfirmUploadResponse(
        media_asset_id=result.media_asset_id,
        status=result.status,
        media_type=result.media_type,
        mime_type=result.mime_type,
        file_format=result.file_format,
        file_size=result.file_size,
        width=result.width,
        height=result.height,
        duration=result.duration,
        url=result.url,
    )
