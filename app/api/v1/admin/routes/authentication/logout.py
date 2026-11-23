from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.database.dependencies import get_uow
from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.policies import RateLimitPolicyName
from app.integrations.security.cookie_service import CookieService
from app.modules.authentication.contracts.services.logout import (
    AbstractLogoutService,
)
from app.modules.authentication.dependencies.cookie import get_cookie_service
from app.modules.authentication.dependencies.logout import get_logout_service
from app.modules.authentication.schemas.logout import LogoutResponse

router = APIRouter()


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(rate_limit(RateLimitPolicyName.AUTHENTICATION)),
    ],
)
async def logout(
    request: Request,
    response: Response,
    service: Annotated[
        AbstractLogoutService,
        Depends(get_logout_service),
    ],
    cookie_service: Annotated[
        CookieService,
        Depends(get_cookie_service),
    ],
    uow: Annotated[AbstractUnitOfWork, Depends(get_uow)],
) -> LogoutResponse:
    refresh_token = cookie_service.get_refresh_token(request)

    result = await service.logout(refresh_token)

    await uow.commit()

    cookie_service.clear_auth_cookies(response)

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return LogoutResponse(
        authenticated=result.authenticated,
        message=result.message,
    )