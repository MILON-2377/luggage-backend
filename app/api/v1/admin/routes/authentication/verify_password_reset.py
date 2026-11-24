from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.policies import RateLimitPolicyName
from app.modules.authentication.contracts.services.verify_password_reset import (
    AbstractVerifyPasswordResetService,
)
from app.modules.authentication.dependencies.verify_password_reset import (
    get_verify_password_reset_service,
)
from app.modules.authentication.schemas.verify_password_reset import (
    VerifyPasswordResetRequest,
    VerifyPasswordResetResponse,
)

router = APIRouter()


@router.post(
    "/reset-password/verify",
    response_model=VerifyPasswordResetResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(rate_limit(RateLimitPolicyName.AUTHENTICATION)),
    ],
)
async def verify_password_reset(
    payload: VerifyPasswordResetRequest,
    response: Response,
    service: Annotated[
        AbstractVerifyPasswordResetService,
        Depends(get_verify_password_reset_service),
    ],
) -> VerifyPasswordResetResponse:
    result = await service.verify_password_reset_token(payload.token)

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return VerifyPasswordResetResponse(
        recovery_token=result.recovery_token,
    )