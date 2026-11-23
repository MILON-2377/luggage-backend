from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.policies import RateLimitPolicyName
from app.integrations.security.cookie_service import CookieService
from app.modules.authentication.contracts.services.totp_login_verify import (
    AbstractTotpLoginVerifyService,
)
from app.modules.authentication.dependencies.cookie import get_cookie_service
from app.modules.authentication.dependencies.totp_login_verify import (
    get_totp_login_verify_service,
)
from app.modules.authentication.dependencies.uow import get_auth_uow
from app.modules.authentication.schemas.totp_login_verify import (
    TotpLoginVerifyRequest,
    TotpLoginVerifyResponse,
)

router = APIRouter()


@router.post(
    "/login/totp/verify",
    response_model=TotpLoginVerifyResponse,
    status_code=status.HTTP_200_OK,
         dependencies=[
            Depends(rate_limit(RateLimitPolicyName.AUTHENTICATION)),
        ],
)
async def verify_totp_login(
    payload: TotpLoginVerifyRequest,
    response: Response,
    service: Annotated[
        AbstractTotpLoginVerifyService,
        Depends(get_totp_login_verify_service),
    ],
    cookie_service: Annotated[
        CookieService,
        Depends(get_cookie_service),
    ],
    uow: Annotated[
        AbstractUnitOfWork,
        Depends(get_auth_uow),
    ],
) -> TotpLoginVerifyResponse:
    result = await service.verify(payload)

    await uow.commit()

    cookie_service.set_auth_cookies(
        response=response,
        access_token=result.access_token.get_secret_value(),
        refresh_token=result.refresh_token.get_secret_value(),
    )

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return TotpLoginVerifyResponse(
        authenticated=True,
        message="Login successful",
    )