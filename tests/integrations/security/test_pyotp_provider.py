import pyotp

from app.integrations.security.pyotp_provider import PyOTPProvider


def test_generate_secret() -> None:
    provider = PyOTPProvider()

    secret = provider.generate_secret()

    assert isinstance(secret, str)
    assert len(secret) == 32


def test_generate_provisioning_uri() -> None:
    provider = PyOTPProvider()
    secret = provider.generate_secret()

    uri = provider.generate_provisioning_uri(
        secret=secret,
        account_name="admin@example.com",
        issuer_name="B2B Manufacturer Platform",
    )

    assert uri.startswith("otpauth://totp/")
    assert "admin%40example.com" in uri
    assert "issuer=" in uri


def test_verify_valid_code() -> None:
    provider = PyOTPProvider()
    secret = provider.generate_secret()
    code = pyotp.TOTP(secret).now()

    assert provider.verify_code(secret, code)


def test_reject_invalid_code() -> None:
    provider = PyOTPProvider()
    secret = provider.generate_secret()

    assert not provider.verify_code(secret, "invalid")
