
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.database.dependencies import get_uow
from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.policies import RateLimitPolicyName
from app.modules.authentication.contracts.services.passkey_login import (
    AbstractPasskeyLoginOptionsService,
)
from app.modules.authentication.dependencies.passkey_login import (
    get_passkey_login_options_service,
)
from app.modules.authentication.dtos.passkey_login import (
    PasskeyLoginOptionsRequest as PasskeyLoginOptionsDTO,
)
from app.modules.authentication.schemas.passkey_login import (
    PasskeyLoginOptionsRequest,
    PasskeyLoginOptionsResponse,
)

router = APIRouter()


@router.post(
    "/login/passkey/options",
    response_model=PasskeyLoginOptionsResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit(RateLimitPolicyName.AUTHENTICATION))],
)
async def generate_passkey_login_options(
    payload: PasskeyLoginOptionsRequest,
    response: Response,
    service: Annotated[
        AbstractPasskeyLoginOptionsService,
        Depends(get_passkey_login_options_service),
    ],
    uow: Annotated[AbstractUnitOfWork, Depends(get_uow)],
) -> PasskeyLoginOptionsResponse:
    result = await service.generate_options(
        PasskeyLoginOptionsDTO(
            challenge_token=payload.challenge_token,
        )
    )

    await uow.commit()

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return PasskeyLoginOptionsResponse(
        public_key=result.public_key,
    )
