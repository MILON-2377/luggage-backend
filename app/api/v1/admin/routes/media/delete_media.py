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

router = APIRouter()


@router.delete(
    "/{media_asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    # dependencies=[
    #     Depends(rate_limit(RateLimitPolicyName.AUTHENTICATED_API)),
    # ],
)
async def delete_media(
    media_asset_id: uuid.UUID,
    _admin: CurrentAdmin,
    service: Annotated[AbstractMediaService, Depends(get_media_service)],
    uow: Annotated[AbstractUnitOfWork, Depends(get_media_uow)],
) -> Response:
    await service.delete(media_asset_id)

    await uow.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
