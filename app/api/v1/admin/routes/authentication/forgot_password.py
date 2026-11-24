from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.policies import RateLimitPolicyName
from app.modules.authentication.contracts.services.forgot_password import (
    AbstractForgotPasswordService,
)
from app.modules.authentication.dependencies.forgot_password import (
    get_forgot_password_service,
)
from app.modules.authentication.dependencies.uow import get_auth_uow
from app.modules.authentication.schemas.forgot_password import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
)

router = APIRouter()


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(rate_limit(RateLimitPolicyName.AUTHENTICATION)),
    ],
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    response: Response,
    service: Annotated[
        AbstractForgotPasswordService,
        Depends(get_forgot_password_service),
    ],
    uow: Annotated[
        AbstractUnitOfWork,
        Depends(get_auth_uow),
    ],
) -> ForgotPasswordResponse:
    await service.request_password_reset(str(payload.email))
    await uow.commit()

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return ForgotPasswordResponse()