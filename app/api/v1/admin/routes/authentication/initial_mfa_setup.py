from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.database.dependencies import get_uow
from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.policies import RateLimitPolicyName
from app.modules.authentication.contracts.services.initial_mfa_setup_authorization import (
    AbstractInitialMFASetupAuthorizationService,
)
from app.modules.authentication.dependencies.initial_mfa_setup import (
    get_initial_mfa_setup_authorization_service,
)
from app.modules.authentication.schemas.initial_mfa_setup import (
    InitialMFASetupRequest,
    InitialMFASetupResponse,
)

router = APIRouter()


@router.post(
    "/initial-mfa-setup",
    response_model=InitialMFASetupResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(rate_limit(RateLimitPolicyName.INITIAL_MFA_SETUP)),
    ],
)
async def authorize_initial_mfa_setup(
    payload: InitialMFASetupRequest,
    response: Response,
    service: Annotated[
        AbstractInitialMFASetupAuthorizationService,
        Depends(get_initial_mfa_setup_authorization_service),
    ],
    uow: Annotated[AbstractUnitOfWork, Depends(get_uow)],
) -> InitialMFASetupResponse:
    result = await service.authorize_initial_setup(
        payload.initial_setup_token.get_secret_value()
    )

    await uow.commit()

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return InitialMFASetupResponse(
        enrollment_token=result.enrollment_token,
        expires_at=result.expires_at,
    )
