from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogoutResponse:
    authenticated: bool
    message: str