from pathlib import Path

import pytest

from app.integrations.email.errors import EmailTemplateError
from app.integrations.email.template_renderer import Jinja2EmailTemplateRenderer

TEMPLATES_DIR = (
    Path(__file__).parents[3]
    / "app"
    / "templates"
    / "email"
)

CONTEXT = {
    "app_name": "Showroom",
    "invitation_url": "https://app.example.com/accept?token=abc",
    "recipient_email": "user@example.com",
    "expires_in_hours": 24,
}


@pytest.fixture
def renderer() -> Jinja2EmailTemplateRenderer:
    return Jinja2EmailTemplateRenderer(TEMPLATES_DIR)


def test_renders_all_parts(renderer: Jinja2EmailTemplateRenderer) -> None:
    rendered = renderer.render("account_invitation", CONTEXT)

    assert rendered.subject == "You've been invited to Showroom"
    assert CONTEXT["invitation_url"] in rendered.html_content
    assert CONTEXT["invitation_url"] in rendered.text_content


def test_html_is_escaped_but_text_is_not(
    renderer: Jinja2EmailTemplateRenderer,
) -> None:
    rendered = renderer.render(
        "account_invitation",
        {**CONTEXT, "recipient_email": "<script>x</script>@example.com"},
    )

    assert "<script>" not in rendered.html_content
    assert "&lt;script&gt;" in rendered.html_content
    assert "<script>" in rendered.text_content


def test_html_attribute_values_are_escaped(
    renderer: Jinja2EmailTemplateRenderer,
) -> None:
    rendered = renderer.render(
        "account_invitation",
        {
            **CONTEXT,
            "invitation_url": 'https://example.com/?x="><script>alert(1)</script>',
        },
    )

    assert 'href="https://example.com/?x=' in rendered.html_content
    assert "<script>" not in rendered.html_content
    assert "&lt;script&gt;" in rendered.html_content


def test_subject_is_normalized_to_single_line(
    renderer: Jinja2EmailTemplateRenderer,
) -> None:
    rendered = renderer.render(
        "account_invitation",
        {**CONTEXT, "app_name": "Show\r\nBcc: evil@example.com"},
    )

    assert "\n" not in rendered.subject
    assert "\r" not in rendered.subject
    assert "Bcc: evil@example.com" in rendered.subject


def test_missing_variable_fails_loudly(
    renderer: Jinja2EmailTemplateRenderer,
) -> None:
    with pytest.raises(EmailTemplateError):
        renderer.render("account_invitation", {"app_name": "Showroom"})


def test_unknown_template_fails(
    renderer: Jinja2EmailTemplateRenderer,
) -> None:
    with pytest.raises(EmailTemplateError):
        renderer.render("does_not_exist", CONTEXT)
