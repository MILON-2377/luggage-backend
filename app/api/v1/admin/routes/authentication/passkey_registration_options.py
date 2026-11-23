from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.policies import RateLimitPolicyName
from app.modules.authentication.contracts.services.passkey_registration import (
    AbstractPasskeyRegistrationService,
)
from app.modules.authentication.dependencies.passkey_registration import (
    get_passkey_registration_service,
)
from app.modules.authentication.dependencies.uow import get_auth_uow
from app.modules.authentication.schemas.passkey_registration import (
    PasskeyRegistrationOptionsRequest,
    PasskeyRegistrationOptionsResponse,
)

router = APIRouter()


@router.post(
    "/mfa/passkey/registration/options",
    response_model=PasskeyRegistrationOptionsResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(rate_limit(RateLimitPolicyName.INITIAL_MFA_SETUP)),
    ],
)
async def generate_passkey_registration_options(
    payload: PasskeyRegistrationOptionsRequest,
    response: Response,
    service: Annotated[
        AbstractPasskeyRegistrationService,
        Depends(get_passkey_registration_service),
    ],
    uow: Annotated[AbstractUnitOfWork, Depends(get_auth_uow)],
) -> PasskeyRegistrationOptionsResponse:
    result = await service.generate_registration_options(
        enrollment_token=payload.enrollment_token.get_secret_value(),
    )

    await uow.commit()

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return PasskeyRegistrationOptionsResponse(
        options=result.options,
    )