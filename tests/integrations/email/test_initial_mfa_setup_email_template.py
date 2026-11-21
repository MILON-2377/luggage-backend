from app.modules.notification.dependencies.email_renderer import (
    get_email_renderer,
)


def test_initial_mfa_setup_email_template_renders_successfully() -> None:
    renderer = get_email_renderer()

    rendered = renderer.render(
        template_name="initial_mfa_setup",
        context={
            "app_name": "Manufacturer Portal",
            "setup_url": "https://example.com/dashboard#token=test-token",
            "recipient_email": "admin@example.com",
            "expires_in_minutes": 30,
        },
    )

    assert rendered.subject == ("Manufacturer Portal - Complete your initial MFA setup")

    assert "Complete MFA setup" in rendered.html_content
    assert "https://example.com/dashboard#token=test-token" in rendered.html_content
    assert "admin@example.com" in rendered.html_content
    assert "30 minutes" in rendered.html_content

    assert "Complete MFA setup" in rendered.text_content
    assert "https://example.com/dashboard#token=test-token" in rendered.text_content
    assert "admin@example.com" in rendered.text_content
    assert "30 minutes" in rendered.text_content
