from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RenderedEmail:
    subject: str
    html_content: str
    text_content: str


class AbstractEmailTemplateRenderer(ABC):
    @abstractmethod
    def render(
        self,
        template_name: str,
        context: Mapping[str, Any],
    ) -> RenderedEmail: ...
