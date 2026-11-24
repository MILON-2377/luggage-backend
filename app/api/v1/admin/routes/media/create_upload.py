from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.policies import RateLimitPolicyName
from app.modules.authentication.dependencies.current_admin import CurrentAdmin
from app.modules.media.contracts.services.media import AbstractMediaService
from app.modules.media.dependencies.media import get_media_service
from app.modules.media.dependencies.uow import get_media_uow
from app.modules.media.dtos.upload import CreateUploadDTO
from app.modules.media.schemas.upload import (
    CreateUploadRequest,
    CreateUploadResponse,
)

router = APIRouter()


@router.post(
    "/uploads",
    response_model=CreateUploadResponse,
    status_code=status.HTTP_201_CREATED,
    # dependencies=[
    #     Depends(rate_limit(RateLimitPolicyName.AUTHENTICATED_API)),
    # ],
)
async def create_upload(
    payload: CreateUploadRequest,
    response: Response,
    admin: CurrentAdmin,
    service: Annotated[AbstractMediaService, Depends(get_media_service)],
    uow: Annotated[AbstractUnitOfWork, Depends(get_media_uow)],
) -> CreateUploadResponse:
    result = await service.create_upload(
        CreateUploadDTO(
            original_filename=payload.original_filename,
            media_type=payload.media_type,
            mime_type=payload.mime_type,
            file_size=payload.file_size,
            uploaded_by=admin.id,
        )
    )

    await uow.commit()

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return CreateUploadResponse(
        media_asset_id=result.media_asset_id,
        upload_url=result.upload_url,
        upload_params=result.upload_params,
    )
