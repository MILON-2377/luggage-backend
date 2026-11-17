import uuid
from datetime import datetime
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult

from app.core.database.repositories.base import BaseRepository
from app.modules.authentication.contracts.repositories.admin_totp_credential import (
    AbstractAdminTotpCredentialRepository,
)
from app.modules.authentication.models.admin_totp_credential import (
    AdminTotpCredential,
)


class AdminTotpCredentialRepository(
    BaseRepository[AdminTotpCredential],
    AbstractAdminTotpCredentialRepository,
):
    async def get_active_by_admin_user_id(
        self,
        admin_user_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> AdminTotpCredential | None:
        statement = select(AdminTotpCredential).where(
            AdminTotpCredential.admin_user_id == admin_user_id,
            AdminTotpCredential.verified_at.is_not(None),
            AdminTotpCredential.revoked_at.is_(None),
        )

        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_unrevoked_by_admin_user_id(
        self,
        admin_user_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> AdminTotpCredential | None:
        statement = select(AdminTotpCredential).where(
            AdminTotpCredential.admin_user_id == admin_user_id,
            AdminTotpCredential.revoked_at.is_(None),
        )

        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def mark_verified(
        self,
        credential_id: uuid.UUID,
        verified_at: datetime,
    ) -> bool:
        statement = (
            update(AdminTotpCredential)
            .where(
                AdminTotpCredential.id == credential_id,
                AdminTotpCredential.verified_at.is_(None),
                AdminTotpCredential.revoked_at.is_(None),
            )
            .values(verified_at=verified_at)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return cast(CursorResult, result).rowcount == 1

    async def record_successful_use(
        self,
        credential_id: uuid.UUID,
        time_step: int,
        used_at: datetime,
    ) -> bool:
        statement = (
            update(AdminTotpCredential)
            .where(
                AdminTotpCredential.id == credential_id,
                AdminTotpCredential.verified_at.is_not(None),
                AdminTotpCredential.revoked_at.is_(None),
                (AdminTotpCredential.last_used_time_step.is_(None))
                | (AdminTotpCredential.last_used_time_step < time_step),
            )
            .values(last_used_time_step=time_step, last_used_at=used_at)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return cast(CursorResult, result).rowcount == 1

    async def revoke(
        self,
        credential_id: uuid.UUID,
        revoked_at: datetime,
    ) -> bool:
        statement = (
            update(AdminTotpCredential)
            .where(
                AdminTotpCredential.id == credential_id,
                AdminTotpCredential.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return cast(CursorResult, result).rowcount == 1
