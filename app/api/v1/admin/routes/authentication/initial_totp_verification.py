from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.database.dependencies import get_uow
from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.policies import RateLimitPolicyName
from app.modules.authentication.contracts.services.initial_totp_verification import (
    AbstractInitialTOTPVerificationService,
)
from app.modules.authentication.dependencies.initial_totp_verification import (
    get_initial_totp_verification_service,
)
from app.modules.authentication.errors.initial_totp_verification import (
    InvalidTOTPVerificationCodeError,
)
from app.modules.authentication.schemas.initial_totp_verification import (
    InitialTOTPVerificationRequest,
    InitialTOTPVerificationResponse,
)

router = APIRouter()


@router.post(
    "/initial-mfa-setup/totp/verify",
    response_model=InitialTOTPVerificationResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(rate_limit(RateLimitPolicyName.INITIAL_MFA_SETUP)),
    ],
)
async def verify_initial_totp(
    payload: InitialTOTPVerificationRequest,
    response: Response,
    service: Annotated[
        AbstractInitialTOTPVerificationService,
        Depends(get_initial_totp_verification_service),
    ],
    uow: Annotated[AbstractUnitOfWork, Depends(get_uow)],
) -> InitialTOTPVerificationResponse:
    try:
        result = await service.verify(
            enrollment_token=payload.enrollment_token.get_secret_value(),
            code=payload.code.get_secret_value(),
        )
    except InvalidTOTPVerificationCodeError:
        await uow.commit()
        raise

    await uow.commit()

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return InitialTOTPVerificationResponse(
        recovery_codes=list(result.recovery_codes),
    )
