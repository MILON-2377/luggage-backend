from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.policies import RateLimitPolicyName
from app.integrations.security.cookie_service import CookieService
from app.modules.authentication.contracts.services.recovery_code_login_verify import (
    AbstractRecoveryCodeLoginVerifyService,
)
from app.modules.authentication.dependencies.cookie import get_cookie_service
from app.modules.authentication.dependencies.recovery_code_login_verify import (
    get_recovery_code_login_verify_service,
)
from app.modules.authentication.dependencies.uow import get_auth_uow
from app.modules.authentication.schemas.recovery_code_login_verify import (
    RecoveryCodeLoginVerifyRequest,
    RecoveryCodeLoginVerifyResponse,
)

router = APIRouter(tags=["Admin Authentication"])


@router.post(
    "/login/recovery-code/verify",
    response_model=RecoveryCodeLoginVerifyResponse,
    status_code=status.HTTP_200_OK,
        dependencies=[
        Depends(rate_limit(RateLimitPolicyName.AUTHENTICATION)),
    ],
)
async def verify_recovery_code_login(
    payload: RecoveryCodeLoginVerifyRequest,
    response: Response,
    service: Annotated[
        AbstractRecoveryCodeLoginVerifyService,
        Depends(get_recovery_code_login_verify_service),
    ],
    cookie_service: Annotated[
        CookieService,
        Depends(get_cookie_service),
    ],
    uow: Annotated[
        AbstractUnitOfWork,
        Depends(get_auth_uow),
    ],
) -> RecoveryCodeLoginVerifyResponse:
    result = await service.verify(payload)

    await uow.commit()

    cookie_service.set_auth_cookies(
        response=response,
        access_token=result.access_token.get_secret_value(),
        refresh_token=result.refresh_token.get_secret_value(),
    )

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return RecoveryCodeLoginVerifyResponse(
        authenticated=True,
        message="Login successful",
    )