from abc import ABC, abstractmethod

from app.modules.media.dtos.cleanup import MediaCleanupResultDTO


class AbstractMediaCleanupService(ABC):
    @abstractmethod
    async def run(self) -> MediaCleanupResultDTO:
        raise NotImplementedError