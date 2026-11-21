from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.database.dependencies import get_uow
from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.policies import RateLimitPolicyName
from app.modules.authentication.contracts.services.initial_totp_enrollment import (
    AbstractInitialTOTPEnrollmentService,
)
from app.modules.authentication.dependencies.initial_totp_enrollment import (
    get_initial_totp_enrollment_service,
)
from app.modules.authentication.schemas.totp_enrollment import (
    TOTPEnrollmentRequest,
    TOTPEnrollmentResponse,
)

router = APIRouter()


@router.post(
    "/initial-mfa-setup/totp/enroll",
    response_model=TOTPEnrollmentResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(rate_limit(RateLimitPolicyName.INITIAL_MFA_SETUP)),
    ],
)
async def enroll_initial_totp(
    payload: TOTPEnrollmentRequest,
    response: Response,
    service: Annotated[
        AbstractInitialTOTPEnrollmentService,
        Depends(get_initial_totp_enrollment_service),
    ],
    uow: Annotated[AbstractUnitOfWork, Depends(get_uow)],
) -> TOTPEnrollmentResponse:
    result = await service.enroll(payload.enrollment_token)

    await uow.commit()

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return TOTPEnrollmentResponse(
        secret=result.secret,
        provisioning_uri=result.provisioning_uri,
        expires_at=result.expires_at,
    )
