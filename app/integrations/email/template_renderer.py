import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    TemplateError,
    select_autoescape,
)

from app.core.contracts.email.template_renderer import (
    AbstractEmailTemplateRenderer,
    RenderedEmail,
)
from app.integrations.email.errors import EmailTemplateError

logger = logging.getLogger(__name__)


class Jinja2EmailTemplateRenderer(AbstractEmailTemplateRenderer):
    def __init__(self, templates_dir: Path) -> None:
        self._env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(
                enabled_extensions=("html.j2", "html", "htm"),
                default_for_string=False,
                default=False,
            ),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(
        self,
        template_name: str,
        context: Mapping[str, Any],
    ) -> RenderedEmail:
        try:
            subject = self._render(
                f"{template_name}.subject.txt.j2",
                context,
            )
            html_content = self._render(
                f"{template_name}.html.j2",
                context,
            )
            text_content = self._render(
                f"{template_name}.txt.j2",
                context,
            )
        except TemplateError as exc:
            logger.error(
                "Email template failed: name=%s error_type=%s",
                template_name,
                type(exc).__name__,
            )
            raise EmailTemplateError from exc

        subject = " ".join(subject.split())

        return RenderedEmail(
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def _render(
        self,
        name: str,
        context: Mapping[str, Any],
    ) -> str:
        return self._env.get_template(name).render(**context).strip()
