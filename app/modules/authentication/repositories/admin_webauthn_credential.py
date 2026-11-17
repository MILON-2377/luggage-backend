import uuid
from datetime import datetime
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult

from app.core.database.repositories.base import BaseRepository
from app.modules.authentication.contracts.repositories.admin_webauthn_credential import (
    AbstractAdminWebauthnCredentialRepository,
)
from app.modules.authentication.models.admin_webauthn_credential import (
    AdminWebauthnCredential,
)


class AdminWebauthnCredentialRepository(
    BaseRepository[AdminWebauthnCredential],
    AbstractAdminWebauthnCredentialRepository,
):
    async def get_by_credential_id(
        self,
        credential_id: bytes,
        *,
        for_update: bool = False,
    ) -> AdminWebauthnCredential | None:
        statement = select(AdminWebauthnCredential).where(
            AdminWebauthnCredential.credential_id == credential_id,
            AdminWebauthnCredential.revoked_at.is_(None),
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
    ) -> list[AdminWebauthnCredential]:
        statement = (
            select(AdminWebauthnCredential)
            .where(
                AdminWebauthnCredential.admin_user_id == admin_user_id,
                AdminWebauthnCredential.revoked_at.is_(None),
            )
            .order_by(
                AdminWebauthnCredential.created_at,
                AdminWebauthnCredential.id,
            )
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_active_by_id_and_admin_user_id(
        self,
        credential_pk: uuid.UUID,
        admin_user_id: uuid.UUID,
    ) -> AdminWebauthnCredential | None:
        statement = select(AdminWebauthnCredential).where(
            AdminWebauthnCredential.id == credential_pk,
            AdminWebauthnCredential.admin_user_id == admin_user_id,
            AdminWebauthnCredential.revoked_at.is_(None),
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def record_successful_use(
        self,
        credential_pk: uuid.UUID,
        new_sign_count: int,
        used_at: datetime,
        *,
        backup_state: bool | None = None,
    ) -> bool:
        values: dict[str, object] = {
            "sign_count": new_sign_count,
            "last_used_at": used_at,
        }
        if backup_state is not None:
            values["backup_state"] = backup_state

        statement = (
            update(AdminWebauthnCredential)
            .where(
                AdminWebauthnCredential.id == credential_pk,
                AdminWebauthnCredential.revoked_at.is_(None),
                (AdminWebauthnCredential.sign_count == 0)
                | (AdminWebauthnCredential.sign_count < new_sign_count),
            )
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return cast(CursorResult, result).rowcount == 1

    async def revoke(
        self,
        credential_pk: uuid.UUID,
        revoked_at: datetime,
    ) -> bool:
        statement = (
            update(AdminWebauthnCredential)
            .where(
                AdminWebauthnCredential.id == credential_pk,
                AdminWebauthnCredential.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return cast(CursorResult, result).rowcount == 1
