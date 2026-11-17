import uuid
from datetime import datetime
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult

from app.core.database.repositories.base import BaseRepository
from app.modules.authentication.contracts.repositories.admin_session import (
    AbstractAdminSessionRepository,
)
from app.modules.authentication.enums.session_revocation_reason import (
    SessionRevocationReason,
)
from app.modules.authentication.models.admin_session import AdminSession


class AdminSessionRepository(
    BaseRepository[AdminSession],
    AbstractAdminSessionRepository,
):
    async def get_by_id(
        self,
        session_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> AdminSession | None:
        statement = select(AdminSession).where(
            AdminSession.id == session_id,
        )

        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_refresh_token_hash(
        self,
        refresh_token_hash: str,
        *,
        for_update: bool = False,
    ) -> AdminSession | None:
        statement = select(AdminSession).where(
            AdminSession.refresh_token_hash == refresh_token_hash,
        )

        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_active_by_admin_user_id(
        self,
        admin_user_id: uuid.UUID,
        now: datetime,
        *,
        for_update: bool = False,
    ) -> list[AdminSession]:
        statement = (
            select(AdminSession)
            .where(
                AdminSession.admin_user_id == admin_user_id,
                AdminSession.revoked_at.is_(None),
                AdminSession.expires_at > now,
            )
            .order_by(AdminSession.created_at, AdminSession.id)
        )

        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def revoke(
        self,
        session_id: uuid.UUID,
        revoked_at: datetime,
        reason: SessionRevocationReason,
    ) -> bool:
        statement = (
            update(AdminSession)
            .where(
                AdminSession.id == session_id,
                AdminSession.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at, revocation_reason=reason)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return cast(CursorResult, result).rowcount == 1

    async def revoke_all_active_by_admin_user_id(
        self,
        admin_user_id: uuid.UUID,
        revoked_at: datetime,
        reason: SessionRevocationReason,
        *,
        except_session_id: uuid.UUID | None = None,
    ) -> int:
        statement = (
            update(AdminSession)
            .where(
                AdminSession.admin_user_id == admin_user_id,
                AdminSession.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at, revocation_reason=reason)
            .execution_options(synchronize_session="fetch")
        )

        if except_session_id is not None:
            statement = statement.where(AdminSession.id != except_session_id)

        result = await self.session.execute(statement)
        return cast(CursorResult, result).rowcount

    async def touch_last_activity(
        self,
        session_id: uuid.UUID,
        now: datetime,
    ) -> bool:
        statement = (
            update(AdminSession)
            .where(
                AdminSession.id == session_id,
                AdminSession.revoked_at.is_(None),
                AdminSession.expires_at > now,
            )
            .values(last_activity_at=now)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return cast(CursorResult, result).rowcount == 1
