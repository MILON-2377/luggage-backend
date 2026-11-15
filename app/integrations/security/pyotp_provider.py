import hashlib

import pyotp

from app.core.contracts.security.totp_provider import TOTPProvider


class PyOTPProvider(TOTPProvider):
    def generate_secret(self) -> str:
        return pyotp.random_base32()

    def generate_provisioning_uri(
        self,
        secret: str,
        account_name: str,
        issuer_name: str,
    ) -> str:
        totp = pyotp.TOTP(
            secret,
            digits=6,
            interval=30,
            digest=hashlib.sha1,
        )

        return totp.provisioning_uri(
            name=account_name,
            issuer_name=issuer_name,
        )

    def verify_code(
        self,
        secret: str,
        code: str,
        valid_window: int = 0,
    ) -> bool:
        if not code.isdigit() or len(code) != 6:
            return False

        totp = pyotp.TOTP(
            secret,
            digits=6,
            interval=30,
            digest=hashlib.sha1,
        )

        return totp.verify(
            code,
            valid_window=valid_window,
        )
