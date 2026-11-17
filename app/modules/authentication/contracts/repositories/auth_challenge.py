import uuid
from abc import abstractmethod
from datetime import datetime

from app.core.contracts.database.repository import AbstractRepository
from app.modules.authentication.enums.challenge_type import ChallengeType
from app.modules.authentication.models.auth_challenge import AuthChallenge


class AbstractAuthChallengeRepository(AbstractRepository):
    @abstractmethod
    async def get_by_token_hash(
        self,
        token_hash: str,
        challenge_type: ChallengeType,
        *,
        for_update: bool = False,
    ) -> AuthChallenge | None:
        raise NotImplementedError

    @abstractmethod
    async def get_pending_by_user_and_type(
        self,
        admin_user_id: uuid.UUID,
        challenge_type: ChallengeType,
        *,
        for_update: bool = False,
    ) -> list[AuthChallenge]:
        raise NotImplementedError

    @abstractmethod
    def create(self, challenge: AuthChallenge) -> None:
        raise NotImplementedError

    @abstractmethod
    async def invalidate_pending_by_user_and_type(
        self,
        admin_user_id: uuid.UUID,
        challenge_type: ChallengeType,
        consumed_at: datetime,
    ) -> int:
        raise NotImplementedError
