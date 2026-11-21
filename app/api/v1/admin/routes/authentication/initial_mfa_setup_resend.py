from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.database.dependencies import get_uow
from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.policies import RateLimitPolicyName
from app.modules.authentication.contracts.services.initial_mfa_setup_resend import (
    AbstractInitialMFASetupResendService,
)
from app.modules.authentication.dependencies.initial_mfa_setup_resend import (
    get_initial_mfa_setup_resend_service,
)
from app.modules.authentication.schemas.initial_mfa_setup_resend import (
    InitialMFASetupResendRequest,
    InitialMFASetupResendResponse,
)

router = APIRouter()

GENERIC_RESPONSE_MESSAGE = "If the account is eligible, a new setup email will be sent."


@router.post(
    "/initial-mfa-setup/resend",
    response_model=InitialMFASetupResendResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(rate_limit(RateLimitPolicyName.INITIAL_MFA_SETUP)),
    ],
)
async def resend_initial_mfa_setup(
    payload: InitialMFASetupResendRequest,
    response: Response,
    service: Annotated[
        AbstractInitialMFASetupResendService,
        Depends(get_initial_mfa_setup_resend_service),
    ],
    uow: Annotated[AbstractUnitOfWork, Depends(get_uow)],
) -> InitialMFASetupResendResponse:
    await service.resend(str(payload.email))

    await uow.commit()

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return InitialMFASetupResendResponse(
        message=GENERIC_RESPONSE_MESSAGE,
    )
