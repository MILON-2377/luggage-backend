from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.database.dependencies import get_uow
from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.policies import RateLimitPolicyName
from app.integrations.security.cookie_service import CookieService
from app.modules.authentication.contracts.services.refresh import (
    AbstractRefreshService,
)
from app.modules.authentication.dependencies.cookie import get_cookie_service
from app.modules.authentication.dependencies.refresh import get_refresh_service

router = APIRouter()


@router.post(
    "/refresh",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(rate_limit(RateLimitPolicyName.AUTHENTICATION)),
    ],
)
async def refresh_authentication(
    request: Request,
    response: Response,
    cookie_service: Annotated[
        CookieService,
        Depends(get_cookie_service),
    ],
    refresh_service: Annotated[
        AbstractRefreshService,
        Depends(get_refresh_service),
    ],
    uow: Annotated[AbstractUnitOfWork, Depends(get_uow)],
) -> None:
    refresh_token = cookie_service.get_refresh_token(request)

    if refresh_token is None:
        from app.modules.authentication.errors.refresh import (
            InvalidRefreshTokenError,
        )

        raise InvalidRefreshTokenError()

    result = await refresh_service.refresh(refresh_token)

    await uow.commit()

    cookie_service.set_auth_cookies(
        response,
        access_token=result.access_token.get_secret_value(),
        refresh_token=result.refresh_token.get_secret_value(),
    )

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
