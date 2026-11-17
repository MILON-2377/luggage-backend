from abc import ABC, abstractmethod
from typing import Any


class AbstractIDGenerator(ABC):
    @abstractmethod
    def generate(self) -> Any:
        raise NotImplementedError
