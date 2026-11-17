from abc import abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

from app.core.contracts.database.repository import AbstractRepository

if TYPE_CHECKING:
    from app.modules.notification.models.email_outbox import EmailOutbox


class AbstractEmailOutboxRepository(AbstractRepository):
    @abstractmethod
    def create(self, email_outbox: "EmailOutbox") -> None:
        raise NotImplementedError

    @abstractmethod
    async def claim_batch(
        self,
        *,
        now: datetime,
        lease_expires_before: datetime,
        limit: int,
    ) -> list["EmailOutbox"]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(
        self,
        email_outbox_id: object,
        *,
        for_update: bool = False,
    ) -> "EmailOutbox | None":
        raise NotImplementedError
