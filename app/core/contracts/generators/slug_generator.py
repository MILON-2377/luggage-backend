from abc import ABC, abstractmethod


class AbstractSlugGenerator(ABC):
    @abstractmethod
    def generate(self, value: str) -> str:
        raise NotImplementedError
