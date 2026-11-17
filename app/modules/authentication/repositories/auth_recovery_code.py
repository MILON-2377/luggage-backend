import uuid
from datetime import datetime
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult

from app.core.database.repositories.base import BaseRepository
from app.modules.authentication.contracts.repositories.auth_recovery_code import (
    AbstractAuthRecoveryCodeRepository,
)
from app.modules.authentication.models.auth_recovery_code import AuthRecoveryCode


class AuthRecoveryCodeRepository(
    BaseRepository[AuthRecoveryCode],
    AbstractAuthRecoveryCodeRepository,
):
    async def get_available_by_admin_user_id(
        self,
        admin_user_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> list[AuthRecoveryCode]:
        statement = (
            select(AuthRecoveryCode)
            .where(
                AuthRecoveryCode.admin_user_id == admin_user_id,
                AuthRecoveryCode.used_at.is_(None),
                AuthRecoveryCode.revoked_at.is_(None),
            )
            .order_by(AuthRecoveryCode.created_at, AuthRecoveryCode.id)
        )

        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_available_by_code_hash(
        self,
        admin_user_id: uuid.UUID,
        code_hash: str,
        *,
        for_update: bool = False,
    ) -> AuthRecoveryCode | None:
        statement = select(AuthRecoveryCode).where(
            AuthRecoveryCode.admin_user_id == admin_user_id,
            AuthRecoveryCode.code_hash == code_hash,
            AuthRecoveryCode.used_at.is_(None),
            AuthRecoveryCode.revoked_at.is_(None),
        )

        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def consume(
        self,
        admin_user_id: uuid.UUID,
        code_hash: str,
        used_at: datetime,
    ) -> bool:
        statement = (
            update(AuthRecoveryCode)
            .where(
                AuthRecoveryCode.admin_user_id == admin_user_id,
                AuthRecoveryCode.code_hash == code_hash,
                AuthRecoveryCode.used_at.is_(None),
                AuthRecoveryCode.revoked_at.is_(None),
            )
            .values(used_at=used_at)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return cast(CursorResult, result).rowcount == 1

    async def revoke_all_available_by_admin_user_id(
        self,
        admin_user_id: uuid.UUID,
        revoked_at: datetime,
    ) -> int:
        statement = (
            update(AuthRecoveryCode)
            .where(
                AuthRecoveryCode.admin_user_id == admin_user_id,
                AuthRecoveryCode.used_at.is_(None),
                AuthRecoveryCode.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return cast(CursorResult, result).rowcount
