from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.database.dependencies import get_uow
from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.policies import RateLimitPolicyName
from app.modules.authentication.contracts.services.login import (
    AbstractLoginService,
)
from app.modules.authentication.dependencies.login import get_login_service
from app.modules.authentication.schemas.login import (
    LoginRequest,
    LoginResponse,
)

router = APIRouter()


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(rate_limit(RateLimitPolicyName.AUTHENTICATION)),
    ],
)
async def login(
    payload: LoginRequest,
    response: Response,
    service: Annotated[
        AbstractLoginService,
        Depends(get_login_service),
    ],
    uow: Annotated[AbstractUnitOfWork, Depends(get_uow)],
) -> LoginResponse:
    result = await service.login(payload)

    await uow.commit()

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return LoginResponse(
        challenge_token=result.challenge_token,
        expires_at=result.expires_at,
        available_mfa_methods=result.available_mfa_methods,
    )