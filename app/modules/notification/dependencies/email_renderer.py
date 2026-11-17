from functools import lru_cache
from pathlib import Path

from app.integrations.email.template_renderer import Jinja2EmailTemplateRenderer

# Navigate up from dependencies -> notification -> modules -> app -> templates/email
TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates" / "email"


@lru_cache
def get_email_renderer() -> Jinja2EmailTemplateRenderer:
    return Jinja2EmailTemplateRenderer(TEMPLATES_DIR)