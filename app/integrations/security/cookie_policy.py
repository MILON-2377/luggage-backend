
from typing import Literal, TypedDict

from app.core.config import Settings


class CookieOptions(TypedDict):
    httponly: bool
    secure: bool
    samesite: Literal["lax", "strict", "none"]
    path: str
    max_age: int


class CookiePolicy:
    def __init__(self, settings: Settings) -> None:
        self._access_token_name = settings.ACCESS_TOKEN_COOKIE_NAME
        self._refresh_token_name = settings.REFRESH_TOKEN_COOKIE_NAME

        self._httponly = settings.AUTH_COOKIE_HTTPONLY
        self._secure = settings.AUTH_COOKIE_SECURE
        self._samesite = settings.AUTH_COOKIE_SAMESITE
        self._path = settings.AUTH_COOKIE_PATH

        if self._samesite == "none" and not self._secure:
            raise ValueError("SameSite=None requires Secure cookies.")

        for cookie_name in (
            self._access_token_name,
            self._refresh_token_name,
        ):
            if cookie_name.startswith("__Host-"):
                if not self._secure or self._path != "/":
                    raise ValueError(
                        "__Host- cookies require Secure and Path=/."
                    )

        self._access_token_max_age = (
            settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        self._refresh_token_max_age = (
            settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )

    @property
    def access_token_name(self) -> str:
        return self._access_token_name

    @property
    def refresh_token_name(self) -> str:
        return self._refresh_token_name

    @property
    def access_token_max_age(self) -> int:
        return self._access_token_max_age

    @property
    def refresh_token_max_age(self) -> int:
        return self._refresh_token_max_age

    @property
    def access_token_options(self) -> CookieOptions:
        return {
            "httponly": self._httponly,
            "secure": self._secure,
            "samesite": self._samesite,
            "path": self._path,
            "max_age": self._access_token_max_age,
        }

    @property
    def refresh_token_options(self) -> CookieOptions:
        return {
            "httponly": self._httponly,
            "secure": self._secure,
            "samesite": self._samesite,
            "path": self._path,
            "max_age": self._refresh_token_max_age,
        }
