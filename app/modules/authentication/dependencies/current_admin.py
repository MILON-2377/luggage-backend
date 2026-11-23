from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.modules.authentication.contracts.repositories.admin_session import (
    AbstractAdminSessionRepository,
)
from app.modules.authentication.contracts.repositories.admin_user import (
    AbstractAdminUserRepository,
)
from app.modules.authentication.dependencies.uow import get_auth_uow
from app.modules.authentication.enums import AdminUserStatus
from app.modules.authentication.models import AdminUser


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Cookie"},
    )


async def get_current_admin(
    request: Request,
    uow: Annotated[AbstractUnitOfWork, Depends(get_auth_uow)],
) -> AdminUser:
    user_id = getattr(request.state, "authenticated_user_id", None)
    session_id = getattr(request.state, "authenticated_session_id", None)

    if not isinstance(user_id, UUID) or not isinstance(session_id, UUID):
        raise _unauthorized("Authentication required.")

    session_repository = uow.get_repository(AbstractAdminSessionRepository)
    user_repository = uow.get_repository(AbstractAdminUserRepository)

    session = await session_repository.get_by_id(session_id)
    now = datetime.now(UTC)

    if (
        session is None
        or session.admin_user_id != user_id
        or session.revoked_at is not None
        or session.expires_at <= now
    ):
        raise _unauthorized("Invalid or expired authentication session.")

    admin_user = await user_repository.get_by_id_with_profile(user_id)

    if admin_user is None or admin_user.status != AdminUserStatus.ACTIVE:
        raise _unauthorized("Admin account is not active.")

    return admin_user


CurrentAdmin = Annotated[AdminUser, Depends(get_current_admin)]