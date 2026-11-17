from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmailMessage:
    recipient: str
    subject: str
    html_content: str
    text_content: str | None = None


class AbstractEmailProvider(ABC):
    @abstractmethod
    async def send(self, message: EmailMessage) -> None:
        raise NotImplementedError
