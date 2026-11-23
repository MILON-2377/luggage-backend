from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.policies import RateLimitPolicyName
from app.integrations.security.cookie_service import CookieService
from app.modules.authentication.contracts.services.passkey_login_verify import (
    AbstractPasskeyLoginVerifyService,
)
from app.modules.authentication.dependencies.cookie import get_cookie_service
from app.modules.authentication.dependencies.passkey_login_verify import (
    get_passkey_login_verify_service,
)
from app.modules.authentication.dependencies.uow import get_auth_uow
from app.modules.authentication.schemas.passkey_login_verify import (
    PasskeyLoginVerifyRequest,
    PasskeyLoginVerifyResponse,
)

router = APIRouter(prefix="/login/passkey")


@router.post(
    "/verify",
    response_model=PasskeyLoginVerifyResponse,
    status_code=status.HTTP_200_OK,
      dependencies=[
            Depends(rate_limit(RateLimitPolicyName.AUTHENTICATION)),
        ],
)
async def verify_passkey_login(
    payload: PasskeyLoginVerifyRequest,
    response: Response,
    service: Annotated[
        AbstractPasskeyLoginVerifyService,
        Depends(get_passkey_login_verify_service),
    ],
    cookie_service: Annotated[
        CookieService,
        Depends(get_cookie_service),
    ],
    uow: Annotated[
        AbstractUnitOfWork,
        Depends(get_auth_uow),
    ],
) -> PasskeyLoginVerifyResponse:
    result = await service.verify(payload)

    await uow.commit()

    cookie_service.set_auth_cookies(
        response=response,
        access_token=result.access_token.get_secret_value(),
        refresh_token=result.refresh_token.get_secret_value(),
    )

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return PasskeyLoginVerifyResponse(
        authenticated=True,
        message="Login successful",
    )