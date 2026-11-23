
from fastapi import Request, Response

from app.integrations.security.cookie_policy import CookiePolicy


class CookieService:
    def __init__(self, policy: CookiePolicy) -> None:
        self._policy = policy

    def set_auth_cookies(
        self,
        response: Response,
        *,
        access_token: str,
        refresh_token: str,
    ) -> None:
        response.set_cookie(
            key=self._policy.access_token_name,
            value=access_token,
            **self._policy.access_token_options,
        )

        response.set_cookie(
            key=self._policy.refresh_token_name,
            value=refresh_token,
            **self._policy.refresh_token_options,
        )

    def get_access_token(self, request: Request) -> str | None:
        return request.cookies.get(self._policy.access_token_name)

    def get_refresh_token(self, request: Request) -> str | None:
        return request.cookies.get(self._policy.refresh_token_name)

    def clear_auth_cookies(self, response: Response) -> None:
        response.delete_cookie(
            key=self._policy.access_token_name,
            path=self._policy.access_token_options["path"],
            secure=self._policy.access_token_options["secure"],
            httponly=self._policy.access_token_options["httponly"],
            samesite=self._policy.access_token_options["samesite"],
        )

        response.delete_cookie(
            key=self._policy.refresh_token_name,
            path=self._policy.refresh_token_options["path"],
            secure=self._policy.refresh_token_options["secure"],
            httponly=self._policy.refresh_token_options["httponly"],
            samesite=self._policy.refresh_token_options["samesite"],
        )
