from fastapi import APIRouter, Depends

from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.policies import RateLimitPolicyName

router = APIRouter(tags=["Health"])


@router.get(
    "/health/live", dependencies=[Depends(rate_limit(RateLimitPolicyName.PUBLIC_API))]
)
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "message": "Application is running",
    }
