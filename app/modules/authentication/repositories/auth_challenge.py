import uuid
from datetime import datetime
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult

from app.core.database.repositories.base import BaseRepository
from app.modules.authentication.contracts.repositories.auth_challenge import (
    AbstractAuthChallengeRepository,
)
from app.modules.authentication.enums.challenge_type import ChallengeType
from app.modules.authentication.models.auth_challenge import AuthChallenge


class AuthChallengeRepository(
    BaseRepository[AuthChallenge],
    AbstractAuthChallengeRepository,
):
    async def get_by_token_hash(
        self,
        token_hash: str,
        challenge_type: ChallengeType,
        *,
        for_update: bool = False,
    ) -> AuthChallenge | None:
        statement = select(AuthChallenge).where(
            AuthChallenge.challenge_token_hash == token_hash,
            AuthChallenge.challenge_type == challenge_type,
        )

        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_pending_by_user_and_type(
        self,
        admin_user_id: uuid.UUID,
        challenge_type: ChallengeType,
        *,
        for_update: bool = False,
    ) -> list[AuthChallenge]:
        statement = (
            select(AuthChallenge)
            .where(
                AuthChallenge.admin_user_id == admin_user_id,
                AuthChallenge.challenge_type == challenge_type,
                AuthChallenge.consumed_at.is_(None),
            )
            .order_by(AuthChallenge.created_at, AuthChallenge.id)
        )

        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def invalidate_pending_by_user_and_type(
        self,
        admin_user_id: uuid.UUID,
        challenge_type: ChallengeType,
        consumed_at: datetime,
    ) -> int:
        statement = (
            update(AuthChallenge)
            .where(
                AuthChallenge.admin_user_id == admin_user_id,
                AuthChallenge.challenge_type == challenge_type,
                AuthChallenge.consumed_at.is_(None),
            )
            .values(consumed_at=consumed_at)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return cast(CursorResult, result).rowcount

    async def consume(self, challenge_id: uuid.UUID, now: datetime) -> bool:
        """Atomically consume a usable challenge. True only for the one caller that wins."""
        statement = (
            update(AuthChallenge)
            .where(
                AuthChallenge.id == challenge_id,
                AuthChallenge.consumed_at.is_(None),
                AuthChallenge.expires_at > now,
                AuthChallenge.failed_attempts < AuthChallenge.max_attempts,
            )
            .values(consumed_at=now)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return cast(CursorResult, result).rowcount == 1

    async def increment_failed_attempts(self, challenge_id: uuid.UUID) -> int | None:
        """Atomically add one failed attempt. Returns the new count, or None if not usable."""
        statement = (
            update(AuthChallenge)
            .where(
                AuthChallenge.id == challenge_id,
                AuthChallenge.consumed_at.is_(None),
                AuthChallenge.failed_attempts < AuthChallenge.max_attempts,
            )
            .values(failed_attempts=AuthChallenge.failed_attempts + 1)
            .returning(AuthChallenge.failed_attempts)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
