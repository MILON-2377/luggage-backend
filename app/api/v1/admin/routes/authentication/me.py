from fastapi import APIRouter, Depends, Response, status

from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.policies import RateLimitPolicyName
from app.modules.authentication.dependencies.current_admin import CurrentAdmin
from app.modules.authentication.schemas.me import AdminMeResponse

router = APIRouter()


@router.get(
    "/me",
    response_model=AdminMeResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(rate_limit(RateLimitPolicyName.AUTHENTICATED_API)),
    ],
)
async def get_me(
    response: Response,
    admin_user: CurrentAdmin,
) -> AdminMeResponse:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return AdminMeResponse.model_validate(admin_user)