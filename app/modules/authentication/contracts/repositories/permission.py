from abc import abstractmethod

from app.core.contracts.database.repository import AbstractRepository
from app.modules.authentication.models.permission import Permission


class AbstractPermissionRepository(AbstractRepository):
    @abstractmethod
    async def get_by_code(self, code: str) -> Permission | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_codes(self, codes: list[str]) -> list[Permission]:
        raise NotImplementedError

    @abstractmethod
    def create(self, permission: Permission) -> None:
        raise NotImplementedError
