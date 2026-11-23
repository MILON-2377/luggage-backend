from typing import Annotated

from fastapi import Depends

from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.generators.uuid_generator import UUIDGenerator
from app.modules.authentication.contracts.services.complete_login import (
    AbstractCompleteLoginService,
)
from app.modules.authentication.contracts.services.session import (
    AbstractAdminSessionService,
)
from app.modules.authentication.contracts.services.token import (
    AbstractAuthenticationTokenService,
)
from app.modules.authentication.dependencies.session import (
    get_admin_session_service,
)
from app.modules.authentication.dependencies.token import (
    get_authentication_token_service,
)
from app.modules.authentication.services.complete_login import (
    CompleteLoginService,
)


def get_complete_login_service(
    token_service: Annotated[
        AbstractAuthenticationTokenService,
        Depends(get_authentication_token_service),
    ],
    session_service: Annotated[
        AbstractAdminSessionService,
        Depends(get_admin_session_service),
    ],
) -> AbstractCompleteLoginService:
    id_generator: AbstractIDGenerator = UUIDGenerator()

    return CompleteLoginService(
        id_generator=id_generator,
        token_service=token_service,
        session_service=session_service,
    )