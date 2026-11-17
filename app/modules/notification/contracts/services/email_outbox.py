from abc import abstractmethod

from app.core.contracts.services.service import AbstractService
from app.modules.notification.dtos.email_outbox import (
    EmailDeliveryResultDTO,
    EnqueueEmailDTO,
)


class AbstractEmailOutboxService(AbstractService):
    @abstractmethod
    async def enqueue(
        self,
        data: EnqueueEmailDTO,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def process_batch(
        self,
        *,
        limit: int = 20,
    ) -> list[EmailDeliveryResultDTO]:
        raise NotImplementedError
